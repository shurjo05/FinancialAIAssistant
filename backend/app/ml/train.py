"""Train, evaluate, and persist the transaction categorization model.

Pipeline: TF-IDF (word + char n-grams) -> LogisticRegression, trained on the
dataset's native 17-category taxonomy. Produces:
  - artifacts/categorizer.joblib   the trained pipeline (used at inference)
  - reports/confusion_matrix.png   native-taxonomy confusion matrix
  - reports/metrics.txt            accuracy / macro-F1 / per-class report +
                                   the rules-vs-ML comparison in display space

Run:
    python -m app.ml.train
"""

from pathlib import Path

import joblib
import matplotlib
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
