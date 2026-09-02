"""Train, evaluate, and persist the transaction categorization model.

Pipeline: TF-IDF (word + char n-grams) -> LogisticRegression, trained on the
dataset's native 17-category taxonomy. Produces:
  - artifacts/categorizer.joblib   the trained pipeline (used at inference)
  - model_metadata.json            provenance: version, metrics, sha256, commit
  - reports/confusion_matrix.png   native-taxonomy confusion matrix
  - reports/metrics.txt            accuracy / macro-F1 / per-class report +
                                   the rules-vs-ML comparison in display space

Run:
    python -m app.ml.train
"""

import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import joblib
import matplotlib
import sklearn

matplotlib.use("Agg")  # headless backend: render to file, no window
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    classification_report,
    f1_score,
)
from sklearn.pipeline import FeatureUnion, Pipeline

from app.ml.dataset import get_grouped_splits, merchant_key, to_display
from app.services.categorizer import categorize

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
REPORTS_DIR = Path(__file__).parent / "reports"
MODEL_PATH = ARTIFACTS_DIR / "categorizer.joblib"
METADATA_PATH = Path(__file__).parent / "model_metadata.json"
DATASET = "DoDataThings/us-bank-transaction-categories-v2"


def _git_commit() -> str | None:
    """Best-effort short SHA of the current commit; None outside a git checkout."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=Path(__file__).parent, check=True,
        )
        return out.stdout.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_pipeline() -> Pipeline:
    """TF-IDF (word + char) features feeding a logistic-regression classifier."""
    features = FeatureUnion([
        ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2),
                                 min_df=2, sublinear_tf=True)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4),
                                 min_df=2, sublinear_tf=True)),
    ])
    clf = LogisticRegression(max_iter=1000, C=4.0)
    return Pipeline([("features", features), ("clf", clf)])


def rules_baseline_display(texts: list[str]) -> list[str]:
    """Predict display categories using the rule-based categorizer."""
    return [categorize(t)[0] for t in texts]


def main() -> None:
    ARTIFACTS_DIR.mkdir(exist_ok=True)
    REPORTS_DIR.mkdir(exist_ok=True)

    print("Loading data (merchant-disjoint split)...")
    X_train, X_test, y_train, y_test = get_grouped_splits()
    train_merchants = {merchant_key(x) for x in X_train}
    test_merchants = {merchant_key(x) for x in X_test}
    overlap = train_merchants & test_merchants
    print(f"  train={len(X_train)}  test={len(X_test)}")
    print(f"  merchants: train={len(train_merchants)}  test={len(test_merchants)}  overlap={len(overlap)}")

    print("Training TF-IDF + LogisticRegression...")
    pipe = build_pipeline()
    pipe.fit(X_train, y_train)

    # --- Evaluate the model in its native 17-category label space ---
    y_pred = pipe.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    macro_f1 = f1_score(y_test, y_pred, average="macro")
    report = classification_report(y_test, y_pred)

    print(f"\nML (native 17 classes):  accuracy={acc:.4f}  macro-F1={macro_f1:.4f}")

    # --- Fair comparison vs the rule baseline, in the app's display space ---
    y_test_display = [to_display(c) for c in y_test]
    ml_display = [to_display(c) for c in y_pred]
    rules_display = rules_baseline_display(X_test)

    ml_acc = accuracy_score(y_test_display, ml_display)
    ml_f1 = f1_score(y_test_display, ml_display, average="macro")
    rules_acc = accuracy_score(y_test_display, rules_display)
    rules_f1 = f1_score(y_test_display, rules_display, average="macro")

    comparison = (
        "Display-space comparison (13 app categories):\n"
        f"  Rule baseline:  accuracy={rules_acc:.4f}  macro-F1={rules_f1:.4f}\n"
        f"  ML model:       accuracy={ml_acc:.4f}  macro-F1={ml_f1:.4f}\n"
    )
    print("\n" + comparison)

    # --- Persist model + reports ---
    joblib.dump(pipe, MODEL_PATH)
    print(f"Saved model -> {MODEL_PATH}")

    # Refresh the provenance record. Preserve the release identity
    # (model_version / release_tag) if one is already set — bump those by hand
    # when you cut a new release — and update everything measurable here.
    prior = {}
    if METADATA_PATH.exists():
        try:
            prior = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            prior = {}
    metadata = {
        "model_version": prior.get("model_version", "1"),
        "release_tag": prior.get("release_tag", "model-v1"),
        "artifact": MODEL_PATH.name,
        "sha256": _sha256(MODEL_PATH),
        "size_bytes": MODEL_PATH.stat().st_size,
        "model_type": "TF-IDF (word + char n-grams) -> LogisticRegression",
        "framework": {
            "scikit_learn": sklearn.__version__,
            "python": ".".join(map(str, sys.version_info[:2])),
            "joblib": joblib.__version__,
        },
        "training_data": {
            "dataset": DATASET,
            "license": "MIT",
            "rows_total": len(X_train) + len(X_test),
            "train_rows": len(X_train),
            "test_rows": len(X_test),
            "split": "merchant-disjoint (GroupShuffleSplit by merchant key)",
            "train_merchants": len(train_merchants),
            "test_merchants": len(test_merchants),
            "merchant_overlap": len(overlap),
        },
        "evaluation": {
            "native_17_class": {"accuracy": round(acc, 4), "macro_f1": round(macro_f1, 4)},
            "display_13_class": {"accuracy": round(ml_acc, 4), "macro_f1": round(ml_f1, 4)},
            "rule_baseline_display": {"accuracy": round(rules_acc, 4), "macro_f1": round(rules_f1, 4)},
        },
        "inference": {"confidence_threshold": 0.5, "credit_debit_override": True},
        "trained_at": datetime.date.today().isoformat(),
        "git_commit": _git_commit(),
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Saved metadata -> {METADATA_PATH} "
          f"(version {metadata['model_version']}, tag {metadata['release_tag']})")
    print("  If this is a NEW release, bump model_version/release_tag and re-publish the asset.")

    (REPORTS_DIR / "metrics.txt").write_text(
        f"Evaluation: merchant-disjoint split (test merchants unseen in training)\n"
        f"train={len(X_train)}  test={len(X_test)}  "
        f"train_merchants={len(train_merchants)}  test_merchants={len(test_merchants)}  "
        f"overlap={len(overlap)}\n\n"
        f"ML model (native 17 classes)\n"
        f"  accuracy = {acc:.4f}\n  macro-F1 = {macro_f1:.4f}\n\n"
        f"Per-class report (native):\n{report}\n\n{comparison}",
        encoding="utf-8",
    )

    fig, ax = plt.subplots(figsize=(10, 9))
    ConfusionMatrixDisplay.from_predictions(
        y_test, y_pred, xticks_rotation="vertical", cmap="Blues",
        colorbar=False, ax=ax,
    )
    ax.set_title("Transaction Categorizer — Confusion Matrix (native 17 classes)")
    fig.tight_layout()
    fig.savefig(REPORTS_DIR / "confusion_matrix.png", dpi=120)
    print(f"Saved confusion matrix -> {REPORTS_DIR / 'confusion_matrix.png'}")


if __name__ == "__main__":
    main()
