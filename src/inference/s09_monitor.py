"""
s09_monitor.py
Production monitoring for the classification pipeline.

Compares new predictions against val baseline:
- Prediction distribution shift
- Confidence score drift
- Embedding drift (cosine similarity to training centroids)

Input:  data/modelling/classified_articles.csv (from s08_predict)
        models/sbert_train_embeddings.npy (training centroids)
        data/modelling/val.csv (baseline)
Output: Monitoring report (printed + saved to data/modelling/monitoring_log.csv)
"""

import os

import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from datetime import datetime
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# -----------------------------
# CONFIG
# -----------------------------
MODEL_NAME = "all-MiniLM-L6-v2"
MODEL_DIR = Path("models")
DATA_DIR = Path("data/modelling")
DRIFT_THRESHOLD = 0.3
DISTRIBUTION_ALERT_THRESHOLD = 0.10


def compute_centroids(train_df, train_emb, label_names, label_col="target"):
    """Compute per-class centroids from training embeddings."""
    centroids = {}
    for cls in label_names:
        mask = train_df[label_col] == cls
        centroids[cls] = train_emb[mask].mean(axis=0)
    return np.array([centroids[cls] for cls in label_names])


def check_distribution(classified_df, val_df, label_names, clf):
    """Compare prediction distribution against val baseline."""
    val_pred = clf.predict(
        np.load(MODEL_DIR / "sbert_val_embeddings.npy")
    )
    val_dist = pd.Series(val_pred).value_counts(normalize=True)
    real_dist = classified_df["top1"].value_counts(normalize=True)

    alerts = []
    for cls in label_names:
        v = val_dist.get(cls, 0)
        r = real_dist.get(cls, 0)
        delta = r - v
        if abs(delta) > DISTRIBUTION_ALERT_THRESHOLD:
            alerts.append(f"  {cls}: {v:.1%} → {r:.1%} (delta {delta:+.1%})")

    return val_dist, real_dist, alerts


def check_confidence(classified_df):
    """Compute confidence statistics."""
    conf = classified_df["top1_confidence"]
    return {
        "mean": conf.mean(),
        "median": conf.median(),
        "min": conf.min(),
        "pct_below_50": (conf < 0.50).mean(),
        "pct_below_30": (conf < 0.30).mean(),
    }


def check_drift(texts, centroid_matrix, label_names, model):
    """Check embedding drift against training centroids."""
    embeddings = model.encode(texts, show_progress_bar=False)
    sims = cosine_similarity(embeddings, centroid_matrix)
    max_sims = sims.max(axis=1)

    flagged = []
    for i in np.where(max_sims < DRIFT_THRESHOLD)[0]:
        closest = label_names[sims[i].argmax()]
        flagged.append({"index": i, "similarity": max_sims[i], "closest": closest})

    return {
        "mean_similarity": max_sims.mean(),
        "min_similarity": max_sims.min(),
        "n_flagged": len(flagged),
        "flagged": flagged,
    }


def main():
    """Run full monitoring report."""
    # Load
    classified_path = DATA_DIR / "classified_articles.csv"
    if not classified_path.exists():
        print(f"  No classified articles found at {classified_path}")
        print("  Run s07_predict.py first.")
        return

    classified_df = pd.read_csv(classified_path)
    val_df = pd.read_csv(DATA_DIR / "val.csv")
    train_df = pd.read_csv(DATA_DIR / "train.csv")
    train_emb = np.load(MODEL_DIR / "sbert_train_embeddings.npy")
    clf = joblib.load(MODEL_DIR / "sbert_classifier_no_meta.joblib")
    model = SentenceTransformer(MODEL_NAME)
    label_names = list(clf.classes_)

    print(f"\n{'='*60}")
    print(f"  Monitoring Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Articles: {len(classified_df)}")
    print(f"{'='*60}")

    # 1. Distribution
    val_dist, real_dist, dist_alerts = check_distribution(classified_df, val_df, label_names, clf)
    print(f"\n  Prediction distribution:")
    print(f"  {'Category':<45} {'Val':>6} {'Real':>6} {'Delta':>7}")
    print(f"  {'-'*66}")
    for cls in label_names:
        v = val_dist.get(cls, 0)
        r = real_dist.get(cls, 0)
        flag = " ⚠" if abs(r - v) > DISTRIBUTION_ALERT_THRESHOLD else ""
        print(f"  {cls:<45} {v:>5.1%} {r:>5.1%} {r-v:>+6.1%}{flag}")

    if dist_alerts:
        print(f"\n  ⚠ Distribution alerts:")
        for alert in dist_alerts:
            print(alert)

    # 2. Confidence
    conf = check_confidence(classified_df)
    print(f"\n  Confidence:")
    print(f"    Mean: {conf['mean']:.3f}, Median: {conf['median']:.3f}")
    print(f"    Below 50%: {conf['pct_below_50']:.1%}, Below 30%: {conf['pct_below_30']:.1%}")

    # 3. Drift
    texts = classified_df["text_clean"].tolist() if "text_clean" in classified_df.columns else []
    if texts:
        centroid_matrix = compute_centroids(train_df, train_emb, label_names)
        drift = check_drift(texts, centroid_matrix, label_names, model)
        print(f"\n  Embedding drift:")
        print(f"    Mean similarity: {drift['mean_similarity']:.3f}")
        print(f"    Min similarity:  {drift['min_similarity']:.3f}")
        if drift["n_flagged"] > 0:
            print(f"    ⚠ {drift['n_flagged']} articles flagged as out-of-distribution")
        else:
            print(f"    ✓ No drift detected")

    # Log — week_start/week_end stamp the window the run was scoped to
    # (set by pipeline.py via INFERENCE_SINCE/UNTIL env vars; blank for ad-hoc runs).
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "week_start": os.getenv("INFERENCE_SINCE", ""),
        "week_end": os.getenv("INFERENCE_UNTIL", ""),
        "n_articles": len(classified_df),
        "mean_confidence": conf["mean"],
        "pct_below_50": conf["pct_below_50"],
        "mean_similarity": drift["mean_similarity"] if texts else None,
        "n_drift_flagged": drift["n_flagged"] if texts else None,
    }
    for cls in label_names:
        log_entry[f"pct_{cls}"] = real_dist.get(cls, 0)

    log_path = DATA_DIR / "monitoring_log.csv"
    log_df = pd.DataFrame([log_entry])
    if log_path.exists():
        existing = pd.read_csv(log_path)
        log_df = pd.concat([existing, log_df], ignore_index=True)
    log_df.to_csv(log_path, index=False)
    print(f"\n  Monitoring log → {log_path}")

    _push_drift_log(conf, drift if texts else None, real_dist, label_names,
                    classified_df, dist_alerts)
    print("  Done.")


def _active_run_id() -> str:
    p = Path("models/runs/active.txt")
    return p.read_text().strip() if p.exists() else "unknown"


def _push_drift_log(conf, drift, real_dist, label_names, classified_df, dist_alerts):
    """Persist headline drift metrics to Supabase drift_log."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("  SUPABASE_URL/SUPABASE_SERVICE_KEY not set — skipping drift_log push.")
        return
    from supabase import create_client
    row = {
        "run_id": _active_run_id(),
        "batch_id": datetime.now().strftime("%Y-%m-%d_%H%M%S"),
        "week_start": os.getenv("INFERENCE_SINCE", "") or None,
        "week_end": os.getenv("INFERENCE_UNTIL", "") or None,
        "n_articles": int(len(classified_df)),
        "mean_confidence": float(conf["mean"]),
        "median_confidence": float(conf["median"]),
        "pct_below_50": float(conf["pct_below_50"]),
        "pct_below_30": float(conf["pct_below_30"]),
        "mean_similarity": float(drift["mean_similarity"]) if drift else None,
        "min_similarity": float(drift["min_similarity"]) if drift else None,
        "n_drift_flagged": int(drift["n_flagged"]) if drift else None,
        "class_distribution": {cls: float(real_dist.get(cls, 0)) for cls in label_names},
        "distribution_alerts": [a.strip() for a in dist_alerts] if dist_alerts else [],
    }
    create_client(url, key).table("drift_log").insert(row).execute()
    print("  Pushed drift_log row to Supabase.")


if __name__ == "__main__":
    main()
