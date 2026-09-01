"""Parser tests: format-agnostic ingest, error handling, and the sign invariant."""

import csv
from pathlib import Path

from app.services.parser import (
    clean_amount_string,
    detect_columns,
    normalize_merchant,
    parse_csv,
)

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
FORMATS = ["chase_sample.csv", "capitalone_sample.csv", "messy_generic.csv"]


def _totals(rows):
    expense = round(sum(r["amount"] for r in rows if r["amount"] > 0), 2)
    income = round(sum(-r["amount"] for r in rows if r["amount"] < 0), 2)
    return expense, income


def test_three_formats_produce_identical_totals():
    """Same underlying data in 3 bank formats must normalize to the same totals."""
    totals = {_totals(parse_csv(str(DATA_DIR / f))[0]) for f in FORMATS}
    assert len(totals) == 1


def test_malformed_row_is_reported_not_crashed():
    rows, errors = parse_csv(str(DATA_DIR / "messy_generic.csv"))
    assert len(rows) > 0
    assert len(errors) == 1
    assert "13/45/2024" in errors[0]["raw"]


def test_sign_invariant_income_negative_expense_positive():
    """Core invariant: expenses are positive, income is negative."""
    rows, _ = parse_csv(str(DATA_DIR / "chase_sample.csv"))
    income = [r for r in rows if "PAYROLL" in r["description"]]
    expenses = [r for r in rows if r["description"].startswith("NETFLIX")]
    assert income and all(r["amount"] < 0 for r in income)
    assert expenses and all(r["amount"] > 0 for r in expenses)


def test_clean_amount_string_cases():
    assert clean_amount_string("-15.99") == -15.99
    assert clean_amount_string("$2,200.00") == 2200.0
    assert clean_amount_string("($73.32)") == -73.32
    assert clean_amount_string("") == 0.0
    assert clean_amount_string(None) == 0.0


def test_normalize_merchant_cases():
    assert normalize_merchant("WHOLE FOODS #456") == "WHOLE FOODS"
    assert normalize_merchant("UBER *TRIP") == "UBER"
    assert normalize_merchant("SHELL OIL 5567") == "SHELL OIL"


def test_detect_columns_handles_split_debit_credit():
    with open(DATA_DIR / "capitalone_sample.csv", newline="") as fh:
        headers = next(csv.reader(fh))
    cols = detect_columns(headers)
    assert "debit" in cols and "credit" in cols


def test_detect_columns_single_amount_format():
    with open(DATA_DIR / "chase_sample.csv", newline="") as fh:
        headers = next(csv.reader(fh))
    cols = detect_columns(headers)
    assert cols.get("amount") and "date" in cols and "description" in cols
