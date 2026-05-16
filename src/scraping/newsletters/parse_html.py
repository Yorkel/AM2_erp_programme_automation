"""
newsletters/parse_html.py
Generic HTML newsletter parser.

This is intentionally minimal — newsletters from different senders have
wildly different markup, so most newsletter sources will need a small
per-sender override. The shape:

    parse_newsletter_html(html, *, source, default_date=None) -> list[Article]

Returns one Article per link found in the newsletter, where each Article
captures the link's anchor text as title and the surrounding paragraph as
text. If the link points to an external article, downstream code can
optionally fetch and replace `text` with the real article body via
fetch_link_bodies().

NOTE: This is NOT the same as src/training_data/s00_extract_newsletters.py,
which parses PAST ESRC ERP newsletters into training items. This module
parses INBOUND newsletters (Wonkhe, EPI, etc.) to extract candidate
articles for the next ESRC newsletter.
"""

from __future__ import annotations

import time
from datetime import date
from urllib.parse import parse_qs, urlparse, urlunparse, urlencode

from bs4 import BeautifulSoup

from src.scraping.common import (
    DEFAULT_SLEEP,
    Article,
    build_text_clean,
    extract_body_text,
    parse_date_loose,
    soup_of,
)

TRACK_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "mkt_tok", "mc_cid", "mc_eid", "gclid", "fbclid", "igshid", "utm_name",
}
SAFE_HOSTS = {
    "eur01.safelinks.protection.outlook.com",
    "safelinks.protection.outlook.com",
    "nam01.safelinks.protection.outlook.com",
    "emea01.safelinks.protection.outlook.com",
}

ANCHOR_BLOCKLIST = {
    "more", "read more", "view in browser", "unsubscribe",
    "click here", "here", "subscribe", "manage preferences",
}

MIN_TITLE_WORDS = 3
MAX_TITLE_WORDS = 30


def canonical_url(u: str) -> str:
    if not u:
        return ""
    u = u.strip()
    try:
        p = urlparse(u)
        if p.netloc.lower() in SAFE_HOSTS:
            inner = parse_qs(p.query).get("url", []) or parse_qs(p.query).get("URL", [])
            if inner:
                u = inner[0]
                p = urlparse(u)
        q = {k: v for k, v in parse_qs(p.query, keep_blank_values=True).items()
             if k.lower() not in TRACK_PARAMS}
        path = p.path.rstrip("/") or "/"
        return urlunparse((p.scheme.lower() or "https", p.netloc.lower(),
                           path, "", urlencode(q, doseq=True), ""))
    except Exception:
        return u


def parse_newsletter_html(html: str, *, source: str,
                          default_date: date | None = None) -> list[Article]:
    """Extract one Article per outbound link in the newsletter HTML.

    The text field is the anchor text + immediate surrounding paragraph text
    (curator description). For real article body, use fetch_link_bodies().
    """
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    rows: list[Article] = []

    for a in soup.find_all("a", href=True):
        href = canonical_url(a["href"])
        if not href or not href.startswith("http"):
            continue
        if href in seen:
            continue

        anchor_text = a.get_text(" ", strip=True)
        if not anchor_text:
            continue
        if anchor_text.lower() in ANCHOR_BLOCKLIST:
            continue
        words = anchor_text.split()
        if len(words) < MIN_TITLE_WORDS or len(words) > MAX_TITLE_WORDS:
            continue

        surrounding = _surrounding_text(a)
        text = (anchor_text + " " + surrounding).strip()

        seen.add(href)
        rows.append(Article(
            url=href,
            title=anchor_text,
            article_date=default_date,
            source=source,
            source_type="newsletter",
            text=text,
            text_clean=build_text_clean(anchor_text, surrounding),
        ))

    return rows


def _surrounding_text(a) -> str:
    """Walk up to the enclosing block and grab its text minus the anchor."""
    block = a
    for _ in range(4):
        parent = block.parent
        if parent is None or parent.name in ("body", "html"):
            break
        block = parent
        if block.name in ("p", "li", "td", "div"):
            break
    text = block.get_text(" ", strip=True)
    a_text = a.get_text(" ", strip=True)
    return text.replace(a_text, "", 1).strip()


def fetch_link_bodies(articles: list[Article], *, sleep: float = DEFAULT_SLEEP,
                      skip_domains: set[str] | None = None) -> None:
    """For each Article, fetch the URL and replace text/text_clean with real body.

    Failures are tolerated — falls back to whatever curator text was already there.
    Mutates the Articles in place.
    """
    skip = skip_domains or {
        "twitter.com", "x.com", "www.linkedin.com",
        "www.youtube.com", "youtu.be", "youtube.com", "vimeo.com",
        "www.ft.com", "www.thetimes.com", "www.telegraph.co.uk",
    }
    for art in articles:
        host = urlparse(art.url).netloc.lower()
        if host in skip:
            continue
        soup = soup_of(art.url)
        if soup is None:
            continue
        body = extract_body_text(soup)
        if body:
            art.text = body
            art.text_clean = build_text_clean(art.title, body)
        time.sleep(sleep)


def extract_issue_date(html: str) -> date | None:
    """Best-effort: pull a date out of the newsletter header."""
    soup = BeautifulSoup(html, "html.parser")
    return parse_date_loose(soup.get_text(" ", strip=True)[:1500])
