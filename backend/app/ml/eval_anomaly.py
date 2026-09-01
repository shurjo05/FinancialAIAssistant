"""Evaluate the anomaly detector against known injected anomalies.

Reuses the synthetic generator (which tags injected anomalies as ground truth),
runs the full categorize + detect pipeline in memory, and reports precision /
recall / F1 for the anomaly detector.

Run:
    python -m app.ml.eval_anomaly
"""

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

from app.services.categorizer import categorize_batch
from app.services.detector import detect_anomalies
from app.services.parser import normalize_merchant

# Load the generator module from the repo's data/ directory (not a package).
_GEN_PATH = Path(__file__).resolve().parents[3] / "data" / "generate_sample_data.py"
_spec = importlib.util.spec_from_file_location("generate_sample_data", _GEN_PATH)
_gen = importlib.util.module_from_spec(_spec)
sys.modules["generate_sample_data"] = _gen
_spec.loader.exec_module(_gen)


def build_labeled_transactions() -> list[SimpleNamespace]:
    """Run the ingest pipeline in memory, preserving ground-truth anomaly tags."""
    rows = _gen.build_transactions()
    descriptions = [r["description"] for r in rows]
    types = [r["type"] for r in rows]
    categories = categorize_batch(descriptions, types)

    transactions = []
    for i, (row, (category, _conf)) in enumerate(zip(rows, categories, strict=False)):
        transactions.append(SimpleNamespace(
            id=i,
            date=row["date"],
            amount=-row["amount"],  # generator uses bank sign; flip to expense-positive
            merchant_normalized=normalize_merchant(row["description"]),
            category=category,
            transaction_type=row["type"],
            injected=bool(row.get("injected_anomaly")),
        ))
    return transactions


def main() -> None:
    transactions = build_labeled_transactions()
    truth_ids = {t.id for t in transactions if t.injected}

    anomalies = detect_anomalies(transactions)
    predicted_ids = {a["transaction_id"] for a in anomalies}

    tp = len(truth_ids & predicted_ids)
    fp = len(predicted_ids - truth_ids)
    fn = len(truth_ids - predicted_ids)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    print(f"Injected anomalies (truth): {len(truth_ids)}")
    print(f"Flagged by detector:        {len(predicted_ids)}")
    print(f"  true positives  = {tp}")
    print(f"  false positives = {fp}")
    print(f"  false negatives = {fn}")
    print(f"\nPrecision = {precision:.2f}   Recall = {recall:.2f}   F1 = {f1:.2f}")

    if fp:
        print("\nFalse positives:")
        for a in anomalies:
            if a["transaction_id"] not in truth_ids:
                print(f"  {a['description']}")

    reports_dir = Path(__file__).parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    (reports_dir / "anomaly_metrics.txt").write_text(
        f"Anomaly detector evaluation (synthetic labeled anomalies)\n"
        f"injected={len(truth_ids)} flagged={len(predicted_ids)} "
        f"TP={tp} FP={fp} FN={fn}\n"
        f"precision={precision:.2f} recall={recall:.2f} f1={f1:.2f}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
