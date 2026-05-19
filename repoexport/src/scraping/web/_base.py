"""
web/_base.py
Base pattern for HTML scrapers. Each per-site scraper module exposes:

    def scrape(since_date=None, until_date=None) -> list[Article]: ...

Use `scrape_listing()` as the standard recipe for a "listing page + article
pages" site (gov.uk, schoolsweek, etc.). For unusual sites, ignore this and
write the scraper from scratch — the only hard contract is the function
signature and that it returns Article objects.
"""

from __future__ import annotations

import time
from datetime import date
from typing import Callable

from bs4 import BeautifulSoup

from src.scraping.common import (
    Article,
    DEFAULT_SLEEP,
    extract_body_text,
    parse_date_loose,
    soup_of,
)


def scrape_listing(
    *,
    source: str,
    start_url: str,
    list_selector: str,
    article_url_attr: str = "href",
    base_url: str = "",
    next_page_selector: str | None = None,
    article_parser: Callable[[BeautifulSoup, str], Article | None] | None = None,
    since_date: date | None = None,
    until_date: date | None = None,
    max_old_pages: int = 3,
    sleep_between_articles: float = DEFAULT_SLEEP,
) -> list[Article]:
    """Walk a listing page, follow article links, return Articles within date window.

    `article_parser(soup, url)` is the per-site bit you write. If None,
    a generic parser is used (<h1> title + <article>/<main> body).
    """
    seen: set[str] = set()
    articles: list[Article] = []
    url = start_url
    page = 1
    old_streak = 0
    parser = article_parser or _generic_article_parser

    while url:
        print(f"  page {page}: {url}")
        soup = soup_of(url)
        if soup is None:
            break

        links = [a.get(article_url_attr) for a in soup.select(list_selector) if a.get(article_url_attr)]
        links = [base_url + l if base_url and l.startswith("/") else l for l in links]

        page_has_recent = False
        for link in links:
            if link in seen:
                continue
            seen.add(link)
            asoup = soup_of(link)
            if asoup is None:
                continue
            art = parser(asoup, link)
            if art is None:
                continue
            art.source = source
            art.source_type = "web"

            if until_date and art.article_date and art.article_date > until_date:
                continue
            articles.append(art)
            if since_date and art.article_date and art.article_date >= since_date:
                page_has_recent = True
            elif since_date is None:
                page_has_recent = True

            time.sleep(sleep_between_articles)

        old_streak = 0 if page_has_recent else old_streak + 1
        if old_streak >= max_old_pages:
            print(f"  stopping: {max_old_pages} consecutive pages with nothing in range")
            break

        if not next_page_selector:
            break
        nxt = soup.select_one(next_page_selector)
        url = nxt.get("href") if nxt and nxt.get("href") else None
        if url and base_url and url.startswith("/"):
            url = base_url + url
        page += 1
        time.sleep(1)

    if since_date:
        articles = [a for a in articles if a.article_date and a.article_date >= since_date]
    if until_date:
        articles = [a for a in articles if a.article_date and a.article_date <= until_date]

    return articles


def _generic_article_parser(soup: BeautifulSoup, url: str) -> Article | None:
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else None

    body = extract_body_text(soup)
    if not body and not title:
        return None

    article_date = _find_any_date(soup)
    return Article(url=url, title=title, article_date=article_date, text=body)


def _find_any_date(soup: BeautifulSoup):
    for sel in ("time[datetime]", "time", "meta[property='article:published_time']"):
        tag = soup.select_one(sel)
        if not tag:
            continue
        candidate = tag.get("datetime") or tag.get("content") or tag.get_text(" ", strip=True)
        d = parse_date_loose(candidate)
        if d:
            return d
    d = parse_date_loose(soup.get_text(" ", strip=True)[:2000])
    return d
