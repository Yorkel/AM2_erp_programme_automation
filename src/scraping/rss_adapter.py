"""
rss_adapter.py
Ingest any RSS / Atom feed (including Google Alerts) and return Article objects.

Used for all `type: rss` and `type: google_alert` entries in sources.yml:

    - name: bera
      type: rss
      scraper: src.scraping.rss_adapter
      params:
        feed_url: https://www.bera.ac.uk/feed

The adapter handles both standard RSS feeds and Google Alerts' Atom format.
Google Alerts wraps each entry's link as `https://www.google.com/url?...&url=<real>`;
this module unwraps that to the real article URL.
"""

from __future__ import annotations

import time
from datetime import date, datetime
from urllib.parse import parse_qs, unquote, urlparse

import html as html_lib
import re

import feedparser
from bs4 import BeautifulSoup

from src.scraping.common import Article, build_text_clean
from src.scraping.relevance import (
    DEFAULT_EDUCATION_KEYWORDS,
    compile_keyword_patterns,
    log_rejection,
)

_WS_RE = re.compile(r"\s+")


def _strip_html(s: str) -> str:
    """Strip HTML tags and unescape entities — keeps just clean text."""
    if not s:
        return ""
    text = BeautifulSoup(s, "html.parser").get_text(" ", strip=True)
    text = html_lib.unescape(text)
    return _WS_RE.sub(" ", text).strip()


def _unwrap_google_url(link: str) -> str:
    """Google Alerts wraps links in a tracking redirect. Extract the real URL."""
    if not link or "google.com/url" not in link:
        return link
    try:
        q = parse_qs(urlparse(link).query)
        inner = q.get("url", []) or q.get("q", [])
        return unquote(inner[0]) if inner else link
    except Exception:
        return link


_ORDINAL_RE = re.compile(r"(\d+)(st|nd|rd|th)\b", re.I)


def _entry_date(entry) -> date | None:
    # First try feedparser's pre-parsed dates (works for standard RSS/Atom)
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        parsed = entry.get(key)
        if parsed:
            try:
                return datetime(*parsed[:6]).date()
            except (TypeError, ValueError):
                continue

    # Fallback: parse the raw date string, handling ordinal suffixes like "9th Apr 2026"
    # (Joseph Rowntree Foundation's RSS feed uses this format)
    for key in ("published", "updated", "created"):
        raw = entry.get(key)
        if not raw:
            continue
        cleaned = _ORDINAL_RE.sub(r"\1", raw).strip()
        for fmt in ("%d %b %Y", "%d %B %Y", "%Y-%m-%d", "%B %d, %Y"):
            try:
                return datetime.strptime(cleaned, fmt).date()
            except ValueError:
                continue
    return None


def _entry_text(entry) -> str:
    # Prefer content > summary > description
    if entry.get("content"):
        try:
            return entry.content[0].value
        except (AttributeError, IndexError, KeyError):
            pass
    return entry.get("summary") or entry.get("description") or ""


def scrape(*, source: str, feed_url: str,
           since_date: date | None = None,
           until_date: date | None = None,
           apply_relevance_filter: bool = False,
           require_keywords: tuple[str, ...] | list[str] | None = None,
           **_ignored) -> list[Article]:
    """Parse an RSS / Atom / Google Alert feed, return Articles.

    Filtering options for broad sources (e.g. Belfast Telegraph whole-paper
    feed, LGA, BBC general):
      apply_relevance_filter=True  →  use DEFAULT_EDUCATION_KEYWORDS
      require_keywords=[...]       →  use a custom keyword list
    Rejected entries are written to data/archive/rejected/<date>_<source>.csv.
    Narrow sources should leave both unset.
    """
    parsed = feedparser.parse(feed_url)
    if parsed.bozo and not parsed.entries:
        print(f"  feedparser bozo for {source}: {parsed.bozo_exception}")
        return []

    # Compile keyword patterns once per scrape (lazy — only if filtering)
    kw_list: tuple[str, ...] | None = None
    kw_patterns = None
    if apply_relevance_filter or require_keywords is not None:
        kw_list = tuple(require_keywords) if require_keywords is not None else DEFAULT_EDUCATION_KEYWORDS
        kw_patterns = compile_keyword_patterns(kw_list)

    is_google_alert = "google.com/alerts" in feed_url or "google.co.uk/alerts" in feed_url
    articles: list[Article] = []
    seen_urls: set[str] = set()
    n_rejected = 0

    for e in parsed.entries:
        url = e.get("link") or ""
        if is_google_alert:
            url = _unwrap_google_url(url)
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        article_date = _entry_date(e)
        if since_date and article_date and article_date < since_date:
            continue
        if until_date and article_date and article_date > until_date:
            continue

        title = _strip_html(e.get("title") or "")
        text = _strip_html(_entry_text(e))

        # Relevance filter — drop entries that don't match any keyword
        if kw_patterns is not None:
            haystack = (title + " " + text).lower()
            matched = [kw for kw, p in zip(kw_list, kw_patterns) if p.search(haystack)]
            if not matched:
                log_rejection(
                    source=source,
                    url=url,
                    title=title,
                    source_type="rss",
                    article_date=article_date,
                    matched_keywords_attempted=[],
                )
                n_rejected += 1
                continue

        articles.append(Article(
            url=url,
            title=title,
            article_date=article_date,
            source=source,
            source_type="rss",
            text=text,
            text_clean=build_text_clean(title, text),
        ))

    if kw_patterns is not None and n_rejected:
        print(f"  {source}: {n_rejected} entries rejected by relevance filter "
              f"(see data/archive/rejected/)")

    return articles
