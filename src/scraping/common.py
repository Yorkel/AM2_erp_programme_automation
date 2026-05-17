"""
common.py
Shared building blocks for every source: row shape, HTTP helper with retries,
date parsing, and the text_clean builder (title + first ~80 words).
"""

from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Iterable

import requests
from bs4 import BeautifulSoup

# -----------------------------------------------------------------------
# Article row shape
# -----------------------------------------------------------------------
# Every source (web scraper or newsletter parser) returns Article objects.
# `to_record()` produces a dict ready for upsert into articles.

MAX_SNIPPET_WORDS = 80  # match s02b_scrape.py — keeps text_clean shape consistent with training


@dataclass
class Article:
    url: str
    title: str | None = None
    article_date: date | None = None
    source: str = ""
    source_type: str = "web"           # 'web' | 'newsletter' | 'rss'
    text: str | None = None            # full body
    text_clean: str | None = None      # title + first ~80 words; built if not provided
    week_number: int | None = None
    extra: dict = field(default_factory=dict)

    def to_record(self) -> dict:
        if not self.text_clean:
            self.text_clean = build_text_clean(self.title, self.text)
        rec = {
            "url": self.url,
            "title": self.title,
            "article_date": self.article_date.isoformat() if self.article_date else None,
            "source": self.source,
            "source_type": self.source_type,
            "text": self.text,
            "text_clean": self.text_clean,
            "week_number": self.week_number,
        }
        return {k: v for k, v in rec.items() if v is not None}


def build_text_clean(title: str | None, body: str | None, max_words: int = MAX_SNIPPET_WORDS) -> str:
    """Build the title + first N words snippet that the classifier expects."""
    title = (title or "").strip()
    body = (body or "").strip()
    if not body:
        return title
    snippet_words = body.split()[:max_words]
    snippet = " ".join(snippet_words)
    return (title + " " + snippet).strip()


# -----------------------------------------------------------------------
# HTTP helper with retries
# -----------------------------------------------------------------------
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AM2-erp-bot/1.0; +https://github.com/anthropic/AM2)"
}

DEFAULT_TIMEOUT = 15
DEFAULT_SLEEP = 0.8


def http_get(url: str, *, headers: dict | None = None, timeout: int = DEFAULT_TIMEOUT,
             retries: int = 2, backoff: float = 1.5) -> requests.Response | None:
    """GET with simple retry + backoff. Returns Response or None on terminal failure."""
    hdrs = {**DEFAULT_HEADERS, **(headers or {})}
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, headers=hdrs, timeout=timeout, allow_redirects=True)
            if r.status_code >= 500:
                raise requests.HTTPError(f"{r.status_code} for {url}")
            r.raise_for_status()
            return r
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(backoff * (attempt + 1))
    print(f"  http_get failed for {url}: {last_err}")
    return None


def soup_of(url: str, **kwargs) -> BeautifulSoup | None:
    r = http_get(url, **kwargs)
    if r is None:
        return None
    return BeautifulSoup(r.text, "html.parser")


# -----------------------------------------------------------------------
# Date parsing
# -----------------------------------------------------------------------
_MONTHS = "(January|February|March|April|May|June|July|August|September|October|November|December)"

_DATE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d", "%d %B %Y", "%d %b %Y", "%B %d, %Y", "%b %d, %Y",
    "%d/%m/%Y", "%Y/%m/%d",
)


def parse_date_loose(text: str | None) -> date | None:
    """Try a handful of common date formats; return date or None."""
    if not text:
        return None
    s = text.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    m = re.search(rf"\b(\d{{1,2}}\s+{_MONTHS}\s+\d{{4}})\b", s)
    if m:
        try:
            return datetime.strptime(m.group(1), "%d %B %Y").date()
        except ValueError:
            pass
    return None


# -----------------------------------------------------------------------
# Text body extraction (generic — fallback for unknown sites)
# -----------------------------------------------------------------------
_BOILERPLATE_TAGS = ("script", "style", "nav", "header", "footer", "aside", "form", "noscript")


def extract_body_text(soup: BeautifulSoup, max_paragraphs: int = 20) -> str:
    """Pull text from <article>/<main>/role=main, falling back to the whole body.

    Mirrors s02b_scrape.py's approach so that web-scraped articles produce
    text in the same shape as the training-time scraped snippets.

    Boilerplate tags are stripped AFTER finding the container, not before — some
    sites (e.g. ASCL on ASP.NET) wrap the entire page in <form>, so a top-level
    decompose would delete the article along with the nav.
    """
    # 1. Find the article container first.
    container = (
        soup.find("article")
        or soup.find("main")
        or soup.find(attrs={"role": "main"})
        or soup.find("body")
        or soup
    )
    # 2. Strip boilerplate INSIDE the container (preserves content for pages
    #    that put the article inside a form/header/etc. at the outer page level).
    for tag in container(_BOILERPLATE_TAGS):
        tag.decompose()
    # 3. Prefer <p> tags; fall back to whole-container text for sites that
    #    don't use <p> (e.g. ASCL uses nested <div>s with <strong>/<em>).
    paragraphs = container.find_all("p")
    if paragraphs:
        return " ".join(p.get_text(" ", strip=True) for p in paragraphs[:max_paragraphs])
    return container.get_text(" ", strip=True)


# -----------------------------------------------------------------------
# Validation helpers for try_source.py
# -----------------------------------------------------------------------
REQUIRED_FIELDS = ("url", "title")


def validate_rows(rows: Iterable[dict | Article]) -> dict:
    """Return a small summary dict used by try_source.py."""
    rows = [r.to_record() if isinstance(r, Article) else r for r in rows]
    n = len(rows)
    if n == 0:
        return {"count": 0, "issues": ["no rows returned"]}

    issues: list[str] = []

    for field_name in REQUIRED_FIELDS:
        missing = sum(1 for r in rows if not r.get(field_name))
        if missing:
            issues.append(f"{missing}/{n} rows missing {field_name}")

    no_date = sum(1 for r in rows if not r.get("article_date"))
    if no_date:
        issues.append(f"{no_date}/{n} rows have no article_date")

    no_text = sum(1 for r in rows if not (r.get("text") or r.get("text_clean")))
    if no_text:
        issues.append(f"{no_text}/{n} rows have no text and no text_clean")

    urls = [r.get("url") for r in rows if r.get("url")]
    dupes = len(urls) - len(set(urls))
    if dupes:
        issues.append(f"{dupes} duplicate urls within this run")

    return {"count": n, "issues": issues, "first": rows[0], "last": rows[-1]}
