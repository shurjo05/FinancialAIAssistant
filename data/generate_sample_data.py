"""Generate synthetic transaction data in several bank export formats.

Produces the SAME underlying transactions rendered three ways, so the CSV
parser can be tested against real-world format variety:

  1. chase_sample.csv        - Chase credit-card style (single Amount col,
                               purchases negative, payments positive)
  2. capitalone_sample.csv   - separate Debit / Credit columns, both positive
  3. messy_generic.csv       - checking-account style with deliberate mess:
                               $ and thousands commas, (parentheses) negatives,
                               mixed date formats, blank rows, one bad date

The data spans 6 months and includes recurring subscriptions, biweekly
income, everyday spending, and one deliberate spending spike (anomaly) so the
detectors built in later phases have something to find.

Run from the repo root:
    python data/generate_sample_data.py
"""

import csv
import datetime
import random
from pathlib import Path

SEED = 42                      # deterministic output
START = datetime.date(2024, 1, 1)
MONTHS = 6
OUT_DIR = Path(__file__).parent

random.seed(SEED)


# --- merchant pools by spending type --------------------------------------
GROCERIES = ["WHOLE FOODS #456", "TRADER JOE'S #221", "KROGER #1123", "SAFEWAY 402"]
RESTAURANTS = ["CHIPOTLE 1442", "STARBUCKS #0912", "MCDONALD'S F1123", "DOORDASH*PANDA", "SUBWAY 33021"]
TRANSPORT = ["UBER *TRIP", "LYFT *RIDE", "SHELL OIL 5567", "CHEVRON 220"]
SHOPPING = ["AMAZON.COM*A1B2", "TARGET 00012", "BEST BUY #401"]


def month_dates(base: datetime.date, months: int):
    """Yield (year, month) tuples for `months` consecutive months."""
    y, m = base.year, base.month
    for _ in range(months):
        yield y, m
        m += 1
        if m > 12:
            m = 1
            y += 1


def build_transactions():
    """Return a list of dicts: {date, description, amount, type}.

    amount here uses the *bank* convention we standardize on for generation:
    negative = money out (expense), positive = money in (income/payment).
    """
    rows = []

    for i, (y, m) in enumerate(month_dates(START, MONTHS)):
        # Biweekly income (two paychecks a month)
        for day in (1, 15):
            rows.append({"date": datetime.date(y, m, day),
                         "description": "DIRECT DEPOSIT EMPLOYER PAYROLL",
                         "amount": 2200.00, "type": "credit"})

        # Fixed monthly recurring charges (subscriptions + bills)
        recurring = [
            ("NETFLIX.COM", 15.99, 3),
            ("SPOTIFY USA", 11.99, 5),
            ("PLANET FITNESS", 24.99, 7),
            ("COMCAST XFINITY", 60.00, 9),
            ("T-MOBILE PCS SVC", 70.00, 11),
            ("SUNSET APARTMENTS RENT", 1800.00, 1),
        ]
        for name, amt, day in recurring:
            rows.append({"date": datetime.date(y, m, day),
                         "description": name, "amount": -amt, "type": "debit"})

        # Everyday variable spending
        for _ in range(random.randint(6, 10)):
            pool = random.choice([GROCERIES, RESTAURANTS, TRANSPORT, SHOPPING])
            name = random.choice(pool)
            amt = round(random.uniform(6, 120), 2)
            day = random.randint(1, 28)
            rows.append({"date": datetime.date(y, m, day),
                         "description": name, "amount": -amt, "type": "debit"})

        # Deliberate anomalies (labeled ground truth for detector evaluation):
        # large charges well above the normal per-category range, spread across
        # months and categories. Tagged with injected_anomaly=True.
        injected = {
            1: ("BEST BUY #401", 1299.00),        # shopping spike
            2: ("WHOLE FOODS #456", 512.40),      # groceries spike
            3: ("BEST BUY #401", 1499.99),        # shopping spike
            4: ("CHIPOTLE 1442", 388.75),         # restaurants spike
            5: ("SHELL OIL 5567", 415.60),        # transport spike
        }
        if i in injected:
            name, amt = injected[i]
            rows.append({"date": datetime.date(y, m, 18),
                         "description": name, "amount": -amt,
                         "type": "debit", "injected_anomaly": True})

    rows.sort(key=lambda r: r["date"])
    return rows


# --- format writers --------------------------------------------------------
def write_chase(rows):
    path = OUT_DIR / "chase_sample.csv"
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Transaction Date", "Post Date", "Description", "Category", "Type", "Amount", "Memo"])
        for r in rows:
            post = r["date"] + datetime.timedelta(days=1)
            typ = "Payment" if r["amount"] > 0 else "Sale"
            w.writerow([r["date"].strftime("%m/%d/%Y"), post.strftime("%m/%d/%Y"),
                        r["description"], "", typ, f"{r['amount']:.2f}", ""])
    return path


def write_capitalone(rows):
    path = OUT_DIR / "capitalone_sample.csv"
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Transaction Date", "Posted Date", "Card No.", "Description", "Category", "Debit", "Credit"])
        for r in rows:
            post = r["date"] + datetime.timedelta(days=2)
            debit = f"{-r['amount']:.2f}" if r["amount"] < 0 else ""
            credit = f"{r['amount']:.2f}" if r["amount"] > 0 else ""
            w.writerow([r["date"].strftime("%Y-%m-%d"), post.strftime("%Y-%m-%d"),
                        "1234", r["description"], "", debit, credit])
    return path


def write_messy(rows):
    """Checking-account style with deliberate real-world mess."""
    path = OUT_DIR / "messy_generic.csv"
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Merchant", "Amount", "Running Balance"])
        balance = 5000.00
        for idx, r in enumerate(rows):
            balance += r["amount"]

            # Vary date format between rows
            if idx % 3 == 0:
                d = r["date"].strftime("%m/%d/%Y")
            elif idx % 3 == 1:
                d = r["date"].strftime("%Y-%m-%d")
            else:
                d = r["date"].strftime("%b %d, %Y")

            # Amounts: $ sign, thousands commas, (parens) for negatives
            if r["amount"] < 0:
                amt = f"(${abs(r['amount']):,.2f})"
            else:
                amt = f"${r['amount']:,.2f}"

            w.writerow([d, r["description"], amt, f"${balance:,.2f}"])

            # Inject a blank row occasionally (real exports have these)
            if idx == 10:
                w.writerow([])
            # Inject one unparseable date to test row-level error handling
            if idx == 20:
                w.writerow(["13/45/2024", "GARBAGE ROW TEST", "($9.99)", "$0.00"])

    return path


def main():
    rows = build_transactions()
    paths = [write_chase(rows), write_capitalone(rows), write_messy(rows)]
    print(f"Generated {len(rows)} base transactions -> 3 formats:")
    for p in paths:
        print(f"  {p.name}")


if __name__ == "__main__":
    main()
