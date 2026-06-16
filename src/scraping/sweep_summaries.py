"""
sweep_summaries.py — idempotent safety-net for article summaries + tags.

Finds every article in `articles` that has a NULL `summary` (or NULL
`topic_tags`) and calls Claude to fill them in. Mirrors the
`sweep_unclassified.py` pattern: same shape, predictable, no surprises.

Designed to run as a step in .github/workflows/scrape.yml AFTER the main
scrape. Catches anything the scrape missed (Anthropic transient outage,
single-article failures, etc.). Re-running with no NULL rows is a no-op.

Env required:
  SUPABASE_URL
  SUPABASE_SERVICE_KEY  (write access)
  ANTHROPIC_API_KEY
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv
from supabase import create_client

from src.inference.summarise import (
    DEFAULT_MODEL,
    extract_topic_sentence,
    summarise_article,
    tag_article,
)


# Only sweep the last N days. Older NULLs are stale (likely failed body
# extraction); don't pay to retry them every week.
LOOKBACK_DAYS = 30

# Body-length thresholds for choosing what text to summarise from.
MIN_BODY_CHARS = 200      # text this long is treated as a real article body
MIN_SNIPPET_CHARS = 40    # text_clean (title + standfirst) usable as a fallback

PLACEHOLDER = "Summary unavailable"


def _claude_available(ant_client) -> bool:
    """Return False quickly when the sweep cannot reach Claude at all.

    Without this guard, a transient/network-wide Anthropic outage causes three
    retried calls per article (summary, tags, topic sentence), which turns a
    best-effort sweep into several minutes of repetitive log noise.
    """
    try:
        ant_client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=1,
            temperature=0,
            messages=[{"role": "user", "content": "Reply OK."}],
        )
        return True
    except Exception as e:
        print(
            f"ERROR: Claude unreachable before sweep: {type(e).__name__}: {e}",
            file=sys.stderr,
        )
        return False


def _best_text(row: dict) -> str:
    """Best available text to summarise from. Prefer the real body; fall back
    to text_clean (title + standfirst) for sources whose body is blocked
    (e.g. Belfast Telegraph 403s). Returns '' when nothing usable exists — so
    genuinely empty rows aren't retried (and billed) on every weekly sweep."""
    text = (row.get("text") or "").strip()
    if len(text) >= MIN_BODY_CHARS:
        return text
    snippet = (row.get("text_clean") or "").strip()
    if len(snippet) >= MIN_SNIPPET_CHARS:
        return snippet
    if len(text) >= MIN_SNIPPET_CHARS:
        return text
    return ""


def _needs_summary(row: dict) -> bool:
    """A row needs a summary if it has none OR carries the 'Summary unavailable'
    placeholder (retryable — finding 8), AND we actually have text to work with.
    Without the usable-text guard the placeholder rows would be retried forever."""
    s = (row.get("summary") or "").strip()
    if s and s != PLACEHOLDER:
        return False
    return bool(_best_text(row))


def main() -> int:
    load_dotenv()
    sup_url = os.environ.get("SUPABASE_URL")
    sup_key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if not (sup_url and sup_key):
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set", file=sys.stderr)
        return 1
    if not anthropic_key:
        print("ERROR: ANTHROPIC_API_KEY must be set", file=sys.stderr)
        return 1
    client = create_client(sup_url, sup_key)

    # Find articles needing summaries OR tags within the lookback window.
    cutoff = (datetime.now(timezone.utc).timestamp() - LOOKBACK_DAYS * 86400)
    cutoff_iso = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()

    rows: list[dict] = []
    off = 0
    while True:
        r = (
            client.table("articles")
            .select("id, url, title, text, text_clean, summary, topic_sentence, topic_tags, geographic_focus, scraped_at")
            .gte("scraped_at", cutoff_iso)
            .range(off, off + 999)
            .execute()
        )
        batch = r.data or []
        rows.extend(batch)
        if len(batch) < 1000:
            break
        off += 1000

    def _needs_topic(r):
        # Blank OR the old "Summary unavailable" placeholder → (re)generate.
        # extract_topic_sentence falls back to the title, so every article can
        # get one regardless of body.
        t = (r.get("topic_sentence") or "").strip()
        return t == "" or t == PLACEHOLDER

    needing_summary = [r for r in rows if _needs_summary(r)]
    needing_tags = [r for r in rows if not r.get("topic_tags") and not r.get("geographic_focus")]
    needing_topic = [r for r in rows if _needs_topic(r)]
    print(f"Rows scanned (last {LOOKBACK_DAYS} days): {len(rows)}")
    print(f"  needing summary:        {len(needing_summary)}")
    print(f"  needing tags:           {len(needing_tags)}")
    print(f"  needing topic sentence: {len(needing_topic)}")

    if not needing_summary and not needing_tags and not needing_topic:
        print("Nothing to sweep — exiting clean.")
        return 0

    # Build a single Anthropic client and reuse it across all calls (cheaper +
    # prompt-cache friendly). Probe connectivity once so a total Claude outage
    # fails quickly instead of retrying every enrichment call for every row.
    from anthropic import Anthropic
    probe_client = Anthropic(max_retries=1)
    if not _claude_available(probe_client):
        return 1
    ant_client = Anthropic(max_retries=5)

    n_sum_ok = 0
    n_sum_fail = 0
    n_tag_ok = 0
    n_tag_fail = 0
    n_topic_ok = 0
    n_topic_fail = 0

    # Build a set of ids needing each, so we don't double-iterate.
    sum_ids = {r["id"] for r in needing_summary}
    tag_ids = {r["id"] for r in needing_tags}
    topic_ids = {r["id"] for r in needing_topic}
    to_process = [r for r in rows if r["id"] in (sum_ids | tag_ids | topic_ids)]

    for row in to_process:
        title = row.get("title") or ""
        text = _best_text(row)   # real body, else text_clean fallback
        update: dict = {}

        if row["id"] in sum_ids:
            try:
                summary = summarise_article(
                    title=title, text=text, category=None, client=ant_client,
                )
                update["summary"] = summary
                update["summary_generated_at"] = datetime.now(timezone.utc).isoformat()
                n_sum_ok += 1
            except Exception as e:
                n_sum_fail += 1
                print(f"  summary failed for {row.get('url')}: {type(e).__name__}: {e}", file=sys.stderr)

        if row["id"] in tag_ids:
            tags = tag_article(title=title, text=text, client=ant_client)
            if tags.get("geographic_focus") or tags.get("topic_tags"):
                update["geographic_focus"] = tags.get("geographic_focus") or None
                update["topic_tags"] = tags.get("topic_tags") or None
                n_tag_ok += 1
            else:
                n_tag_fail += 1

        if row["id"] in topic_ids:
            try:
                # Topic sentence must come from the REAL body (not the text_clean
                # fallback), else it can quote scraped metadata that isn't in the
                # article. extract_topic_sentence falls back to the title.
                ts = extract_topic_sentence(
                    title=title, text=row.get("text") or "", client=ant_client,
                )
                update["topic_sentence"] = ts
                update["topic_sentence_generated_at"] = datetime.now(timezone.utc).isoformat()
                n_topic_ok += 1
            except Exception as e:
                n_topic_fail += 1
                print(f"  topic sentence failed for {row.get('url')}: {type(e).__name__}: {e}", file=sys.stderr)

        if update:
            try:
                client.table("articles").update(update).eq("id", row["id"]).execute()
            except Exception as e:
                print(f"  upsert failed for {row.get('url')}: {type(e).__name__}: {e}", file=sys.stderr)

    print(
        f"Sweep done: summaries {n_sum_ok} ok / {n_sum_fail} fail; "
        f"tags {n_tag_ok} ok / {n_tag_fail} fail; "
        f"topic sentences {n_topic_ok} ok / {n_topic_fail} fail"
    )
    # Non-zero exit if the sweep made no progress despite having work to do.
    # That signals a real problem (e.g. Anthropic down) → GitHub emails us.
    had_work = bool(needing_summary or needing_tags or needing_topic)
    made_progress = (n_sum_ok > 0) or (n_tag_ok > 0) or (n_topic_ok > 0)
    if had_work and not made_progress:
        print("ERROR: sweep had work but made no progress — Claude likely unreachable", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
