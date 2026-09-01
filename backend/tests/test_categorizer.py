"""Categorizer tests: deterministic rule matches and the credit/debit override."""

from app.services.categorizer import categorize, categorize_batch


def test_rule_matches_known_merchants():
    assert categorize("NETFLIX.COM")[0] == "subscriptions"
    assert categorize("WHOLE FOODS #456")[0] == "groceries"
    assert categorize("DIRECT DEPOSIT EMPLOYER PAYROLL")[0] == "income"


def test_unknown_merchant_is_other():
    category, confidence = categorize("ZZZ UNKNOWN MERCHANT")
    assert category == "other"
    assert confidence == 0.0


def test_credit_override_reclassifies_expense_only_to_income():
    # A money-IN row can't be a subscription charge -> corrected to income.
    (category, _), = categorize_batch(["NETFLIX.COM"], ["credit"])
    assert category == "income"


def test_debit_keeps_expense_category():
    (category, _), = categorize_batch(["NETFLIX.COM"], ["debit"])
    assert category == "subscriptions"
