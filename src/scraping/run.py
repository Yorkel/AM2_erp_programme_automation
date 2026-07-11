"""
run.py
Orchestrator. Iterates every enabled source in sources.yml, runs each,
upserts into Supabase articles, and logs one scrape_runs row per source.

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
from src.scraping.relevance import (
    DEFAULT_EDUCATION_KEYWORDS,
    compile_keyword_patterns,
    is_approved_domain,
    is_blocked_domain,
    is_blocked_url_pattern,
    is_broad_domain,
    is_non_uk_content,
    is_paywall_domain,
    log_rejection,
    matched_blocked_title_keyword,
)
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


def _scrape_one(src: dict, *, since: date | None, until: date | None) -> tuple[list, bool, list | None]:
    """Call the scraper for one source and return (items, apply_filter, require_keywords).
    Filter params are popped from `params` here so individual scrapers never see them —
    filtering is applied centrally in `_filter_items` after this returns.
    """
    params = dict(src.get("params") or {})
    params.setdefault("source", src["name"])
    params["since_date"] = since
    params["until_date"] = until

    # Centralised relevance-filter config: pop from params so scrapers don't see it.
    apply_filter = bool(params.pop("apply_relevance_filter", False))
    require_keywords = params.pop("require_keywords", None)

    if src["type"] == "newsletter":
        ingestion = src.get("ingestion", "disk")
        if ingestion == "disk":
            mod = importlib.import_module("src.scraping.newsletters.from_disk")
        elif ingestion == "gmail":
            mod = importlib.import_module("src.scraping.newsletters.gmail")
        else:
            raise RuntimeError(f"unknown newsletter ingestion '{ingestion}'")
        items = mod.scrape(**params)
    elif src["type"] == "web":
        scraper_path = src.get("scraper")
        if not scraper_path:
            raise RuntimeError(f"web source {src['name']} must specify 'scraper'")
        mod = importlib.import_module(scraper_path)
        items = mod.scrape(**params)
    elif src["type"] in ("rss", "google_alert"):
        scraper_path = src.get("scraper") or "src.scraping.rss_adapter"
        mod = importlib.import_module(scraper_path)
        items = mod.scrape(**params)
    else:
        raise RuntimeError(f"unknown source type {src['type']}")

    return items, apply_filter, require_keywords


def _filter_items(items: list, source: str,
                  apply_filter: bool, require_keywords: list | None) -> list:
    """Apply the education-relevance filter to Article items. Centralised here so
    every scraper type (rss_adapter, auto_listing, custom HTML scrapers) gets the
    same behaviour with one flip of `apply_relevance_filter: true` in sources.yml.
    Rejected items are logged to data/archive/rejected/<date>_<source>.csv.
    """
    # Hard-block social/clickbait domains and known-noisy URL paths
    # regardless of `apply_filter`. These are never wanted.
    pre_blocked: list = []
    pre_kept: list = []
    for item in items:
        if isinstance(item, Article):
            reason = None
            if is_blocked_domain(item.url):
                reason = "__blocked_domain__"
            elif is_blocked_url_pattern(item.url):
                reason = "__blocked_url_pattern__"
            if reason:
                log_rejection(
                    source=source,
                    url=item.url,
                    title=item.title or "",
                    source_type=item.source_type,
                    article_date=item.article_date,
                    matched_keywords_attempted=[reason],
                )
                pre_blocked.append(item)
                continue
        pre_kept.append(item)
    if pre_blocked:
        print(f"  {source}: {len(pre_blocked)} hard-blocked URL(s) dropped "
              f"(domain or URL-path; see data/archive/rejected/)")
    items = pre_kept

    # ── Title-keyword blocklist (universal — applies to every source) ─────
    # Drop articles whose title contains an out-of-scope keyword
    # (e.g. trans-rights coverage). Most specific reason — checked first.
    title_kept: list = []
    n_rejected_title = 0
    for item in items:
        if isinstance(item, Article):
            kw = matched_blocked_title_keyword(item.title)
            if kw:
                log_rejection(
                    source=source,
                    url=item.url,
                    title=item.title or "",
                    source_type=item.source_type,
                    article_date=item.article_date,
                    matched_keywords_attempted=[f"__blocked_title:{kw}__"],
                )
                n_rejected_title += 1
                continue
        title_kept.append(item)
    if n_rejected_title:
        print(f"  {source}: {n_rejected_title} dropped — blocked title keyword")
    items = title_kept

    # ── Paywall check (universal — applies to every source) ────────────────
    # Drop articles whose URL is on the paywall list. Checked before the
    # approved-domain check so paywall rejections get a distinct reason.
    paywall_kept: list = []
    n_rejected_paywall = 0
    for item in items:
        if isinstance(item, Article) and is_paywall_domain(item.url):
            log_rejection(
                source=source,
                url=item.url,
                title=item.title or "",
                source_type=item.source_type,
                article_date=item.article_date,
                matched_keywords_attempted=["__paywall__"],
            )
            n_rejected_paywall += 1
            continue
        paywall_kept.append(item)
    if n_rejected_paywall:
        print(f"  {source}: {n_rejected_paywall} dropped — paywall domain")
    items = paywall_kept

    # ── Approved-domain allowlist (universal — applies to every source) ────
    # Drop any article whose URL domain isn't on the curator-approved list.
    # Mainly catches Google-Alert-sourced articles that landed on random
    # councils, tabloids, foreign news, etc.
    domain_kept: list = []
    n_rejected_domain = 0
    for item in items:
        if isinstance(item, Article) and not is_approved_domain(item.url):
            log_rejection(
                source=source,
                url=item.url,
                title=item.title or "",
                source_type=item.source_type,
                article_date=item.article_date,
                matched_keywords_attempted=["__not_approved_domain__"],
            )
            n_rejected_domain += 1
            continue
        domain_kept.append(item)
    if n_rejected_domain:
        print(f"  {source}: {n_rejected_domain} dropped — URL domain not in approved list")
    items = domain_kept

    # Determine whether the keyword filter needs to run on each item. The flag
    # is forced ON for items on BROAD_DOMAINS (BBC, Guardian, universities,
    # parliaments etc. — covered in relevance.py).
    if not apply_filter and require_keywords is None and not any(
        isinstance(it, Article) and is_broad_domain(it.url) for it in items
    ):
        return items

    kws = tuple(require_keywords) if require_keywords is not None else DEFAULT_EDUCATION_KEYWORDS
    patterns = compile_keyword_patterns(kws)

    kept: list = []
    n_rejected_kw = 0
    n_rejected_country = 0
    n_broad_filtered = 0
    for item in items:
        if not isinstance(item, Article):
            kept.append(item)
            continue
        item_apply_filter = apply_filter or is_broad_domain(item.url)
        if not item_apply_filter and require_keywords is None:
            # Non-broad approved domain, source didn't opt in → no filter
            kept.append(item)
            continue
        # Country veto first — uses title + body since locations are usually
        # named in body text, not headlines.
        non_uk = is_non_uk_content(item.title, item.text or item.text_clean)
        if non_uk:
            log_rejection(
                source=source,
                url=item.url,
                title=item.title or "",
                source_type=item.source_type,
                article_date=item.article_date,
                matched_keywords_attempted=[f"__non_uk:{non_uk}__"],
            )
            n_rejected_country += 1
            continue
        # Education keyword match — TITLE ONLY. Body matches were letting
        # general-politics pieces through whenever they mentioned "schools"
        # or "education" in passing.
        title = (item.title or "").lower()
        matched = [kw for kw, p in zip(kws, patterns) if p.search(title)]
        if matched:
            kept.append(item)
            if is_broad_domain(item.url) and not apply_filter:
                n_broad_filtered += 1
        else:
            log_rejection(
                source=source,
                url=item.url,
                title=item.title or "",
                source_type=item.source_type,
                article_date=item.article_date,
                matched_keywords_attempted=[],
            )
            n_rejected_kw += 1

    if n_rejected_country:
        print(f"  {source}: {n_rejected_country} dropped as non-UK content")
    if n_rejected_kw:
        print(f"  {source}: {n_rejected_kw} dropped — no edu keyword in title")
    if n_broad_filtered:
        print(f"  {source}: {n_broad_filtered} broad-domain items passed the keyword filter")
    return kept


# Feed bodies shorter than this (chars) are treated as headline-only — many
# RSS feeds and ~all Google Alerts give a one-line blurb with no article body.
# Below the threshold we fetch the page and extract the real content.
# Raised 200 → 600 (2026-06-22): some feeds (e.g. spice-spotlight.scot, the
# Scottish Parliament SPICe blog) return a ~200-400 char *intro snippet* that
# squeaked over the old 200 bar, so the full ~7k-char body was never fetched and
# the summary came out "Summary unavailable". 600 distinguishes an RSS snippet
# from a real body. Safe: backfill only fetches KEPT articles (<100/wk) and only
# swaps in the fetched body when it's longer, so genuinely-short items are kept.
MIN_BODY_CHARS = 600


def _backfill_bodies(items: list, source: str, *, dry_run: bool = False) -> None:
    """Fill missing article bodies by fetching the page for kept articles.

    Runs AFTER _filter_items, so we only fetch pages for articles we're actually
    keeping — the fetch count tracks the weekly survivor volume, not the much
    larger raw feed count. For each kept Article whose `text` is shorter than
    MIN_BODY_CHARS (headline-only feed entry), fetch the URL and extract the main
    content via the same selector ladder used elsewhere (extract_body_text).
    If the fetched body is longer than what we had, swap it in and rebuild
    text_clean so the snippet stays consistent.

    Failures are swallowed: soup_of returns None on a 403/timeout, the item keeps
    its short body, and the summary step degrades to 'Summary unavailable' rather
    than blocking the scrape. This is why hard-blocked sites (e.g. Belfast
    Telegraph) simply stay un-summarised instead of erroring.
    """
    if dry_run or not items:
        return
    from src.scraping.common import build_text_clean, extract_body_text, soup_of

    n_fetched = 0
    n_unreachable = 0
    for item in items:
        if not isinstance(item, Article) or not item.url:
            continue
        if len((item.text or "").strip()) >= MIN_BODY_CHARS:
            continue
        soup = soup_of(item.url)
        if soup is None:
            n_unreachable += 1
            continue
        body = extract_body_text(soup)
        if len(body.strip()) > len((item.text or "").strip()):
            item.text = body
            item.text_clean = build_text_clean(item.title, body)
            n_fetched += 1
    if n_fetched or n_unreachable:
        print(f"  {source}: body backfill — {n_fetched} fetched"
              + (f", {n_unreachable} unreachable" if n_unreachable else ""))


def _generate_summaries(items: list, source: str, *, dry_run: bool = False) -> None:
    """Populate Article.summary + .geographic_focus + .topic_tags for each kept
    item via model enrichment. Mutates in place.

    Enrichment is provider-aware (see summarise.enrich_provider): OpenAI-primary
    on the runner (ENRICH_PROVIDER=openai), Claude-primary elsewhere, each with
    the other provider as fallback.
    Cheap (~$0.001/article with prompt caching). Failures are logged and
    skipped — a single bad article never blocks the scrape.

    REQUIRES migrations 012 + 013 applied (articles.summary,
    summary_generated_at, geographic_focus, topic_tags columns).
    """
    if dry_run:
        print(f"  [dry-run] {source}: would enrich {len(items)} article(s)")
        return
    if not items:
        return

    from datetime import datetime
    from src.inference.summarise import enrich_summary, enrich_tags

    n_ok_sum = 0
    n_ok_tag = 0
    n_fail = 0
    for item in items:
        if not isinstance(item, Article):
            continue
        title = item.title or ""
        # Use only item.text (real body). NEVER fall back to text_clean —
        # it's a noisy 80-word truncation that often starts with nav cruft
        # ("HOME > Blog >"). If body is empty, summarise_article returns
        # "Summary unavailable" rather than fabricating from nothing.
        body = item.text or ""
        if not item.summary:
            try:
                # Pass only item.text (the real body). If empty, summary
                # generation returns "Summary unavailable" — better than summarising
                # from text_clean which is a noisy 80-word truncation that
                # often starts with nav like "HOME > Blog >".
                item.summary = enrich_summary(
                    title=title, text=item.text or "", category=None,
                )
                item.summary_generated_at = datetime.utcnow()
                n_ok_sum += 1
            except Exception as e:
                n_fail += 1
                print(f"    WARNING: summary failed for {item.url}: {type(e).__name__}: {e}")
        if not item.geographic_focus and not item.topic_tags:
            tags = enrich_tags(title=title, text=body)
            if tags.get("geographic_focus") or tags.get("topic_tags"):
                item.geographic_focus = tags.get("geographic_focus") or None
                item.topic_tags = tags.get("topic_tags") or None
                n_ok_tag += 1
    if n_ok_sum or n_ok_tag or n_fail:
        print(f"  {source}: {n_ok_sum} summaries, {n_ok_tag} tags"
              + (f" ({n_fail} failed)" if n_fail else ""))


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
    parser.add_argument("--no-summaries", action="store_true",
                        help="Skip AI enrichment for kept articles. Body backfill still runs; "
                             "summary/tag/topic-sentence sweep can run separately.")
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
            items, apply_filter, require_keywords = _scrape_one(
                src, since=args.since, until=args.until
            )
            items = _filter_items(items, name, apply_filter, require_keywords)
            _backfill_bodies(items, name, dry_run=args.dry_run)
            if not args.no_summaries:
                _generate_summaries(items, name, dry_run=args.dry_run)
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
