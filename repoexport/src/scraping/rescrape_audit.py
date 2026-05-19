"""
rescrape_audit.py

Take a snapshot of articles in given weeks (before deletion), then later
diff against a second snapshot (after re-scrape) to record what changed.

Two modes:

  snapshot — pull the current rows from Supabase for given weeks and save
             them to data/archive/rescrape_audit/<timestamp>_<label>.csv

  diff     — compare two snapshot CSVs and print:
             - URLs only in BEFORE (dropped by re-scrape)
             - URLs only in AFTER (newly recovered)
             - URLs in both (kept)
             Plus a CSV summary at data/archive/rescrape_audit/<timestamp>_diff.csv

Usage:
  # Step 1 — capture state before deletion
  python -m src.scraping.rescrape_audit snapshot --weeks 19 20 --label before

  # …delete + re-scrape happens via Supabase SQL + GH Actions…

  # Step 2 — capture state after re-scrape
  python -m src.scraping.rescrape_audit snapshot --weeks 19 20 --label after

  # Step 3 — compare
  python -m src.scraping.rescrape_audit diff \\
      data/archive/rescrape_audit/<TS1>_before.csv \\
      data/archive/rescrape_audit/<TS2>_after.csv
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ARCHIVE_DIR = Path("data/archive/rescrape_audit")


def _client():
    from supabase import create_client
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"],
    )


def snapshot(weeks: list[int], label: str) -> Path:
    client = _client()
    print(f"Pulling weeks {weeks} from Supabase...")
    resp = (
        client.table("articles")
        .select("url, title, source, article_date, week_number, country, dataset_type")
        .in_("week_number", weeks)
        .execute()
    )
    df = pd.DataFrame(resp.data)
    print(f"  {len(df)} rows")
    print("\n  By source:")
    for src, n in df["source"].value_counts().items():
        print(f"    {src:<45} {n:>4}")

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out = ARCHIVE_DIR / f"{ts}_{label}.csv"
    df.to_csv(out, index=False)
    print(f"\n  Saved → {out}")
    return out


def diff(before_csv: Path, after_csv: Path) -> Path:
    before = pd.read_csv(before_csv).set_index("url")
    after = pd.read_csv(after_csv).set_index("url")

    only_before = before.loc[before.index.difference(after.index)]
    only_after = after.loc[after.index.difference(before.index)]
    in_both = before.index.intersection(after.index)

    print(f"\nBEFORE: {len(before)} articles")
    print(f"AFTER:  {len(after)} articles")
    print(f"\n  Dropped (in BEFORE only): {len(only_before)}")
    print(f"  Added   (in AFTER only):  {len(only_after)}")
    print(f"  Kept    (in both):        {len(in_both)}")

    if len(only_before):
        print("\n  Dropped — top sources:")
        for src, n in only_before["source"].value_counts().head(10).items():
            print(f"    {src:<45} {n:>4}")
        print("\n  Dropped — sample titles:")
        for t in only_before["title"].head(15).tolist():
            print(f"    - {t}")

    if len(only_after):
        print("\n  Added — top sources:")
        for src, n in only_after["source"].value_counts().head(10).items():
            print(f"    {src:<45} {n:>4}")
        print("\n  Added — sample titles:")
        for t in only_after["title"].head(15).tolist():
            print(f"    - {t}")

    # Combined CSV for the record
    only_before = only_before.assign(change="dropped").reset_index()
    only_after = only_after.assign(change="added").reset_index()
    combined = pd.concat([only_before, only_after], ignore_index=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out = ARCHIVE_DIR / f"{ts}_diff.csv"
    combined.to_csv(out, index=False)
    print(f"\n  Diff CSV → {out}")
    return out


def main() -> int:
    load_dotenv()
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="mode", required=True)

    p_snap = sub.add_parser("snapshot")
    p_snap.add_argument("--weeks", nargs="+", type=int, required=True)
    p_snap.add_argument("--label", default="snapshot",
                        help="Tag for the filename (e.g. 'before' / 'after')")

    p_diff = sub.add_parser("diff")
    p_diff.add_argument("before_csv", type=Path)
    p_diff.add_argument("after_csv", type=Path)

    args = p.parse_args()
    if args.mode == "snapshot":
        snapshot(args.weeks, args.label)
    else:
        diff(args.before_csv, args.after_csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
