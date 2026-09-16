"""Regression gate: evaluate the pinned categorizer against its recorded baseline.

Reproduces the merchant-disjoint test split, predicts with the loaded model,
computes native + display macro-F1, and exits non-zero if either drops more than
TOLERANCE below the baseline recorded in model_metadata.json. Run by the
`ml-eval` CI workflow (not on every commit) and manually before publishing a new
model. Does NOT retrain — it only evaluates the pinned artifact.

    python -m app.ml.eval_categorizer
"""

import json
import sys
from pathlib import Path

from sklearn.metrics import accuracy_score, f1_score

from app.ml.dataset import get_grouped_splits, to_display
from app.services.categorizer import _load_model

METADATA_PATH = Path(__file__).parent / "model_metadata.json"

# Allowed macro-F1 drop below the recorded baseline before we fail the build.
# Small enough to catch a real regression, loose enough to absorb split noise.
TOLERANCE = 0.03


def main() -> int:
    model = _load_model()
    if model is None:
        print(
            "ERROR: no model artifact present. Run `python -m scripts.fetch_model` first.",
            file=sys.stderr,
        )
        return 1

    meta = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    base_native = meta["evaluation"]["native_17_class"]["macro_f1"]
    base_display = meta["evaluation"]["display_13_class"]["macro_f1"]

    _, x_test, _, y_test = get_grouped_splits()
    y_pred = list(model.predict(x_test))

    native_f1 = f1_score(y_test, y_pred, average="macro")
    native_acc = accuracy_score(y_test, y_pred)
    display_f1 = f1_score(
        [to_display(c) for c in y_test],
        [to_display(c) for c in y_pred],
        average="macro",
    )

    print(f"native  macro-F1 = {native_f1:.4f}  (baseline {base_native:.4f}, acc {native_acc:.4f})")
    print(f"display macro-F1 = {display_f1:.4f}  (baseline {base_display:.4f})")

    failures = []
    if native_f1 < base_native - TOLERANCE:
        failures.append(f"native macro-F1 {native_f1:.4f} < {base_native - TOLERANCE:.4f}")
    if display_f1 < base_display - TOLERANCE:
        failures.append(f"display macro-F1 {display_f1:.4f} < {base_display - TOLERANCE:.4f}")

    if failures:
        print("REGRESSION detected:\n  " + "\n  ".join(failures), file=sys.stderr)
        return 1
    print(f"OK: no macro-F1 regression beyond tolerance ({TOLERANCE}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
