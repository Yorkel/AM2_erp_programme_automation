"""
supabase_client.py
Thin Supabase wrapper. Two responsibilities:
  - get_client(): build a Supabase client from .env (SUPABASE_URL + SUPABASE_SERVICE_KEY)
  - upsert_articles(): batched upsert into articles with on_conflict=url
  - log_run(): one row in scrape_runs per source per orchestrator run

Lifted/stripped from atlas-ed-data's seed_supabase.py — kernel only,
no CSV/country/week discovery.
"""

from __future__ import annotations

import os
import uuid
from datetime import date, datetime
from typing import Iterable

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # env vars injected directly in CI

from supabase import Client, create_client

BATCH_SIZE = 500
ARTICLES_TABLE = "articles"
RUNS_TABLE = "scrape_runs"


def get_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
    return create_client(url, key)


def upsert_articles(client: Client, records: list[dict], *, label: str = "",
                    dry_run: bool = False) -> int:
    """Upsert article records into articles. Returns rows upserted."""
    if not records:
        print(f"  {label}: no rows to upsert")
        return 0

    # Canonicalise URLs (strip ?_locale=, utm_*, trailing slash, lowercase host)
    # so the same article isn't stored twice, then drop within-batch duplicates
    # that now collapse to the same URL. Keys on `url` (on_conflict=url).
    from src.scraping.common import normalise_url
    seen: set[str] = set()
    deduped: list[dict] = []
    for r in records:
        if "url" in r and r.get("url"):
            r["url"] = normalise_url(r["url"])
        u = r.get("url")
        if u and u in seen:
            continue
        if u:
            seen.add(u)
        deduped.append(r)
    if len(deduped) < len(records):
        print(f"  {label}: dropped {len(records) - len(deduped)} duplicate URL(s) after normalising")
    records = deduped

    if dry_run:
        print(f"  [dry-run] {label}: would upsert {len(records)} rows")
        return len(records)

    total = 0
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i : i + BATCH_SIZE]
        client.table(ARTICLES_TABLE).upsert(batch, on_conflict="url").execute()
        total += len(batch)
        if len(records) > BATCH_SIZE:
            print(f"    batch {i // BATCH_SIZE + 1}: {total}/{len(records)}")
    print(f"  {label}: upserted {total} rows")
    return total


def new_run_id() -> str:
    """Generate a single run_id to tag every scrape_runs row from one orchestrator run."""
    return uuid.uuid4().hex[:12]


def log_run(client: Client, *, run_id: str, source: str, source_type: str,
            since_date: date | None, until_date: date | None,
            started_at: datetime, finished_at: datetime,
            rows_scraped: int, rows_upserted: int,
            status: str, error: str | None = None,
            dry_run: bool = False) -> None:
    """Append one row to scrape_runs. Best-effort — never raises."""
    if dry_run:
        print(f"  [dry-run] {source}: would log run ({status}, scraped={rows_scraped}, upserted={rows_upserted})")
        return
    record = {
        "run_id": run_id,
        "source": source,
        "source_type": source_type,
        "since_date": since_date.isoformat() if since_date else None,
        "until_date": until_date.isoformat() if until_date else None,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "rows_scraped": rows_scraped,
        "rows_upserted": rows_upserted,
        "status": status,
        "error": error,
    }
    try:
        client.table(RUNS_TABLE).insert(record).execute()
    except Exception as e:
        print(f"  WARNING: scrape_runs log failed for {source}: {e}")
