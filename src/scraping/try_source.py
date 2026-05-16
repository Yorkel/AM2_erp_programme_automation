"""
try_source.py
Test a single source WITHOUT writing to Supabase.

Three modes:

  # 1. Run a source from sources.yml
  python -m src.scraping.try_source --source wonkhe_newsletter
  python -m src.scraping.try_source --source gov_uk_education --since 2026-04-01

  # 2. Test an ad-hoc URL with the generic web scraper
  python -m src.scraping.try_source --url https://example.com/article

  # 3. Test an ad-hoc newsletter HTML file
  python -m src.scraping.try_source --html path/to/newsletter.html

Outputs:
  - row count
  - validation issues
  - first + last row
  - optionally --save to data/scratch/<source>_<date>.json
"""

from __future__ import annotations

import argparse
import importlib
import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from pathlib import Path

from src.scraping.common import (
    Article,
    extract_body_text,
    parse_date_loose,
    soup_of,
    validate_rows,
)
from src.scraping.config import get_source

SCRATCH_DIR = Path("data/scratch")


def _to_records(items):
    out = []
    for r in items:
        if isinstance(r, Article):
            out.append(r.to_record())
        elif is_dataclass(r):
            out.append(asdict(r))
        else:
            out.append(r)
    return out


def _print_report(rows, label):
    summary = validate_rows(rows)
    print(f"\n=== {label} ===")
    print(f"rows: {summary['count']}")
    if summary.get("issues"):
        print("issues:")
        for i in summary["issues"]:
            print(f"  - {i}")
    else:
        print("no validation issues")
    if summary["count"]:
        print("\nfirst row:")
        print(json.dumps(summary["first"], indent=2, default=str)[:1500])
        if summary["count"] > 1:
            print("\nlast row:")
            print(json.dumps(summary["last"], indent=2, default=str)[:1500])


def _run_source_from_registry(name: str, since: date | None, until: date | None,
                              follow_links: bool):
    src = get_source(name)
    if src is None:
        raise SystemExit(f"source '{name}' not found in sources.yml")
    print(f"running source: {name} (type={src['type']})")

    params = dict(src.get("params") or {})
    params.setdefault("source", name)
    params["since_date"] = since
    params["until_date"] = until

    if src["type"] == "newsletter":
        ingestion = src.get("ingestion", "disk")
        if ingestion == "disk":
            mod = importlib.import_module("src.scraping.newsletters.from_disk")
            params["follow_links"] = follow_links
        elif ingestion == "gmail":
            mod = importlib.import_module("src.scraping.newsletters.gmail")
        else:
            raise SystemExit(f"unknown newsletter ingestion '{ingestion}'")
        return mod.scrape(**params)

    if src["type"] == "web":
        scraper_path = src.get("scraper")
        if not scraper_path:
            raise SystemExit(f"web source {name} must specify a 'scraper' module path in sources.yml")
        mod = importlib.import_module(scraper_path)
        return mod.scrape(**params)

    if src["type"] in ("rss", "google_alert"):
        scraper_path = src.get("scraper") or "src.scraping.rss_adapter"
        mod = importlib.import_module(scraper_path)
        return mod.scrape(**params)

    raise SystemExit(f"unknown source type {src['type']}")


def _run_adhoc_url(url: str) -> list[Article]:
    soup = soup_of(url)
    if soup is None:
        return []
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else None
    body = extract_body_text(soup)
    return [Article(
        url=url,
        title=title,
        article_date=parse_date_loose(soup.get_text(" ", strip=True)[:2000]),
        source="adhoc",
        source_type="web",
        text=body,
    )]


def _run_adhoc_html(path: Path) -> list[Article]:
    from src.scraping.newsletters.parse_html import (
        extract_issue_date,
        parse_newsletter_html,
    )
    html = path.read_text(encoding="utf-8", errors="ignore")
    issue_date = extract_issue_date(html)
    return parse_newsletter_html(html, source=f"adhoc:{path.name}", default_date=issue_date)


def main():
    parser = argparse.ArgumentParser(description="Test a single source without DB writes.")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--source", help="Source name from sources.yml")
    g.add_argument("--url", help="Ad-hoc URL to scrape with the generic parser")
    g.add_argument("--html", help="Ad-hoc newsletter HTML file path")

    parser.add_argument("--since", type=lambda s: date.fromisoformat(s), default=None)
    parser.add_argument("--until", type=lambda s: date.fromisoformat(s), default=None)
    parser.add_argument("--no-follow-links", action="store_true",
                        help="For newsletter sources: skip fetching link bodies (faster, lower-fidelity)")
    parser.add_argument("--save", action="store_true",
                        help=f"Write rows as JSON under {SCRATCH_DIR}/")
    args = parser.parse_args()

    if args.source:
        rows = _run_source_from_registry(args.source, args.since, args.until,
                                         follow_links=not args.no_follow_links)
        label = args.source
    elif args.url:
        rows = _run_adhoc_url(args.url)
        label = f"adhoc url: {args.url}"
    else:
        rows = _run_adhoc_html(Path(args.html))
        label = f"adhoc html: {args.html}"

    records = _to_records(rows)
    _print_report(records, label)

    if args.save:
        SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        out = SCRATCH_DIR / f"{label.replace('/', '_').replace(' ', '_')[:60]}_{stamp}.json"
        out.write_text(json.dumps(records, indent=2, default=str))
        print(f"\nsaved → {out}")


if __name__ == "__main__":
    main()
