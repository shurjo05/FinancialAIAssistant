"""Load and prepare the training data for the categorization model.

Dataset: DoDataThings/us-bank-transaction-categories-v2 (MIT, open).
~68k US transaction descriptions across 17 categories, synthesized from 500+
real merchant names in realistic bank-statement format. Columns: `description`,
`category`. Small enough to download and load fully (no streaming needed).

The model trains on the dataset's native 17-category taxonomy (honest metrics);
DATASET_TO_DISPLAY maps those to the app's 13 display categories at inference.

Run directly to inspect the data and class distribution:
    python -m app.ml.dataset
"""

import re

import pandas as pd
from datasets import load_dataset
from sklearn.model_selection import GroupShuffleSplit, train_test_split

# Taxonomy constants live in a dependency-free module shared with inference.
from app.ml.taxonomy import DATASET_CATEGORIES, DATASET_TO_DISPLAY, to_display  # noqa: F401

DATASET_ID = "DoDataThings/us-bank-transaction-categories-v2"

# Descriptions are prefixed with a debit/credit tag, e.g. "[debit] PP*SAFEWAY".
# We strip it so the training text matches our app's raw merchant strings
# (our transactions store type separately, not inline in the description).
_TAG_PREFIX = re.compile(r"^\s*\[(?:debit|credit)\]\s*", re.IGNORECASE)


def clean_description(text: str) -> str:
    """Strip the [debit]/[credit] tag so text matches app inference input."""
    return _TAG_PREFIX.sub("", (text or "").strip())


def merchant_key(description: str) -> str:
    """Heuristic merchant identifier used to group rows for a disjoint split.

    Strips digits/refs/addresses to letters, then keys on the first two words
    (e.g. "wholefds #8860 chicago" -> "wholefds", "BEST BUY #12" -> "best buy").
    Approximate, but enough to keep a merchant out of both train and test so
    accuracy reflects generalization to UNSEEN merchants, not memorization.
    """
    text = clean_description(description).lower()
    text = re.sub(r"[^a-z ]", " ", text)
    tokens = [t for t in text.split() if len(t) > 1]
    return " ".join(tokens[:2]) if tokens else "unknown"


def load_frame(sample_size: int | None = None, seed: int = 42) -> pd.DataFrame:
    """Load the dataset into a DataFrame with cleaned descriptions.

    Columns: [description, category]. Pass sample_size to subsample (stratified)
    for faster iteration; None uses the full ~68k rows.
    """
    ds = load_dataset(DATASET_ID, split="train")
    df = ds.to_pandas()[["description", "category"]].copy()
    df["description"] = df["description"].map(clean_description)
    df = df[(df["description"] != "") & df["category"].notna()].reset_index(drop=True)

    if sample_size is not None and sample_size < len(df):
        df, _ = train_test_split(
            df, train_size=sample_size, random_state=seed, stratify=df["category"]
        )
        df = df.reset_index(drop=True)
    return df


def get_splits(
    sample_size: int | None = None,
    test_size: float = 0.2,
    seed: int = 42,
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Return (X_train, X_test, y_train, y_test), stratified by category.

    Random split: fast, but merchants overlap between train and test, so the
    resulting accuracy overstates real-world performance. Prefer
    get_grouped_splits for an honest generalization estimate.
    """
    df = load_frame(sample_size=sample_size, seed=seed)
    X = df["description"].tolist()
    y = df["category"].tolist()
    return train_test_split(X, y, test_size=test_size, random_state=seed, stratify=y)


def get_grouped_splits(
    sample_size: int | None = None,
    test_size: float = 0.2,
    seed: int = 42,
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Merchant-disjoint split: test merchants never appear in training.

    Groups rows by merchant_key and splits on groups (GroupShuffleSplit), so
    the model is scored on merchants it has never seen. This is the honest
    generalization number to report.
    """
    df = load_frame(sample_size=sample_size, seed=seed)
    groups = df["description"].map(merchant_key)

    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    train_idx, test_idx = next(splitter.split(df, df["category"], groups))

    X = df["description"].tolist()
    y = df["category"].tolist()
    X_train = [X[i] for i in train_idx]
    X_test = [X[i] for i in test_idx]
    y_train = [y[i] for i in train_idx]
    y_test = [y[i] for i in test_idx]
    return X_train, X_test, y_train, y_test


if __name__ == "__main__":
    frame = load_frame()
    print(f"Loaded {len(frame)} rows across {frame['category'].nunique()} categories\n")
    print("Class distribution:")
    print(frame["category"].value_counts().to_string())
    print("\nExample cleaned rows:")
    print(frame.sample(8, random_state=1).to_string(index=False))
    print("\nUnmapped categories (should be empty):",
          sorted(set(frame["category"]) - set(DATASET_TO_DISPLAY)))
