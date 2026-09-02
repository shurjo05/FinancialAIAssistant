"""Rule-based transaction categorization.

Assigns each transaction one of the display categories using keyword matching
over the description. Serves two purposes:

  1. Phase A baseline  - the accuracy the ML model must beat.
  2. Phase B rule layer - refines the ML model's coarse prediction into the
     finer display taxonomy (see .claude/PROJECT_PLAN.md, hybrid taxonomy).

Matching strategy: the longest keyword that appears in the description wins, so
specific phrases beat generic ones ("amazon prime" -> subscriptions rather than
"amazon" -> shopping; "uber eats" -> restaurants rather than "uber" ->
transport).
"""

import json
from functools import lru_cache
from pathlib import Path

import joblib

from app.ml.taxonomy import to_display

# Display taxonomy for the app.
CATEGORIES = [
    "income", "rent", "groceries", "restaurants", "subscriptions", "transport",
    "utilities", "entertainment", "shopping", "health", "fees", "transfers", "other",
]

# Category -> keyword list. Keywords are matched as lowercase substrings.
CATEGORY_RULES: dict[str, list[str]] = {
    "income": ["direct deposit", "payroll", "salary", "employer", "ach credit"],
    "rent": ["rent", "apartment", "apartments", "lease", "property management", "landlord"],
    "groceries": [
        "whole foods", "trader joe", "kroger", "safeway", "wegmans", "publix",
        "aldi", "costco", "sprouts", "grocery",
    ],
    "restaurants": [
        "chipotle", "starbucks", "mcdonald", "doordash", "ubereats", "uber eats",
        "grubhub", "dunkin", "subway", "domino", "pizza", "cafe", "diner", "grill",
        "restaurant", "panda", "burger",
    ],
    "subscriptions": [
        "netflix", "spotify", "hulu", "disney+", "apple.com/bill", "amazon prime",
        "prime video", "youtube premium", "hbo", "paramount", "peacock", "adobe",
        "github", "patreon",
    ],
    "transport": [
        "uber", "lyft", "metro", "mta", "bart", "parking", "exxon", "shell",
        "chevron", "sunoco", "speedway", "gas station", "toll",
    ],
    "utilities": [
        "electric", "water bill", "verizon", "at&t", "t-mobile", "comcast",
        "xfinity", "internet", "utility", "power company",
    ],
    "entertainment": [
        "amc", "regal", "cinema", "ticketmaster", "eventbrite", "steam",
        "playstation", "xbox", "nintendo", "concert", "museum", "theater",
    ],
    "shopping": [
        "amazon", "ebay", "etsy", "target", "best buy", "walmart", "nordstrom",
        "zara", "h&m", "old navy", "ikea", "home depot", "wayfair",
    ],
    "health": [
        "cvs", "walgreens", "rite aid", "gym", "planet fitness", "pharmacy",
        "medical", "dental", "vision", "doctor",
    ],
    "fees": [
        "atm fee", "overdraft", "service charge", "late fee", "foreign transaction",
        "monthly fee", "annual fee",
    ],
    "transfers": ["transfer", "venmo", "zelle", "paypal", "cash app", "wire"],
}


def categorize(description: str, bank_hint: str | None = None) -> tuple[str, float]:
    """Return (category, confidence in 0.0-1.0) for a transaction description.

    Longest keyword match wins. Confidence is 0.95 when the description is
    essentially just the keyword, 0.80 for a substring hit. Falls back to a
    bank-supplied category hint (weak, 0.40) and finally to ("other", 0.0).
    """
    if not description:
        return ("other", 0.0)

    text = description.lower()
    best_category: str | None = None
    best_keyword = ""

    for category, keywords in CATEGORY_RULES.items():
        for keyword in keywords:
            if keyword in text and len(keyword) > len(best_keyword):
                best_keyword = keyword
                best_category = category

    if best_category is not None:
        confidence = 0.95 if text.strip() == best_keyword else 0.80
        return (best_category, confidence)

    # No keyword hit: trust a valid bank-supplied category weakly, else "other".
    if bank_hint and bank_hint.strip().lower() in CATEGORIES:
        return (bank_hint.strip().lower(), 0.40)

    return ("other", 0.0)


# ---------------------------------------------------------------------------
# Hybrid ML categorization (Phase B): trained model first, rules as fallback.
# ---------------------------------------------------------------------------
MODEL_PATH = Path(__file__).parent.parent / "ml" / "artifacts" / "categorizer.joblib"
METADATA_PATH = Path(__file__).parent.parent / "ml" / "model_metadata.json"

# Below this max-probability, we trust the rule layer instead of the model.
CONFIDENCE_THRESHOLD = 0.50

# Categories that are inherently money OUT. If a transaction is a credit
# (money in) but the model predicted one of these, it is almost certainly
# income the text model confused (income vs transfer/subscription is the
# classifier's known weak spot). We override using the credit/debit signal,
# which the text-only model never had access to.
_EXPENSE_ONLY = {
    "rent", "groceries", "restaurants", "subscriptions", "transport",
    "utilities", "entertainment", "shopping", "health", "fees",
}


@lru_cache(maxsize=1)
def _load_model():
    """Load the trained pipeline once (cached). None if it hasn't been trained."""
    if MODEL_PATH.exists():
        return joblib.load(MODEL_PATH)
    return None


@lru_cache(maxsize=1)
def _load_metadata() -> dict | None:
    """Load the model's provenance record, if present."""
    if METADATA_PATH.exists():
        try:
            return json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
    return None


def model_info() -> dict:
    """Provenance of the active categorizer, for /api/health and observability."""
    meta = _load_metadata() or {}
    loaded = _load_model() is not None
    return {
        "model_loaded": loaded,
        "mode": "ml+rules" if loaded else "rules-only",
        "model_version": meta.get("model_version") if loaded else None,
        "release_tag": meta.get("release_tag") if loaded else None,
    }


def _apply_credit_override(
    category: str, confidence: float, transaction_type: str | None
) -> tuple[str, float]:
    """Correct expense-only predictions on money-in rows to income.

    A credit (money received) cannot be a subscription/grocery/rent charge, so
    such a prediction is a misclassified income row. Uses the credit/debit
    signal from the parser that the text model doesn't see.
    """
    if transaction_type == "credit" and category in _EXPENSE_ONLY:
        return ("income", max(confidence, 0.70))
    return (category, confidence)


def categorize_batch(
    descriptions: list[str],
    transaction_types: list[str] | None = None,
) -> list[tuple[str, float]]:
    """Categorize many descriptions: ML model where confident, rules otherwise.

    Batched so the model vectorizes/predicts the whole upload in one pass.
    If transaction_types are given, applies the credit/debit income override.
    Returns (display_category, confidence) per description. With no trained
    model present, falls back entirely to the rule categorizer.
    """
    model = _load_model()

    base: list[tuple[str, float]]
    if model is None:
        base = [categorize(d) for d in descriptions]
    else:
        predictions = model.predict(descriptions)
        confidences = model.predict_proba(descriptions).max(axis=1)
        base = []
        for description, native_label, confidence in zip(descriptions, predictions, confidences, strict=False):
            if confidence >= CONFIDENCE_THRESHOLD:
                base.append((to_display(native_label), float(confidence)))
            else:
                base.append(categorize(description))  # low confidence -> rules

    if transaction_types is None:
        return base

    return [
        _apply_credit_override(cat, conf, ttype)
        for (cat, conf), ttype in zip(base, transaction_types, strict=False)
    ]
