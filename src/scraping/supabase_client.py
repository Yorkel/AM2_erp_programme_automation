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

# Accepted terminal summary for body-less articles (not a failure). It must never
# be allowed to OVERWRITE a real summary already saved for the same URL — during a
# provider outage enrich_summary returns this string, and a re-scrape of a recent
# URL would otherwise clobber good data with the placeholder.
PLACEHOLDER_SUMMARY = "Summary unavailable"
_BLANK_SUMMARY = {"", "nan", "none", "nat"}


def _is_real_summary(v) -> bool:
    """True only for a genuine summary: not NULL/blank and not the placeholder."""
    if v is None:
        return False
    s = str(v).strip()
    if s.lower() in _BLANK_SUMMARY:
        return False
    return s != PLACEHOLDER_SUMMARY


def protect_existing_summaries(records: list[dict], existing: dict[str, str]) -> int:
    """Strip summary/summary_generated_at from any record that would overwrite an
    already-real summary with the placeholder. `existing` maps url -> current DB
    summary. Mutates records in place; returns how many were protected. Pure —
    unit-testable without a DB."""
    protected = 0
    for r in records:
        if str(r.get("summary") or "").strip() != PLACEHOLDER_SUMMARY:
            continue  # only the placeholder can clobber; real summaries write through
        if _is_real_summary(existing.get(r.get("url"))):
            r.pop("summary", None)
            r.pop("summary_generated_at", None)
            protected += 1
    return protected


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

    # Protect good summaries: only fetch existing rows for URLs whose incoming
    # summary is the placeholder (an outage re-scrape). If the DB already holds a
    # real summary there, drop the summary field so the upsert leaves it intact.
    placeholder_urls = [
        r["url"] for r in records
        if r.get("url") and str(r.get("summary") or "").strip() == PLACEHOLDER_SUMMARY
    ]
    if placeholder_urls:
        existing: dict[str, str] = {}
        for i in range(0, len(placeholder_urls), BATCH_SIZE):
            chunk = placeholder_urls[i : i + BATCH_SIZE]
            rows = (
                client.table(ARTICLES_TABLE).select("url, summary")
                .in_("url", chunk).execute().data or []
            )
            existing.update({x["url"]: x.get("summary") for x in rows})
        n_protected = protect_existing_summaries(records, existing)
        if n_protected:
            print(f"  {label}: kept {n_protected} existing summary(ies) — refused to "
                  f"overwrite with '{PLACEHOLDER_SUMMARY}' (provider likely down)")

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
