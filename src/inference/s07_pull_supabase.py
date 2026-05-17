"""
s07_pull_supabase.py
Pull weekly inference articles from Supabase.

Fetches England inference articles from the articles table,
saves locally for classification.

Input:  Supabase articles table (requires SUPABASE_URL + SUPABASE_SERVICE_KEY in .env)
Output: data/modelling/supabase_inference_articles.csv
"""

import os
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

# -----------------------------
# CONFIG
# -----------------------------
DATA_DIR = Path("data/modelling")
COUNTRY = "eng"
DATASET_TYPE = "inference"


def main():
    """Pull inference articles from Supabase."""
    load_dotenv()

    from supabase import create_client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        print("  ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
        return

    client = create_client(url, key)

    since = os.getenv("INFERENCE_SINCE")
    until = os.getenv("INFERENCE_UNTIL")

    # Pull articles (optionally bounded by article_date)
    q = (
        client.table("articles")
        .select("url, title, article_date, source, text_clean, week_number")
        .eq("country", COUNTRY)
        .eq("dataset_type", DATASET_TYPE)
    )
    if since:
        q = q.gte("article_date", since)
    if until:
        q = q.lte("article_date", until)
    response = q.order("article_date").execute()

    df = pd.DataFrame(response.data)
    window = f" [{since or '...'} → {until or '...'}]" if (since or until) else ""
    print(f"  Pulled {len(df)} articles from Supabase{window}")
    print(f"  Country: {COUNTRY}")
    if len(df):
        print(f"  Weeks: {df['week_number'].min()} to {df['week_number'].max()}")
        print(f"  Date range: {df['article_date'].min()} to {df['article_date'].max()}")

    # Drop missing text
    missing = df["text_clean"].isna() | (df["text_clean"].str.strip() == "")
    if missing.any():
        print(f"  Dropped {missing.sum()} articles with missing text")
        df = df[~missing]

    # Save
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DATA_DIR / "supabase_inference_articles.csv"
    df.to_csv(out_path, index=False)
    print(f"  Saved {len(df)} articles → {out_path}")
    print("  Done.")


if __name__ == "__main__":
    main()
