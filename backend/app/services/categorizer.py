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
