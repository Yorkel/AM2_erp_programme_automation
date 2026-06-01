"""Parameterised WordPress REST API adapter.

A generic adapter for any WordPress-powered site that exposes the standard
``/wp-json/wp/v2/posts`` endpoint. Mirrors the row-write convention used by
``src/england/schoolsweek.py`` (url, title, date, text) so the resulting
scrapers slot directly into the atlas-ed-data pipeline.

Gotchas (per scraping guide section 3):
  - ``per_page`` is silently clamped to 100 by WordPress core — do not exceed.
  - HTTP 400 from the posts endpoint means "past the last page" — treat it as
    a normal end-of-feed signal, NOT an error.
  - ``after`` / ``before`` filters expect ISO-8601 datetimes (not bare dates).
  - Sleep 0.5s between pages to stay polite and avoid rate limiting.
  - Some sites lock down ``/wp-json`` (401/403). We fall through cleanly by
    breaking out of the loop on any non-200, non-400 status code.
"""

import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; AtlasEDBot/1.0; "
        "+https://github.com/anthropic/atlas-ed-data)"
    )
}


def _strip_html(html):
    """Convert WordPress rendered HTML into plain paragraph text."""
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup.find_all(["script", "style", "figure", "aside"]):
        tag.decompose()
    paras = [
        p.get_text(" ", strip=True)
        for p in soup.find_all("p")
        if p.get_text(strip=True)
    ]
    return "\n".join(paras)


def scrape_wordpress(api_url, since_date=None, until_date=None):
    """Generic WordPress REST API scraper.

    Args:
        api_url: Full URL to the posts endpoint
            (e.g. ``https://example.com/wp-json/wp/v2/posts``).
        since_date: Optional ``datetime.date`` — only return posts published
            on or after this date.
        until_date: Optional ``datetime.date`` — only return posts published
            on or before this date.

    Returns:
        List of dicts with keys: url, title, date, text.
    """
    articles = []
    page = 1
    while True:
        # per_page max is 100 (silently clamped if higher)
        params = {"per_page": 100, "page": page, "orderby": "date", "order": "desc"}
        # after/before are ISO-8601 datetimes
        if since_date:
            params["after"] = since_date.isoformat() + "T00:00:00"
        if until_date:
            params["before"] = until_date.isoformat() + "T23:59:59"

        r = requests.get(api_url, headers=HEADERS, params=params, timeout=30)

        # HTTP 400 means past last page — treat as done, not error
        if r.status_code == 400:
            break
        # some sites restrict /wp-json (401/403) — fall through cleanly
        if r.status_code != 200:
            break

        try:
            posts = r.json()
        except Exception:
            break
        if not posts:
            break

        for post in posts:
            try:
                articles.append({
                    "url":   post["link"],
                    "title": BeautifulSoup(
                        post["title"]["rendered"], "html.parser"
                    ).get_text(strip=True),
                    "date":  datetime.fromisoformat(post["date"]).date().isoformat(),
                    "text":  _strip_html(post["content"]["rendered"]),
                })
            except Exception:
                continue

        # Short page = final page, regardless of HTTP status
        if len(posts) < 100:
            break

        page += 1
        # 0.5s sleep between pages
        time.sleep(0.5)
    return articles


def make_wp_scraper(api_url):
    """Build a scraper callable matching atlas-ed-data's scraper signature.

    The returned function has signature
    ``(since_date=None, until_date=None, output_path=None, append=False)``
    so it can be registered alongside hand-written scrapers like
    ``scrape_schoolsweek`` in ``src/run.py``.
    """
    def _scraper(since_date=None, until_date=None, output_path=None, append=False):
        rows = scrape_wordpress(
            api_url, since_date=since_date, until_date=until_date
        )
        if output_path is not None and rows:
            import pandas as pd
            df = pd.DataFrame(rows)
            if append and output_path.exists():
                existing = pd.read_csv(output_path)
                df = (
                    pd.concat([existing, df])
                    .drop_duplicates(subset=["url"])
                    .reset_index(drop=True)
                )
            df.to_csv(output_path, index=False)
        return rows
    return _scraper
