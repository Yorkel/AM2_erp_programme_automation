"""
run.py
Orchestrator. Iterates every enabled source in sources.yml, runs each,
upserts into Supabase articles_topics, and logs one scrape_runs row per source.

Modes:

  # Twice-weekly incremental run (cron path)
  python -m src.scraping.run --since 2026-05-12 --until 2026-05-15

  # Backfill — same code path, just a long --since
  python -m src.scraping.run --since 2023-01-01

  # Single source (debugging — but try_source.py is usually better)
  python -m src.scraping.run --source wonkhe_newsletter --since 2026-05-12

  # Dry run — runs scrapers, prints counts, never writes to Supabase
  python -m src.scraping.run --since 2026-05-12 --dry-run
"""

from __future__ import annotations

import argparse
import importlib
import traceback
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from pathlib import Path

from src.scraping.common import Article
from src.scraping.config import load_sources
from src.scraping.supabase_client import (
    get_client,
    log_run,
    new_run_id,
    upsert_articles,
)


def _to_records(items) -> list[dict]:
    out: list[dict] = []
    for r in items:
        if isinstance(r, Article):
            out.append(r.to_record())
        elif is_dataclass(r):
            out.append(asdict(r))
        elif isinstance(r, dict):
            out.append(r)
    return out


def _scrape_one(src: dict, *, since: date | None, until: date | None) -> list:
    params = dict(src.get("params") or {})
    params.setdefault("source", src["name"])
    params["since_date"] = since
    params["until_date"] = until

    if src["type"] == "newsletter":
        ingestion = src.get("ingestion", "disk")
        if ingestion == "disk":
            mod = importlib.import_module("src.scraping.newsletters.from_disk")
        elif ingestion == "gmail":
            mod = importlib.import_module("src.scraping.newsletters.gmail")
        else:
            raise RuntimeError(f"unknown newsletter ingestion '{ingestion}'")
        return mod.scrape(**params)

    if src["type"] == "web":
        scraper_path = src.get("scraper")
        if not scraper_path:
            raise RuntimeError(f"web source {src['name']} must specify 'scraper'")
        mod = importlib.import_module(scraper_path)
        return mod.scrape(**params)

    if src["type"] in ("rss", "google_alert"):
        scraper_path = src.get("scraper") or "src.scraping.rss_adapter"
        mod = importlib.import_module(scraper_path)
        return mod.scrape(**params)

    raise RuntimeError(f"unknown source type {src['type']}")


def _weekly_windows(start: date, end: date) -> list[tuple[date, date]]:
    """Yield (since, until) tuples, each a Tuesday-anchored 7-day week, walking forward."""
    # Snap to the Tuesday on/before `start`
    days_to_tue = (start.weekday() - 1) % 7  # Mon=0, Tue=1; snap back to Tue
    from datetime import timedelta
    cur = start - timedelta(days=days_to_tue)
    weeks: list[tuple[date, date]] = []
    while cur <= end:
        week_end = cur + timedelta(days=6)
        if week_end > end:
            week_end = end
        weeks.append((cur, week_end))
        cur = cur + timedelta(days=7)
    return weeks


def main():
    parser = argparse.ArgumentParser(description="AM2 scraping orchestrator")
    parser.add_argument("--since", type=lambda s: date.fromisoformat(s), default=None,
                        help="Earliest article_date to include")
    parser.add_argument("--until", type=lambda s: date.fromisoformat(s), default=None,
                        help="Latest article_date to include")
    parser.add_argument("--source", default=None,
                        help="Run a single named source; default = all enabled")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run scrapers and print counts; do not write to Supabase")
    parser.add_argument("--sources-yml", default=None,
                        help="Path to sources.yml (defaults to src/scraping/sources.yml)")
    parser.add_argument("--weekly-backfill", action="store_true",
                        help="Iterate Tuesday-anchored 7-day weeks from --since to --until, "
                             "one run per week. Use with --since to walk weeks forward.")
    parser.add_argument("--since-last-run", action="store_true",
                        help="Set --since to the started_at of the most recent successful "
                             "scrape_runs row, or 7 days ago if no previous run exists. "
                             "Used by the cron workflow for incremental fetches.")
    args = parser.parse_args()

    # Resolve --since-last-run BEFORE other logic so it sets args.since.
    if args.since_last_run:
        if args.since:
            raise SystemExit("--since-last-run and --since are mutually exclusive")
        from datetime import timedelta
        try:
            client = get_client()
            resp = (client.table("scrape_runs")
                    .select("started_at")
                    .eq("status", "ok")
                    .order("started_at", desc=True)
                    .limit(1)
                    .execute())
            if resp.data:
                last_ts = resp.data[0]["started_at"][:10]
                args.since = date.fromisoformat(last_ts)
                print(f"--since-last-run: last successful run was {last_ts}, using as --since")
            else:
                args.since = date.today() - timedelta(days=7)
                print(f"--since-last-run: no previous successful run, defaulting to 7 days ago ({args.since})")
        except Exception as e:
            args.since = date.today() - timedelta(days=7)
            print(f"--since-last-run: lookup failed ({e}); defaulting to 7 days ago ({args.since})")

    # Weekly-backfill mode: split [--since, --until] into Tuesday-anchored weeks and
    # invoke the per-source loop once per week. Useful for staged backfill.
    if args.weekly_backfill:
        if not args.since:
            raise SystemExit("--weekly-backfill requires --since")
        end = args.until or date.today()
        weeks = _weekly_windows(args.since, end)
        print(f"weekly-backfill: {len(weeks)} week(s) from {args.since} to {end}")
        # Recursively call this run per week, mutating args.since/args.until each iteration
        for wk_since, wk_until in weeks:
            print(f"\n{'='*60}\nWEEK: {wk_since} → {wk_until}\n{'='*60}")
            args.since = wk_since
            args.until = wk_until
            args.weekly_backfill = False
            _execute_run(args)
        return

    _execute_run(args)


def _execute_run(args):
    """The actual orchestrator loop, extracted so weekly-backfill can call it per week."""

    sources = load_sources(Path(args.sources_yml) if args.sources_yml else None)
    if args.source:
        sources = [s for s in sources if s["name"] == args.source]
        if not sources:
            raise SystemExit(f"source '{args.source}' not found / disabled in sources.yml")

    if not sources:
        print("no sources configured. Add entries to src/scraping/sources.yml")
        return

    client = None if args.dry_run else get_client()
    run_id = new_run_id()
    print(f"run_id={run_id} sources={len(sources)} since={args.since} until={args.until} dry_run={args.dry_run}")

    total_scraped = 0
    total_upserted = 0
    failures: list[str] = []

    for src in sources:
        name = src["name"]
        stype = src["type"]
        print(f"\n--- {name} ({stype}) ---")
        started = datetime.now()
        rows_scraped = 0
        rows_upserted = 0
        status = "ok"
        error: str | None = None
        try:
            items = _scrape_one(src, since=args.since, until=args.until)
            records = _to_records(items)
            rows_scraped = len(records)
            rows_upserted = upsert_articles(
                client, records, label=name, dry_run=args.dry_run,
            ) if records else 0
        except Exception as e:
            status = "failed"
            error = f"{type(e).__name__}: {e}"
            print(f"  FAILED: {error}")
            traceback.print_exc()
            failures.append(name)
        finally:
            finished = datetime.now()
            if client is not None:
                log_run(
                    client,
                    run_id=run_id, source=name, source_type=stype,
                    since_date=args.since, until_date=args.until,
                    started_at=started, finished_at=finished,
                    rows_scraped=rows_scraped, rows_upserted=rows_upserted,
                    status=status, error=error,
                    dry_run=args.dry_run,
                )
            total_scraped += rows_scraped
            total_upserted += rows_upserted

    print(f"\n=== run {run_id} done ===")
    print(f"sources={len(sources)} scraped={total_scraped} upserted={total_upserted} failed={len(failures)}")
    if failures:
        print(f"failed sources: {', '.join(failures)}")


if __name__ == "__main__":
    main()
