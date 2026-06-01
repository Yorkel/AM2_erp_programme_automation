"""Dry-run helper for new WordPress sources.

Calls a WordPress adapter for a single source over a given date range, applies
the same relevance filter used in run.py::_postprocess (title-only HE filter
+ empty-text drop + URL dedupe — language flagging is intentionally skipped),
and prints RAW_COUNT, POST_FILTER_COUNT, and 5 sample titles. No CSV is
written.

Example:
    python dry_run_wp.py --source sutton_trust \
        --api-url https://www.suttontrust.com/wp-json/wp/v2 \
        --since 2023-01-01 --until 2025-12-31
"""

import argparse
from datetime import datetime

import pandas as pd

from scraping.wordpress_adapter import make_wp_scraper
from run import TITLE_HE_TERMS, TITLE_SCHOOL_TERMS


def _filter(df):
    """Apply run.py::_postprocess relevance rules (no language flagging)."""
    # 1. Drop empty text
    df = df.dropna(subset=["text"])
    df = df[df["text"].astype(str).str.strip() != ""]

    # 2. Title-only HE filter
    def _should_remove(title):
        t = str(title).lower()
        has_he = any(term in t for term in TITLE_HE_TERMS)
        if not has_he:
            return False
        has_school = any(term in t for term in TITLE_SCHOOL_TERMS)
        return not has_school

    df = df[~df["title"].apply(_should_remove)]

    # 3. Dedupe by URL
    df = df.drop_duplicates(subset=["url"])
    return df


def parse_args():
    parser = argparse.ArgumentParser(description="Dry-run a new WordPress source")
    parser.add_argument("--source", required=True, help="Source name (for logging)")
    parser.add_argument(
        "--api-url",
        required=True,
        help="WordPress REST API base URL (e.g. https://example.com/wp-json/wp/v2)",
    )
    parser.add_argument(
        "--since",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        default=datetime.strptime("2023-01-01", "%Y-%m-%d").date(),
    )
    parser.add_argument(
        "--until",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        default=datetime.strptime("2025-12-31", "%Y-%m-%d").date(),
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Normalise to the /posts endpoint that wordpress_adapter expects.
    api_url = args.api_url.rstrip("/")
    if not api_url.endswith("/posts"):
        api_url = api_url + "/posts"

    scraper = make_wp_scraper(api_url)
    rows = scraper(since_date=args.since, until_date=args.until)
    raw_count = len(rows) if rows else 0

    if raw_count == 0:
        print(f"SOURCE={args.source}")
        print(f"RAW_COUNT=0")
        print(f"POST_FILTER_COUNT=0")
        print("SAMPLE:")
        return

    df = pd.DataFrame(rows)
    filtered = _filter(df)
    post_count = len(filtered)

    print(f"SOURCE={args.source}")
    print(f"RAW_COUNT={raw_count}")
    print(f"POST_FILTER_COUNT={post_count}")
    print("SAMPLE:")
    for title in filtered["title"].head(5).tolist():
        print(f"TITLE: {title}")


if __name__ == "__main__":
    main()
