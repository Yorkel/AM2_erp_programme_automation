"""
pipeline_health.py — end-to-end health check for the weekly newsletter pipeline.

Verifies that THIS newsletter week's articles (the Tuesday→Tuesday cycle) made it
all the way through: scraped → classified → summarised. Designed to run as the
LAST step after the scrape/classify chain (and on a schedule backstop), AFTER the
self-heal sweeps. If anything is still broken, it exits non-zero so GitHub Actions
marks the run failed and emails — i.e. WE find out before a curator does.

This is the missing piece behind the 2026-06-16 and 2026-06-22 incidents: the
pipeline failed silently and a curator hit the broken dashboard first.

Checks (within the current Tue→Tue window):
  - every article is classified (present in classify_newsletter)
  - every article has a real summary (not NULL / 'nan' / empty)
The legitimate 'Summary unavailable' placeholder (body-extraction-blocked sources)
is treated as OK — it means we tried and there was no body, not a pipeline failure.

Exit code: 0 = healthy, 1 = unhealthy (→ GitHub failure email).

Env required: SUPABASE_URL, SUPABASE_SERVICE_KEY
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta, timezone

from dotenv import load_dotenv

from src.scraping.supabase_client import get_client

PLACEHOLDER = "Summary unavailable"
_BLANK = {"", "nan", "none", "nat"}


def _is_blank(v) -> bool:
    """True for NULL / NaN / empty / the literal strings 'nan'/'none'/'nat'.
    Also True for an empty array/collection (topic_tags is an array column, so
    NULL and [] both mean 'no tags').
    The 'Summary unavailable' placeholder is NOT blank (it's an accepted fallback)."""
    if v is None:
        return True
    if isinstance(v, (list, tuple, set, dict)):
        return len(v) == 0
    return str(v).strip().lower() in _BLANK


def last_tuesday(today: date | None = None) -> date:
    """Most recent Tuesday strictly before today — matches the classify window
    (`date -d 'last tuesday'`). On a Tuesday this returns the PREVIOUS Tuesday,
    so the open Tue→Tue cycle is fully covered on both the Mon and Tue runs."""
    today = today or datetime.now(timezone.utc).date()
    offset = (today.weekday() - 1) % 7   # Mon=0..Sun=6; Tuesday=1
    if offset == 0:                      # today IS Tuesday → go back a full week
        offset = 7
    return today - timedelta(days=offset)


def _emit_summary(lines: list[str]) -> None:
    """Mirror the report into the GitHub Actions step summary when available."""
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    try:
        with open(path, "a") as f:
            f.write("\n".join(lines) + "\n")
    except OSError:
        pass


def main() -> int:
    load_dotenv()
    if not (os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_KEY")):
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set", file=sys.stderr)
        return 1

    client = get_client()
    since = last_tuesday().isoformat()

    # This week's articles (Tue→Tue window, by article_date).
    articles: list[dict] = []
    off = 0
    while True:
        r = (
            client.table("articles")
            .select("url, source, article_date, summary, topic_sentence, topic_tags")
            .gte("article_date", since)
            .range(off, off + 999)
            .execute()
        )
        batch = r.data or []
        articles.extend(batch)
        if len(batch) < 1000:
            break
        off += 1000

    # Everything that's been classified (url set).
    classified: set[str] = set()
    off = 0
    while True:
        r = client.table("classify_newsletter").select("url").range(off, off + 999).execute()
        batch = r.data or []
        classified.update(x["url"] for x in batch)
        if len(batch) < 1000:
            break
        off += 1000

    total = len(articles)
    unclassified = [a for a in articles if a["url"] not in classified]
    blank_summary = [a for a in articles if _is_blank(a.get("summary"))]
    blank_topic = [a for a in articles if _is_blank(a.get("topic_sentence"))]
    blank_tags = [a for a in articles if _is_blank(a.get("topic_tags"))]
    placeholders = [a for a in articles if (a.get("summary") or "").strip() == PLACEHOLDER]

    healthy = not unclassified and not blank_summary and not blank_topic and not blank_tags

    lines = [
        "## Pipeline health check",
        f"- Newsletter week (Tue→Tue): since **{since}**",
        f"- Articles this week: **{total}**",
        f"- Unclassified: **{len(unclassified)}**",
        f"- Blank summaries (NULL/nan): **{len(blank_summary)}**",
        f"- Blank topic sentences (NULL/nan): **{len(blank_topic)}**",
        f"- Blank topic tags (NULL/empty): **{len(blank_tags)}**",
        f"- 'Summary unavailable' placeholders (accepted): {len(placeholders)}",
        f"- **Status: {'✅ HEALTHY' if healthy else '❌ UNHEALTHY'}**",
    ]
    print("\n".join(lines))
    _emit_summary(lines)

    if not healthy:
        for a in (unclassified[:10]):
            print(f"  UNCLASSIFIED: {a.get('source')} | {a.get('url')}", file=sys.stderr)
        for a in (blank_summary[:10]):
            print(f"  BLANK SUMMARY: {a.get('source')} | {a.get('url')}", file=sys.stderr)
        for a in (blank_topic[:10]):
            print(f"  BLANK TOPIC: {a.get('source')} | {a.get('url')}", file=sys.stderr)
        for a in (blank_tags[:10]):
            print(f"  BLANK TAGS: {a.get('source')} | {a.get('url')}", file=sys.stderr)
        print(
            f"UNHEALTHY: {len(unclassified)} unclassified, {len(blank_summary)} blank "
            f"summaries, {len(blank_topic)} blank topic sentences, {len(blank_tags)} blank "
            f"topic tags this week — self-heal did not fully recover.",
            file=sys.stderr,
        )
        return 1

    print("Pipeline healthy — this week's articles are classified, summarised, and topic-tagged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
