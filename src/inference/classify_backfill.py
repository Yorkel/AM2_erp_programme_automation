"""
classify_backfill.py

Re-classify all inference articles in Supabase, iterating week by week.
Pulls each week's rows, calls the deployed classifier API, saves per-week
snapshots to data/modelling/weekly/, and writes a combined
classified_articles.csv for the existing s10 push step to consume.

Usage:
    python -m src.inference.classify_backfill
    python -m src.inference.s10_push_supabase   # then push to Supabase
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

from src.inference.classify_via_api import classify, summarise

DATA_DIR = Path("data/modelling")
WEEKLY_DIR = DATA_DIR / "weekly"


def main() -> int:
    load_dotenv()
    client = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_KEY"),
    )

    weeks_resp = (
        client.table("articles")
        .select("week_number")
        .eq("country", "eng")
        .eq("dataset_type", "inference")
        .execute()
    )
    weeks = sorted({r["week_number"] for r in weeks_resp.data
                    if r["week_number"] is not None})
    print(f"Found {len(weeks)} weeks to classify: {weeks}")

    WEEKLY_DIR.mkdir(parents=True, exist_ok=True)
    all_classified: list[pd.DataFrame] = []

    for w in weeks:
        print(f"\n=== Week {w:02d} ===")
        resp = (
            client.table("articles")
            .select("url, title, article_date, source, text_clean, week_number")
            .eq("country", "eng")
            .eq("dataset_type", "inference")
            .eq("week_number", w)
            .execute()
        )
        df = pd.DataFrame(resp.data)
        if df.empty:
            print(f"  No articles for week {w}, skipping.")
            continue
        print(f"  {len(df)} articles in week {w}")

        input_path = DATA_DIR / f"_week_{w:02d}_input.csv"
        df.to_csv(input_path, index=False)
        try:
            classified = classify(input_path, batch_size=50)
        finally:
            input_path.unlink(missing_ok=True)

        out = WEEKLY_DIR / f"classified_week_{w:02d}.csv"
        classified.to_csv(out, index=False)
        print(f"  Saved → {out}")
        summarise(classified)
        all_classified.append(classified)

    if all_classified:
        combined = pd.concat(all_classified, ignore_index=True)
        full_out = DATA_DIR / "classified_articles.csv"
        combined.to_csv(full_out, index=False)
        print(f"\nCombined {len(combined)} predictions → {full_out}")
        print("Next: python -m src.inference.s10_push_supabase")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
