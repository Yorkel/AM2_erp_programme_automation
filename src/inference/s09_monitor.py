"""
s09_monitor.py
Production monitoring for the classification pipeline.

Compares new predictions against pre-computed val baselines:
- Prediction distribution shift
- Confidence score drift
- Embedding drift (cosine similarity to pre-computed training centroids)

Inputs (all in repo — no train.csv / val.csv at runtime):
  data/modelling/classified_articles.csv             (from classify_via_api)
  models/runs/<active>/centroids.npy                 (precomputed; see precompute_baselines.py)
  models/runs/<active>/baselines.json                (precomputed)
Output: data/modelling/monitoring_log.csv + drift_log row in Supabase
"""

import json
import os

from dotenv import load_dotenv

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

MODEL_NAME = "all-MiniLM-L6-v2"
MODEL_DIR = Path("models")
DATA_DIR = Path("data/modelling")
DRIFT_THRESHOLD = 0.3
DISTRIBUTION_ALERT_THRESHOLD = 0.10


def _active_run_dir() -> Path:
    active = (MODEL_DIR / "runs" / "active.txt").read_text().strip()
    return MODEL_DIR / "runs" / active


def check_distribution(classified_df, val_dist, label_names):
    """Compare prediction distribution against the pre-computed val baseline.
    `val_dist` is a Series indexed by label name with proportion values."""
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
    load_dotenv()
    # Load
    classified_path = DATA_DIR / "classified_articles.csv"
    if not classified_path.exists():
        print(f"  No classified articles found at {classified_path}")
        print("  Run s07_predict.py first.")
        return

    classified_df = pd.read_csv(classified_path)

    # Load pre-computed baselines (committed under models/runs/<active>/)
    run_dir = _active_run_dir()
    baselines = json.loads((run_dir / "baselines.json").read_text())
    label_names = baselines["label_names"]
    val_dist = pd.Series(baselines["val_distribution"])
    centroid_matrix = np.load(run_dir / "centroids.npy")
    model = SentenceTransformer(MODEL_NAME)

    print(f"\n{'='*60}")
    print(f"  Monitoring Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Articles: {len(classified_df)}")
    print(f"{'='*60}")

    # 1. Distribution
    val_dist, real_dist, dist_alerts = check_distribution(classified_df, val_dist, label_names)
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

    # 3. Drift — uses pre-computed centroids loaded above
    texts = classified_df["text_clean"].tolist() if "text_clean" in classified_df.columns else []
    if texts:
        drift = check_drift(texts, centroid_matrix, label_names, model)
        print(f"\n  Embedding drift:")
        print(f"    Mean similarity: {drift['mean_similarity']:.3f}")
        print(f"    Min similarity:  {drift['min_similarity']:.3f}")
        if drift["n_flagged"] > 0:
            print(f"    ⚠ {drift['n_flagged']} articles flagged as out-of-distribution")
        else:
            print(f"    ✓ No drift detected")

    # ── RAG status for alert routing (green=log only, amber=digest, red=action) ──
    ood_rate = (drift["n_flagged"] / len(classified_df)) if texts and len(classified_df) else 0.0
    max_delta = max((abs(real_dist.get(c, 0) - val_dist.get(c, 0)) for c in label_names), default=0.0)
    reasons = []
    if conf["mean"] < 0.40:
        reasons.append(f"mean confidence {conf['mean']:.3f} < 0.40 (retrain floor)")
    if max_delta > 0.15:
        reasons.append(f"class-mix shift {max_delta:.0%} > 15%")
    if ood_rate > 0.15:
        reasons.append(f"out-of-distribution {ood_rate:.0%} > 15%")
    if reasons:
        status = "RED"
    elif dist_alerts or conf["pct_below_50"] > 0.70 or ood_rate > 0.05:
        status = "AMBER"
        if dist_alerts:
            reasons.append(f"{len(dist_alerts)} class-mix alert(s) >10%")
        if conf["pct_below_50"] > 0.70:
            reasons.append(f"{conf['pct_below_50']:.0%} below 0.5 confidence")
        if ood_rate > 0.05:
            reasons.append(f"out-of-distribution {ood_rate:.0%}")
    else:
        status = "GREEN"
    print(f"\n  MONITOR STATUS: {status}"
          + (f" — {'; '.join(reasons)}" if reasons else " — all signals nominal"))

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
        msg = "SUPABASE_URL/SUPABASE_SERVICE_KEY not set — cannot push drift_log."
        if os.getenv("GITHUB_ACTIONS") or os.getenv("CI"):
            raise RuntimeError(msg + " Refusing to exit 0 in CI — add the env block to the workflow step.")
        print("  " + msg + " Skipping (local run).")
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
