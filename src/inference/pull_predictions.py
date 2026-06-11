"""
pull_predictions.py

Pull the joined article+prediction view (v_dashboard) from Supabase and
write it to data/modelling/classified_articles.csv. Used by drift.yml and
fairness.yml GitHub Actions workflows so they can run standalone — without
needing the artifact produced by classify.yml.

Note: `model_run_id` is not stored in `classify_newsletter`. Downstream tools
(s09_monitor, fairness_audit) fall back to `models/runs/active.txt` when the
column is absent.

Usage:
  python -m src.inference.pull_predictions
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

DATA_DIR = Path("data/modelling")
OUTPUT = DATA_DIR / "classified_articles.csv"
UK_NATIONS = ("eng", "sco", "wal", "nir", "uk")  # all UK nations (was England-only)


def main() -> int:
    load_dotenv()
    from supabase import create_client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("  ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")
        return 1

    client = create_client(url, key)
    resp = (
        client.table("v_dashboard")
        .select(
            "url, title, source, country, article_date, week_number, "
            "text_clean, top1, top1_confidence, top2, top2_confidence"
        )
        .in_("country", UK_NATIONS)
        .execute()
    )

    df = pd.DataFrame(resp.data)
    df = df.dropna(subset=["top1"])
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT, index=False)
    print(f"  Pulled {len(df)} classified rows → {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
