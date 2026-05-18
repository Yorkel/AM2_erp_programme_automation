"""
cleanup_existing_articles.py

Apply the current scraper filter retroactively to articles already in Supabase.
Identifies rows that would be rejected under the new filter rules and
(optionally) deletes them along with their predictions.

Defaults to DRY RUN — prints what would happen and writes a CSV report,
makes no changes. Pass --apply to actually delete.

By default skips weeks 19 + 20 (those are being re-scraped instead).

Usage:
  python -m src.scraping.cleanup_existing_articles
  python -m src.scraping.cleanup_existing_articles --apply
  python -m src.scraping.cleanup_existing_articles --exclude-weeks 20 --apply
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from src.scraping.relevance import (
    DEFAULT_EDUCATION_KEYWORDS,
    compile_keyword_patterns,
    is_blocked_domain,
    is_blocked_url_pattern,
    is_non_uk_content,
)

ARCHIVE_DIR = Path("data/archive/cleanup")
DELETE_BATCH = 200


def classify_row(row, edu_patterns) -> str | None:
    """Return rejection reason if the row would be filtered, else None."""
    url = row.get("url") or ""
    title = (row.get("title") or "")
    title_l = title.lower()
    body = row.get("text_clean") or ""
    if is_blocked_domain(url):
        return "blocked_domain"
    if is_blocked_url_pattern(url):
        return "blocked_url_pattern"
    non_uk = is_non_uk_content(title, body)
    if non_uk:
        return f"non_uk:{non_uk}"
    if not any(p.search(title_l) for p in edu_patterns):
        return "no_edu_keyword_in_title"
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                        help="Actually delete from Supabase (default is dry-run).")
    parser.add_argument("--exclude-weeks", nargs="*", type=int, default=[19, 20],
                        help="Week numbers to skip (re-scraped separately). "
                             "Default: 19 20")
    args = parser.parse_args()

    load_dotenv()
    from supabase import create_client
    client = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_KEY"),
    )

    print(f"Pulling articles from Supabase "
          f"(excluding weeks {args.exclude_weeks})...")
    resp = (
        client.table("articles")
        .select("url, title, text_clean, source, week_number")
        .execute()
    )
    df = pd.DataFrame(resp.data)
    print(f"  Pulled {len(df)} articles total")

    if args.exclude_weeks:
        before = len(df)
        df = df[~df["week_number"].isin(args.exclude_weeks)].copy()
        print(f"  Excluded {before - len(df)} from weeks {args.exclude_weeks} "
              f"→ {len(df)} candidates")

    edu_patterns = compile_keyword_patterns(DEFAULT_EDUCATION_KEYWORDS)

    df["reject_reason"] = df.apply(
        lambda r: classify_row(r, edu_patterns), axis=1
    )
    to_delete = df[df["reject_reason"].notna()].copy()

    pct = (len(to_delete) / len(df) * 100) if len(df) else 0
    print(f"\n  Would delete: {len(to_delete)} of {len(df)} ({pct:.1f}%)")

    if len(to_delete):
        print("\n  By reason:")
        for reason, count in to_delete["reject_reason"].value_counts().items():
            print(f"    {reason:<35} {count:>5}")
        print("\n  Sample (first 15):")
        sample = (
            to_delete[["week_number", "source", "title", "reject_reason"]]
            .head(15)
            .to_string(index=False)
        )
        print("    " + sample.replace("\n", "\n    "))

    # Always write the report so user can eyeball outside the terminal
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    batch_id = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    report_path = ARCHIVE_DIR / f"{batch_id}_would_delete.csv"
    to_delete[["url", "title", "source", "week_number", "reject_reason"]].to_csv(
        report_path, index=False
    )
    print(f"\n  Report: {report_path}")

    if not args.apply:
        print("\n  DRY RUN — no changes made. Re-run with --apply to delete.")
        return 0

    if not len(to_delete):
        print("\n  Nothing to delete.")
        return 0

    urls = to_delete["url"].tolist()
    print(f"\n  Deleting {len(urls)} articles + their predictions...")
    # Predictions first to satisfy FK constraint
    for i in range(0, len(urls), DELETE_BATCH):
        batch = urls[i:i + DELETE_BATCH]
        client.table("classify_newsletter").delete().in_("url", batch).execute()
        print(f"    classify_newsletter batch {i // DELETE_BATCH + 1}: "
              f"{len(batch)} rows")
    for i in range(0, len(urls), DELETE_BATCH):
        batch = urls[i:i + DELETE_BATCH]
        client.table("articles").delete().in_("url", batch).execute()
        print(f"    articles batch {i // DELETE_BATCH + 1}: {len(batch)} rows")
    print(f"  Done. Deleted {len(urls)} articles.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
