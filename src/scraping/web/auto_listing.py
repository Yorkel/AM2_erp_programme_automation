"""
web/auto_listing.py
Generic listing-page scraper that auto-detects article cards by finding repeated
containers that have both a date string AND an outbound link.

Used for any site where:
  - There's a single index page listing articles
  - Each article card has a date visible in the card text
  - Each card has a link to the article's own page

Configure per source in sources.yml:

    - name: ada_lovelace_institute
      type: web
      scraper: src.scraping.web.auto_listing
      params:
        start_url: https://www.adalovelaceinstitute.org/news/

Optional params:
  container_class : CSS class substring to filter containers (e.g. "base-card")
  fetch_body      : whether to fetch each article URL for full body (default True)
  max_articles    : hard cap on items returned (default 30)
"""

from __future__ import annotations

import re
import time
from collections import Counter
from datetime import date
from bs4 import BeautifulSoup

from src.scraping.common import (
    Article,
    DEFAULT_SLEEP,
    build_text_clean,
    extract_body_text,
    parse_date_loose,
    resolve_url,
    soup_of,
)

_DATE_RE = re.compile(
    r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b|"
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b|"
    r"\b\d{4}-\d{2}-\d{2}\b",
    re.I,
)


def _find_article_containers(soup: BeautifulSoup,
                             container_class: str | None) -> list:
    """Find repeated containers that look like article cards.

    Heuristic: pick the most-repeated CSS class signature among elements
    that contain BOTH a date string AND an <a href>.
    """
    candidates: list[tuple] = []
    for el in soup.find_all(["article", "li", "div", "section"], class_=True):
        cls_list = el.get("class", []) or []
        if container_class and container_class not in " ".join(cls_list):
            continue
        text = el.get_text(" ", strip=True)
        if not _DATE_RE.search(text):
            continue
        if not el.find("a", href=True):
            continue
        candidates.append((el, " ".join(cls_list)))

    if not candidates:
        return []

    counts = Counter(c for _, c in candidates)
    top_cls, n = counts.most_common(1)[0]
    if n < 2:
        # Only one match — accept it (some sites have featured-article layouts)
        return [el for el, _ in candidates[:1]]
    return [el for el, c in candidates if c == top_cls]


def _extract_from_container(container, base_url: str) -> tuple[str, str, date | None]:
    """Pull (title, url, date) out of a single article-card container."""
    # Title: first h2/h3/h4 inside, else first long anchor text
    h = container.find(["h1", "h2", "h3", "h4", "h5"])
    title = ""
    if h:
        title = h.get_text(" ", strip=True)
    # URL: first <a href> that points to an article (skip empty / # links)
    url = ""
    for a in container.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue
        url = resolve_url(href, base_url)
        if not title:
            title = a.get_text(" ", strip=True)
        break
    # Date: first match in container text
    text = container.get_text(" ", strip=True)
    m = _DATE_RE.search(text)
    art_date = parse_date_loose(m.group(0)) if m else None
    return title, url, art_date


def scrape(*, source: str,
           start_url: str,
           container_class: str | None = None,
           fetch_body: bool = True,
           max_articles: int = 30,
           since_date: date | None = None,
           until_date: date | None = None,
           sleep: float = DEFAULT_SLEEP,
           **_ignored) -> list[Article]:
    """Auto-detect article cards on a single listing page and return Articles."""
    soup = soup_of(start_url)
    if soup is None:
        print(f"  auto_listing: failed to fetch {start_url}")
        return []

    containers = _find_article_containers(soup, container_class)
    if not containers:
        print(f"  auto_listing: no article containers found at {start_url}")
        return []

    articles: list[Article] = []
    seen_urls: set[str] = set()

    for container in containers[:max_articles]:
        title, url, art_date = _extract_from_container(container, start_url)
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        if since_date and art_date and art_date < since_date:
            continue
        if until_date and art_date and art_date > until_date:
            continue

        body = ""
        if fetch_body:
            asoup = soup_of(url)
            if asoup is not None:
                body = extract_body_text(asoup)
            time.sleep(sleep)

        articles.append(Article(
            url=url,
            title=title or "",
            article_date=art_date,
            source=source,
            source_type="web",
            text=body,
            text_clean=build_text_clean(title, body),
        ))

    return articles
