"""backfill_bodies.py — one-off cleanup for articles stored with only a headline.

The forward fix (`_backfill_bodies` in run.py) only helps NEW scrapes. This
script cleans up articles ALREADY in `articles` whose `text` is empty or
headline-short (and which therefore show "Summary unavailable" on the
dashboard). For each, it fetches the URL, extracts the main body, and — if it
gets a meaningfully longer body — updates `text` + `text_clean` and regenerates
the summary + tags via Claude.

Sites that hard-block (e.g. Belfast Telegraph 403s) are skipped and left as-is;
they can't be summarised without heavier tooling.

Mirrors sweep_summaries.py in shape (Supabase + reused Anthropic client).

Env required:
  SUPABASE_URL
  SUPABASE_SERVICE_KEY  (write access)
  ANTHROPIC_API_KEY

Run:
  python -m src.scraping.backfill_bodies --dry-run          # report only
  python -m src.scraping.backfill_bodies                    # fix everything
  python -m src.scraping.backfill_bodies --lookback-days 30 # limit by recency
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv
from supabase import create_client

from src.scraping.common import build_text_clean, extract_body_text, soup_of
from src.scraping.run import MIN_BODY_CHARS
from src.inference.summarise import summarise_article, tag_article


def _fetch_candidates(client, lookback_days: int | None) -> list[dict]:
    """Pull articles whose stored body is headline-short (< MIN_BODY_CHARS).

    Filtering on text length is done in Python (Supabase has no clean length
    predicate). Optionally restrict to articles scraped within `lookback_days`.
    """
    rows: list[dict] = []
    off = 0
    q_cols = "id, url, title, text, summary, topic_tags, geographic_focus, source, scraped_at"
    cutoff_iso = None
    if lookback_days is not None:
        cutoff = datetime.now(timezone.utc).timestamp() - lookback_days * 86400
        cutoff_iso = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()
    while True:
        q = client.table("articles").select(q_cols)
        if cutoff_iso:
            q = q.gte("scraped_at", cutoff_iso)
        r = q.range(off, off + 999).execute()
        batch = r.data or []
        rows.extend(batch)
        if len(batch) < 1000:
            break
        off += 1000
    return [r for r in rows if len((r.get("text") or "").strip()) < MIN_BODY_CHARS]


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-fetch missing article bodies + re-summarise")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would change; write nothing")
    parser.add_argument("--lookback-days", type=int, default=None,
                        help="Only consider articles scraped within N days (default: all)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Cap the number of articles processed (debugging)")
    args = parser.parse_args()

    load_dotenv()
    sup_url = os.environ.get("SUPABASE_URL")
    sup_key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if not (sup_url and sup_key):
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set", file=sys.stderr)
        return 1
    if not anthropic_key and not args.dry_run:
        print("ERROR: ANTHROPIC_API_KEY must be set (or use --dry-run)", file=sys.stderr)
        return 1
    client = create_client(sup_url, sup_key)

    ant_client = None
    if not args.dry_run:
        from anthropic import Anthropic
        ant_client = Anthropic(max_retries=5)

    candidates = _fetch_candidates(client, args.lookback_days)
    if args.limit:
        candidates = candidates[: args.limit]
    print(f"Headline-short articles found (text < {MIN_BODY_CHARS} chars): {len(candidates)}")
    if not candidates:
        print("Nothing to backfill — exiting clean.")
        return 0

    n_fetched = 0       # got a longer body
    n_unreachable = 0   # 403 / timeout
    n_no_improve = 0    # fetched but body no better than what we had
    n_resummarised = 0
    n_sum_fail = 0

    for row in candidates:
        url = row.get("url") or ""
        old_len = len((row.get("text") or "").strip())
        if not url:
            continue
        soup = soup_of(url)
        if soup is None:
            n_unreachable += 1
            print(f"  unreachable: {url}")
            continue
        body = extract_body_text(soup)
        if len(body.strip()) <= old_len:
            n_no_improve += 1
            continue

        n_fetched += 1
        title = row.get("title") or ""
        update: dict = {
            "text": body,
            "text_clean": build_text_clean(title, body),
        }
        if args.dry_run:
            print(f"  would fix ({old_len}->{len(body.strip())} chars): {url}")
            continue

        # Regenerate summary + tags from the real body now we have it.
        try:
            update["summary"] = summarise_article(
                title=title, text=body, category=None, client=ant_client,
            )
            update["summary_generated_at"] = datetime.utcnow().isoformat()
            n_resummarised += 1
        except Exception as e:
            n_sum_fail += 1
            print(f"  summary failed for {url}: {type(e).__name__}: {e}", file=sys.stderr)
        try:
            tags = tag_article(title=title, text=body, client=ant_client)
            if tags.get("geographic_focus") or tags.get("topic_tags"):
                update["geographic_focus"] = tags.get("geographic_focus") or None
                update["topic_tags"] = tags.get("topic_tags") or None
        except Exception as e:
            print(f"  tags failed for {url}: {type(e).__name__}: {e}", file=sys.stderr)

        try:
            client.table("articles").update(update).eq("id", row["id"]).execute()
            print(f"  fixed ({old_len}->{len(body.strip())} chars): {url}")
        except Exception as e:
            print(f"  DB update failed for {url}: {type(e).__name__}: {e}", file=sys.stderr)

    print(
        f"\nDone: {n_fetched} bodies fetched"
        f"{' (dry-run, nothing written)' if args.dry_run else f', {n_resummarised} re-summarised'}"
        f"; {n_unreachable} unreachable, {n_no_improve} no improvement"
        + (f", {n_sum_fail} summary failures" if n_sum_fail else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
