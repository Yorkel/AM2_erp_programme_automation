"""
backfill_drift_log.py

One-off: populate the (previously empty) `drift_log` table with one row per
scrape-week, computed from the live classified data. drift_log was empty because
the drift.yml "Run drift monitor" step never had the Supabase env block, so every
production run silently skipped the push (fixed 2026-06-11). Going forward s09 writes
one row per run; this backfills the history so the §12 review surface has a trend.

Reuses s09_monitor's metric functions for an apples-to-apples result.

Usage:  python -m src.inference.backfill_drift_log
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from supabase import create_client

from src.inference.s09_monitor import (
    MODEL_NAME, _active_run_dir, _active_run_id,
    check_confidence, check_distribution, check_drift,
)
import json

LIVE_CSV = Path("data/modelling/inference_classified_live.csv")


def main() -> int:
    load_dotenv()
    url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("  SUPABASE_URL/SUPABASE_SERVICE_KEY not set — aborting.")
        return 1
    client = create_client(url, key)

    df = pd.read_csv(LIVE_CSV)
    df["article_date"] = pd.to_datetime(df["article_date"])

    run_dir = _active_run_dir()
    baselines = json.loads((run_dir / "baselines.json").read_text())
    label_names = baselines["label_names"]
    val_dist = pd.Series(baselines["val_distribution"])
    centroids = np.load(run_dir / "centroids.npy")
    model = SentenceTransformer(MODEL_NAME)
    run_id = _active_run_id()

    # idempotent: clear any prior backfill rows
    client.table("drift_log").delete().like("batch_id", "backfill_%").execute()

    weeks = sorted(df["week_number"].dropna().astype(int).unique())
    print(f"Backfilling drift_log for {len(weeks)} weeks: {weeks[0]}-{weeks[-1]}")
    rows = []
    for w in weeks:
        dfw = df[df["week_number"] == w]
        if len(dfw) < 3:                       # too few to be meaningful
            print(f"  week {w}: {len(dfw)} articles — skipped (too thin)")
            continue
        conf = check_confidence(dfw)
        _, real_dist, alerts = check_distribution(dfw, val_dist, label_names)
        texts = dfw["text_clean"].fillna("").tolist()
        drift = check_drift(texts, centroids, label_names, model)
        rows.append({
            "run_id": run_id,
            "batch_id": f"backfill_w{int(w):02d}",
            "week_start": str(dfw["article_date"].min().date()),
            "week_end": str(dfw["article_date"].max().date()),
            "n_articles": int(len(dfw)),
            "mean_confidence": float(conf["mean"]),
            "median_confidence": float(conf["median"]),
            "pct_below_50": float(conf["pct_below_50"]),
            "pct_below_30": float(conf["pct_below_30"]),
            "mean_similarity": float(drift["mean_similarity"]),
            "min_similarity": float(drift["min_similarity"]),
            "n_drift_flagged": int(drift["n_flagged"]),
            "class_distribution": {c: float(real_dist.get(c, 0)) for c in label_names},
            "distribution_alerts": [a.strip() for a in alerts] if alerts else [],
        })
        print(f"  week {int(w):02d}: n={len(dfw):3d}  conf={conf['mean']:.3f}  "
              f"sim={drift['mean_similarity']:.3f}  ood={drift['n_flagged']}")

    if rows:
        client.table("drift_log").insert(rows).execute()
    print(f"\nInserted {len(rows)} weekly drift_log rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
