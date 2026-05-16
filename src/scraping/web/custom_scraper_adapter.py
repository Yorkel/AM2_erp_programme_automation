"""
web/custom_scraper_adapter.py
Thin wrapper around the per-site custom scrapers in src/scraping/web/<country>/.

Each custom scraper exposes:
    scrape_<name>(since_date=None, until_date=None,
                  output_path=None, append=False) -> list[dict]

with row keys: url, title, date, text (+ source-specific extras).

This adapter:
  - Imports the named site module
  - Calls its scrape_<...> function
  - Wraps each row in an Article object (so text_clean etc. match our pipeline)

Configured per-source via sources.yml, e.g.:

    - name: dfe
      type: web
      scraper: src.scraping.web.custom_scraper_adapter
      params:
        module: src.scraping.web.england.dfe
"""

from __future__ import annotations

from datetime import date, datetime
from importlib import import_module

from src.scraping.common import Article


def _to_date(value):
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return None


def _find_scrape_function(mod):
    """Pick the scrape_<name> function on the module (excluding scrape_article)."""
    for name in dir(mod):
        if name.startswith("scrape_") and name != "scrape_article" and callable(getattr(mod, name)):
            return getattr(mod, name)
    raise RuntimeError(f"no scrape_<name>() function found on {mod.__name__}")


def scrape(*, source: str, module: str,
           since_date: date | None = None, until_date: date | None = None,
           **_ignored) -> list[Article]:
    mod = import_module(module)
    fn = _find_scrape_function(mod)
    rows = fn(since_date=since_date, until_date=until_date,
              output_path=None, append=False) or []

    articles: list[Article] = []
    for r in rows:
        if not r.get("url"):
            continue
        extras = {k: v for k, v in r.items()
                  if k not in ("url", "title", "date", "text")}
        articles.append(Article(
            url=r["url"],
            title=r.get("title"),
            article_date=_to_date(r.get("date")),
            source=source,
            source_type="web",
            text=r.get("text"),
            extra=extras,
        ))
    return articles
