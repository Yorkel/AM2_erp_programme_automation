"""
s05_train.py
Train the production classifier: LogReg on sentence transformer embeddings.
No metadata — chosen in notebook 09 after SHAP analysis showed metadata
caused the model to classify by source type rather than content.

Input:  data/modelling/train.csv
        models/sbert_train_embeddings.npy
Output: models/sbert_classifier_no_meta.joblib
"""

import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from sklearn.linear_model import LogisticRegression

# -----------------------------
# CONFIG
# -----------------------------
DATA_DIR = Path("data/modelling")
MODEL_DIR = Path("models")
LABEL_COL = "target"
RANDOM_SEED = 42


def main():
    """Train LogReg on sentence embeddings (no metadata)."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # Load training data
    train_df = pd.read_csv(DATA_DIR / "train.csv")
    train_emb = np.load(MODEL_DIR / "sbert_train_embeddings.npy")
    print(f"  Training data: {len(train_df)} articles, {train_emb.shape[1]} dimensions")

    # Integrity guard: embeddings and labels are aligned BY ROW ORDER only (the .npy
    # carries no ids). If train.csv was regenerated or re-sorted without re-embedding,
    # the counts diverge and every label would attach to the wrong vector — a silently
    # corrupt model. Fail loudly instead.
    if len(train_df) != train_emb.shape[0]:
        raise SystemExit(
            f"Row mismatch: train.csv has {len(train_df)} rows but "
            f"sbert_train_embeddings.npy has {train_emb.shape[0]}. Re-run the embedding "
            f"step so vectors and labels line up before training."
        )
    if train_df[LABEL_COL].isna().any():
        raise SystemExit(
            f"{int(train_df[LABEL_COL].isna().sum())} rows have a NaN {LABEL_COL!r} — "
            f"clean the label column before training."
        )

    # Train
    clf = LogisticRegression(
        max_iter=1000,
        class_weight="balanced",
        random_state=RANDOM_SEED,
    )
    clf.fit(train_emb, train_df[LABEL_COL])
    print(f"  Classes: {list(clf.classes_)}")

    # Save
    out_path = MODEL_DIR / "sbert_classifier_no_meta.joblib"
    joblib.dump(clf, out_path)
    print(f"  Saved → {out_path}")
    print("  Done.")


if __name__ == "__main__":
    main()
