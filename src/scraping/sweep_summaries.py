"""
sweep_summaries.py — idempotent safety-net for article summaries + tags.

Finds every article in `articles` that has a NULL `summary` (or NULL
`topic_tags`) and calls Claude to fill them in. If Claude/the proxy is
unreachable, summary rows try OpenAI next, then get a deterministic extractive
fallback (or the accepted placeholder when there is no text), so health checks
are not blocked by an external LLM outage. Mirrors the `sweep_unclassified.py` pattern: same shape,
predictable, no surprises.

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


from src.inference.summarise import (
    DEFAULT_MODEL,
    enrich_provider,
    enrich_summary,
    enrich_tags,
    enrich_topic_sentence,
    extractive_fallback_summary,
    summarise_article_openai,
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


def _openai_available(oai_client) -> bool:
    """Return False quickly when the sweep cannot reach OpenAI at all (the mirror
    of _claude_available for the OpenAI-primary runner path)."""
    from src.inference.summarise import _openai_summary_model
    try:
        oai_client.responses.create(
            model=_openai_summary_model(),
            input="Reply OK.",
            max_output_tokens=16,
        )
        return True
    except Exception as e:
        print(
            f"ERROR: OpenAI unreachable before sweep: {type(e).__name__}: {e}",
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


def _fallback_summary(row: dict) -> str:
    return extractive_fallback_summary(
        title=row.get("title") or "",
        text=_best_text(row),
    )


def _needs_summary(row: dict) -> bool:
    """True when the row still needs a terminal summary value.

    Blank rows are work even with no usable text: they should be written to the
    accepted placeholder so health checks do not flag them forever. Existing
    placeholders are only retryable when we have text that Claude/OpenAI/fallback can
    turn into something better.
    """
    s = (row.get("summary") or "").strip()
    if s and s != PLACEHOLDER:
        return False
    has_text = bool(_best_text(row))
    if s == PLACEHOLDER and not has_text:
        return False
    return True


def _apply_fallback_summaries(client, rows: list[dict]) -> tuple[int, int]:
    """Fill missing summaries without Claude. Returns (ok, fail)."""
    ok = 0
    fail = 0
    generated_at = datetime.now(timezone.utc).isoformat()

    for row in rows:
        summary = _fallback_summary(row)
        if not summary:
            fail += 1
            continue
        try:
            client.table("articles").update({
                "summary": summary,
                "summary_generated_at": generated_at,
            }).eq("id", row["id"]).execute()
            ok += 1
        except Exception as e:
            fail += 1
            print(
                f"  fallback summary failed for {row.get('url')}: "
                f"{type(e).__name__}: {e}",
                file=sys.stderr,
            )

    return ok, fail


def _apply_openai_summaries(client, rows: list[dict]) -> tuple[int, int]:
    """Fill missing summaries through OpenAI when Claude/proxy is down."""
    ok = 0
    fail = 0
    generated_at = datetime.now(timezone.utc).isoformat()

    for row in rows:
        text = _best_text(row)
        if not text:
            summary = PLACEHOLDER
        else:
            try:
                summary = summarise_article_openai(
                    title=row.get("title") or "",
                    text=text,
                    category=None,
                )
            except Exception as e:
                fail += 1
                print(
                    f"  OpenAI summary failed for {row.get('url')}: "
                    f"{type(e).__name__}: {e}",
                    file=sys.stderr,
                )
                continue

        try:
            client.table("articles").update({
                "summary": summary,
                "summary_generated_at": generated_at,
            }).eq("id", row["id"]).execute()
            ok += 1
        except Exception as e:
            fail += 1
            print(
                f"  OpenAI summary update failed for {row.get('url')}: "
                f"{type(e).__name__}: {e}",
                file=sys.stderr,
            )

    return ok, fail


def _apply_title_topic_sentences(client, rows: list[dict]) -> tuple[int, int]:
    """Fill missing topic sentences from the article TITLE, with no LLM call.

    Used on the Claude-down path so the dashboard's topic line is never left
    blank during an outage. This is the same "defer to the title" degradation
    that extract_topic_sentence uses; a later healthy sweep will not re-touch a
    row once it is non-blank, so an outage freezes the title in place until the
    row is cleared (accepted trade-off: a title beats a blank line)."""
    import re

    ok = 0
    fail = 0
    generated_at = datetime.now(timezone.utc).isoformat()

    for row in rows:
        title = re.sub(r"\s+", " ", (row.get("title") or "").strip())
        if not title:
            fail += 1
            continue
        try:
            client.table("articles").update({
                "topic_sentence": title,
                "topic_sentence_generated_at": generated_at,
            }).eq("id", row["id"]).execute()
            ok += 1
        except Exception as e:
            fail += 1
            print(
                f"  title topic sentence failed for {row.get('url')}: "
                f"{type(e).__name__}: {e}",
                file=sys.stderr,
            )

    return ok, fail


def main() -> int:
    from dotenv import load_dotenv
    from supabase import create_client

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

    # Build one reusable client for the configured primary provider (cheaper +
    # prompt-cache friendly) and probe it once, so a total outage takes the
    # degraded path instead of retrying every enrichment call for every row.
    # On the GitHub runner ENRICH_PROVIDER=openai, because it cannot reach Claude.
    provider = enrich_provider()
    ant_client = None
    oai_client = None
    if provider == "openai":
        from openai import OpenAI
        oai_client = OpenAI(timeout=60.0, max_retries=2)
        primary_ok = _openai_available(oai_client)
    else:
        from src.inference.anthropic_client import make_anthropic_client
        ant_client = make_anthropic_client(5)
        primary_ok = _claude_available(ant_client)
    print(f"Enrichment provider: {provider} (reachable: {primary_ok})")

    if not primary_ok:
        # Primary provider is down. Fill summaries with whatever works, then
        # STILL fill topic sentences from titles so the dashboard is never left
        # with a blank topic line. Tags wait for a later healthy sweep (which the
        # health check now flags — see pipeline_health.py).
        summary_ok = 0
        # When Claude is primary-but-down, OpenAI may still work for summaries.
        # When OpenAI is primary-but-down, don't retry it — go straight to local.
        if provider != "openai" and os.environ.get("OPENAI_API_KEY"):
            summary_ok, n_openai_fail = _apply_openai_summaries(
                client, needing_summary
            )
            print(
                "Primary down; used OpenAI summaries: "
                f"{summary_ok} ok / {n_openai_fail} fail"
            )
        if summary_ok == 0:
            summary_ok, n_fallback_fail = _apply_fallback_summaries(
                client, needing_summary
            )
            print(
                "Providers unavailable; used extractive fallback summaries: "
                f"{summary_ok} ok / {n_fallback_fail} fail"
            )

        n_title_ok, n_title_fail = _apply_title_topic_sentences(
            client, needing_topic
        )
        print(
            "Primary down; topic sentences from title fallback: "
            f"{n_title_ok} ok / {n_title_fail} fail"
        )

        # Progress on either front is enough to exit clean; only a total
        # standstill (had work, filled nothing) should alarm.
        had_work = bool(needing_summary or needing_topic)
        if had_work and summary_ok == 0 and n_title_ok == 0:
            return 1
        return 0

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
            if not text:
                update["summary"] = PLACEHOLDER
                update["summary_generated_at"] = datetime.now(timezone.utc).isoformat()
                n_sum_ok += 1
            else:
                try:
                    summary = enrich_summary(
                        title=title, text=text, category=None,
                        client=ant_client, openai_client=oai_client,
                    )
                    update["summary"] = summary
                    update["summary_generated_at"] = datetime.now(timezone.utc).isoformat()
                    n_sum_ok += 1
                except Exception as e:
                    n_sum_fail += 1
                    print(f"  summary failed for {row.get('url')}: {type(e).__name__}: {e}", file=sys.stderr)

        if row["id"] in tag_ids:
            tags = enrich_tags(
                title=title, text=text,
                client=ant_client, openai_client=oai_client,
            )
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
                ts = enrich_topic_sentence(
                    title=title, text=row.get("text") or "",
                    client=ant_client, openai_client=oai_client,
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
        print("ERROR: sweep had work but made no progress — summary providers likely unreachable", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
