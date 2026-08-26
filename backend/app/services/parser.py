"""CSV parsing and normalization.

Turns a raw bank/credit-card CSV (any of several formats) into a clean,
consistent list of transaction dicts plus a structured list of row-level
errors. See .claude/PROJECT_PLAN.md sections 5-6 for the strategy.

Canonical output shape per row:
    {
        "date": datetime.date,
        "description": str,
        "merchant_normalized": str,
        "amount": float,          # positive = expense, negative = income
        "transaction_type": str,  # 'debit' | 'credit'
    }
"""

import csv
import datetime
import difflib
import os
import re
from typing import IO

from dateutil import parser as dateparser

# Canonical field -> the messy header names banks actually use.
# Headers are lowercased/stripped before matching against these.
COLUMN_ALIASES = {
    "date": ["date", "transaction date", "post date", "posted date", "trans date", "txn date"],
    "description": ["description", "merchant", "payee", "memo", "original description", "name"],
    "amount": ["amount", "transaction amount", "charge"],
    "debit": ["debit", "withdrawal", "debit amount"],
    "credit": ["credit", "deposit", "credit amount"],
    "type": ["type", "transaction type", "credit/debit"],
    "balance": ["balance", "running bal", "running balance"],
}

# How close a fuzzy match must be (0-1). Higher = stricter.
MATCH_CUTOFF = 0.7


def detect_columns(headers: list[str]) -> dict[str, str]:
    """Map canonical field names to the actual header in this CSV.

    Given a CSV's header row, return a dict like:
        {"date": "Transaction Date", "description": "Description",
         "amount": "Amount"}
    Only fields confidently found are included. Each real header is assigned
    to at most one canonical field (the best-scoring match wins).
    """
    results: dict[str, str] = {}

    # Normalized header (lowercase, stripped) -> original header, so we can
    # match loosely but return the properly-cased name the CSV actually uses.
    normalized = {h.strip().lower(): h for h in headers}

    # Track headers already claimed so two fields can't grab the same column
    # (e.g. "Transaction Amount" must not map to both "amount" and "type").
    used: set[str] = set()

    for field, aliases in COLUMN_ALIASES.items():
        best_header: str | None = None
        best_score = 0.0

        for norm, original in normalized.items():
            if original in used:
                continue

            # Fuzzy-match the header against this field's known aliases.
            match = difflib.get_close_matches(norm, aliases, n=1, cutoff=MATCH_CUTOFF)
            if not match:
                continue

            # Retain the strongest-scoring header for this field.
            score = difflib.SequenceMatcher(None, norm, match[0]).ratio()
            if score > best_score:
                best_score = score
                best_header = original

        if best_header is not None:
            results[field] = best_header
            used.add(best_header)

    return results


def clean_amount_string(raw: str | None) -> float:
    """Parse a currency string into a signed float, preserving the source sign.

    Handles plain numbers, leading-minus negatives, dollar signs, thousands
    separators, and parenthesised negatives. Blank/missing values become 0.0.
    Sign stays in source terms (money out is negative); conversion to the
    internal convention happens in normalize_amount.

        "-15.99" -> -15.99   "$2,200.00" -> 2200.0
        "($73.32)" -> -73.32 "" -> 0.0
    """
    if raw is None:
        return 0.0
    text = str(raw).strip()
    if not text:
        return 0.0

    negative = text.startswith("-") or (text.startswith("(") and text.endswith(")"))
    digits = re.sub(r"[^\d.]", "", text)
    if not digits or digits == ".":
        return 0.0

    value = float(digits)
    return -value if negative else value


def normalize_amount(row: dict, columns: dict[str, str]) -> tuple[float, str]:
    """Return (amount, transaction_type) in the internal convention.

    Internal convention: amount > 0 = expense (money out), amount < 0 = income.
    Handles both split debit/credit files and single-amount files.
    """
    # Split file: separate debit/credit columns (both positive in the source).
    if "debit" in columns or "credit" in columns:
        debit_val = clean_amount_string(row.get(columns["debit"])) if "debit" in columns else 0.0
        credit_val = clean_amount_string(row.get(columns["credit"])) if "credit" in columns else 0.0
        if debit_val != 0.0:
            return abs(debit_val), "debit"      # money out -> expense (positive)
        if credit_val != 0.0:
            return -abs(credit_val), "credit"   # money in -> income (negative)
        return 0.0, "debit"

    # Single-amount file: banks emit money-out as negative, so flip the sign.
    if "amount" in columns:
        raw = clean_amount_string(row.get(columns["amount"]))
        amount = -raw
        return amount, ("debit" if amount > 0 else "credit")

    raise ValueError("no amount, debit, or credit column detected")


def parse_date(raw: str | None) -> "datetime.date":
    """Parse a date string in any common format into a date, or raise ValueError.

    dateutil handles MM/DD/YYYY, YYYY-MM-DD, 'Mon DD, YYYY', etc. Unparseable
    input (e.g. '13/45/2024') raises ValueError, which parse_csv records as a
    row-level error rather than crashing the whole file.
    """
    if raw is None or not str(raw).strip():
        raise ValueError("empty date")
    return dateparser.parse(str(raw).strip()).date()


def normalize_merchant(raw: str) -> str:
    """Reduce a raw description to a canonical merchant name for grouping.

        "WHOLE FOODS #456"  -> "WHOLE FOODS"
        "UBER *TRIP"        -> "UBER"
        "MCDONALD'S F1123"  -> "MCDONALD'S"
        "SHELL OIL 5567"    -> "SHELL OIL"
    """
    if not raw:
        return ""
    text = raw.upper().strip()
    text = text.split("*", 1)[0]                       # drop txn id after '*'
    text = re.sub(r"#\w+", " ", text)                  # store/ref codes: #456
    text = re.sub(r"\b[A-Z]?\d{2,}[A-Z0-9]*\b", " ", text)  # codes: F1123, 00012
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text


def parse_csv(file: "str | os.PathLike | IO[str]") -> tuple[list[dict], list[dict]]:
    """Parse a bank CSV into (clean_rows, errors).

    clean_rows: list of {date, description, merchant_normalized, amount,
                transaction_type}.
    errors:     list of {row, issue, raw} for rows that could not be parsed.

    One bad row never aborts the file; it is recorded and parsing continues.
    Accepts a path or an already-open text file object.
    """
    close_after = False
    if isinstance(file, (str, os.PathLike)):
        handle: IO[str] = open(file, newline="", encoding="utf-8-sig")
        close_after = True
    else:
        handle = file

    clean_rows: list[dict] = []
    errors: list[dict] = []

    try:
        reader = csv.DictReader(handle)
        columns = detect_columns(list(reader.fieldnames or []))

        has_amount = any(k in columns for k in ("amount", "debit", "credit"))
        if "date" not in columns or "description" not in columns or not has_amount:
            errors.append({
                "row": 0,
                "issue": "could not detect required columns (date, description, amount)",
                "raw": str(reader.fieldnames),
            })
            return clean_rows, errors

        # start=2: row 1 is the header, so data rows match spreadsheet numbering.
        for i, row in enumerate(reader, start=2):
            if not any((v or "").strip() for v in row.values()):
                continue  # skip fully blank rows

            try:
                description = (row.get(columns["description"]) or "").strip()
                clean_rows.append({
                    "date": parse_date(row.get(columns["date"])),
                    "description": description,
                    "merchant_normalized": normalize_merchant(description),
                    **dict(zip(("amount", "transaction_type"), normalize_amount(row, columns))),
                })
            except Exception as exc:  # noqa: BLE001 - one bad row must not abort
                errors.append({"row": i, "issue": str(exc), "raw": str(row)})

        return clean_rows, errors
    finally:
        if close_after:
            handle.close()
