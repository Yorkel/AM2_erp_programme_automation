"""
s10_push_supabase.py
Push classified articles back to Supabase and save weekly archive locally.

Upserts results to the classify_newsletter table.
Uses URL as unique key — re-running won't create duplicates.
Saves a per-week CSV locally for historical tracking.

Input:  data/modelling/classified_articles.csv (from s08_predict)
Output: Supabase classify_newsletter table
        data/modelling/weekly/week_N_classified.csv
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# -----------------------------
# CONFIG
# -----------------------------
DATA_DIR = Path("data/modelling")
TABLE_NAME = "classify_newsletter"
INPUT_CSV = DATA_DIR / "classified_articles.csv"


def main():
    """Push classified articles to Supabase."""
    load_dotenv()

    from supabase import create_client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        print("  ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
        return

    if not INPUT_CSV.exists():
        print(f"  ERROR: {INPUT_CSV} not found. Run s08_predict.py first.")
        return

    client = create_client(url, key)

    # Load classified articles
    df = pd.read_csv(INPUT_CSV)
    print(f"  Loaded {len(df)} classified articles from {INPUT_CSV}")

    # Save weekly archive locally
    weekly_dir = DATA_DIR / "weekly"
    weekly_dir.mkdir(parents=True, exist_ok=True)
    if "week_number" in df.columns and df["week_number"].notna().any():
        for week in sorted(df["week_number"].dropna().unique()):
            week_df = df[df["week_number"] == week]
            weekly_path = weekly_dir / f"week_{int(week)}_classified.csv"
            week_df.to_csv(weekly_path, index=False)
            print(f"  Saved week {int(week)} ({len(week_df)} articles) → {weekly_path}")
    else:
        all_path = weekly_dir / f"classified_{datetime.now().strftime('%Y%m%d')}.csv"
        df.to_csv(all_path, index=False)
        print(f"  Saved → {all_path}")

    # Prepare rows for upsert — lean schema (A2) plus scoring (migration 006).
    # Article metadata (title, source, article_date, week_number, text_clean) lives
    # in the articles table and is joined in via the v_dashboard view.
    now = datetime.now().isoformat()
    rows = []
    for _, row in df.iterrows():
        def _num(col):
            v = row.get(col)
            return float(v) if pd.notna(v) else None

        record = {
            "url": row.get("url"),
            "top1": row["top1"],
            "top1_confidence": float(row["top1_confidence"]),
            "top2": row.get("top2"),
            "top2_confidence": _num("top2_confidence"),
            "confidence_gap": _num("confidence_gap"),
            "classified_at": now,
            # Scoring columns (migration 006). Populated by `scoring` pipeline step.
            "cluster_id":       int(row["cluster_id"]) if pd.notna(row.get("cluster_id")) else None,
            "cluster_size":     int(row["cluster_size"]) if pd.notna(row.get("cluster_size")) else None,
            "is_cluster_lead":  bool(row["is_cluster_lead"]) if pd.notna(row.get("is_cluster_lead")) else None,
            "source_authority": _num("source_authority"),
            "recency_score":    _num("recency_score"),
            "substance_score":  _num("substance_score"),
            "composite_score":  _num("composite_score"),
        }
        rows.append(record)

    # Upsert in batches (Supabase has a row limit per request)
    BATCH_SIZE = 100
    total_upserted = 0

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        response = (
            client.table(TABLE_NAME)
            .upsert(batch, on_conflict="url")
            .execute()
        )
        total_upserted += len(batch)
        print(f"  Upserted batch {i // BATCH_SIZE + 1}: {len(batch)} rows")

    print(f"\n  Total upserted: {total_upserted} rows to {TABLE_NAME}")
    print("  Done.")


if __name__ == "__main__":
    main()
