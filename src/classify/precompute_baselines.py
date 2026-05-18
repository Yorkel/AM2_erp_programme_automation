"""
precompute_baselines.py

Bake the drift-monitoring baselines once locally and write them next to the
active classifier in models/runs/<active>/. This lets drift.yml run in GH
Actions without needing the (gitignored) train.csv + val.csv.

Outputs (small, committable):
  models/runs/<active>/centroids.npy     — class centroids (n_classes, embed_dim)
  models/runs/<active>/baselines.json    — label_names, val_distribution

Usage:
  python -m src.classify.precompute_baselines
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "modelling"
MODEL_DIR = PROJECT_ROOT / "models"
RUNS_DIR = MODEL_DIR / "runs"


def _active_run_id() -> str:
    active = RUNS_DIR / "active.txt"
    if not active.exists():
        raise RuntimeError(f"{active} not found — can't determine active model run")
    return active.read_text().strip()


def main() -> int:
    run_id = _active_run_id()
    out_dir = RUNS_DIR / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    train_csv = DATA_DIR / "train.csv"
    val_csv = DATA_DIR / "val.csv"
    train_emb_path = MODEL_DIR / "sbert_train_embeddings.npy"
    val_emb_path = MODEL_DIR / "sbert_val_embeddings.npy"
    clf_path = out_dir / "classifier.joblib"

    for p in [train_csv, val_csv, train_emb_path, val_emb_path, clf_path]:
        if not p.exists():
            raise RuntimeError(f"missing input: {p}")

    print(f"Loading inputs for run {run_id}...")
    train_df = pd.read_csv(train_csv)
    val_df = pd.read_csv(val_csv)
    train_emb = np.load(train_emb_path)
    val_emb = np.load(val_emb_path)
    clf = joblib.load(clf_path)
    label_names = list(clf.classes_)
    print(f"  {len(train_df)} train rows, {len(val_df)} val rows, "
          f"{len(label_names)} classes")

    print("Computing class centroids from train embeddings...")
    centroids = np.zeros((len(label_names), train_emb.shape[1]))
    for i, cls in enumerate(label_names):
        mask = train_df["target"] == cls
        if not mask.any():
            raise RuntimeError(f"no train rows for class {cls}")
        centroids[i] = train_emb[mask].mean(axis=0)
    centroids_path = out_dir / "centroids.npy"
    np.save(centroids_path, centroids)
    print(f"  Saved {centroids.shape} → {centroids_path}")

    print("Computing val distribution baseline...")
    val_pred = clf.predict(val_emb)
    val_dist = pd.Series(val_pred).value_counts(normalize=True).to_dict()
    val_dist = {str(k): float(v) for k, v in val_dist.items()}

    print("Computing val top-1 / top-2 accuracy...")
    proba = clf.predict_proba(val_emb)
    top2_idx = np.argsort(-proba, axis=1)[:, :2]
    top2_labels = np.array(label_names)[top2_idx]
    val_truth = val_df["target"].to_numpy()
    val_top1_correct = top2_labels[:, 0] == val_truth
    val_top2_correct = np.array([t in row for t, row in zip(val_truth, top2_labels)])
    val_top1_acc = float(val_top1_correct.mean())
    val_top2_acc = float(val_top2_correct.mean())
    print(f"  top-1 accuracy: {val_top1_acc:.1%}")
    print(f"  top-2 accuracy: {val_top2_acc:.1%}")

    baselines = {
        "run_id": run_id,
        "computed_at": datetime.now().isoformat(timespec="seconds"),
        "label_names": label_names,
        "val_distribution": val_dist,
        "val_top1_accuracy": val_top1_acc,
        "val_top2_accuracy": val_top2_acc,
        "n_train": int(len(train_df)),
        "n_val": int(len(val_emb)),
        "embed_dim": int(train_emb.shape[1]),
    }
    baselines_path = out_dir / "baselines.json"
    baselines_path.write_text(json.dumps(baselines, indent=2))
    print(f"  Saved → {baselines_path}")

    print("\nBaseline preview:")
    for cls, p in sorted(val_dist.items(), key=lambda x: -x[1]):
        print(f"  {cls:<45} {p:.1%}")
    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
