"""Category taxonomy constants shared by training and inference.

Kept dependency-free (no `datasets`/`sklearn` imports) so the API can import
the mapping at request time without pulling in heavy training libraries.
"""

# The training dataset's native 17-category taxonomy (the model's label space).
DATASET_CATEGORIES = [
    "Restaurants", "Groceries", "Shopping", "Transportation", "Entertainment",
    "Utilities", "Subscription", "Healthcare", "Insurance", "Mortgage", "Rent",
    "Travel", "Education", "Personal Care", "Transfer", "Income", "Fees",
]

# Maps the dataset's 17 categories -> the app's 13 display categories.
DATASET_TO_DISPLAY = {
    "Restaurants": "restaurants",
    "Groceries": "groceries",
    "Shopping": "shopping",
    "Transportation": "transport",
    "Entertainment": "entertainment",
    "Utilities": "utilities",
    "Subscription": "subscriptions",
    "Healthcare": "health",
    "Insurance": "other",
    "Mortgage": "rent",
    "Rent": "rent",
    "Travel": "transport",
    "Education": "other",
    "Personal Care": "health",
    "Transfer": "transfers",
    "Income": "income",
    "Fees": "fees",
}


def to_display(category: str) -> str:
    """Map a dataset (native) category to the app's display taxonomy."""
    return DATASET_TO_DISPLAY.get(category, "other")
