"""
web/wordpress_adapter.py
Generic WordPress REST API scraper — deep, paginated, date-filterable.

Ported from the AtlasED policy-tracker repo (2026-06-01). For any WordPress site
exposing the standard `/wp-json/wp/v2/posts` endpoint, this pulls the FULL
archive (not just the shallow latest-10 the RSS feed shows). Bodies come back in
the same response (`content.rendered`), so there's no second fetch per article.

Wire a source in sources.yml like:

    - name: sutton_trust_wp
      type: web
      scraper: src.scraping.web.wordpress_adapter
      params:
        wp_api_url: "https://www.suttontrust.com/wp-json/wp/v2/posts"
        apply_relevance_filter: true   # optional, like any source

Gotchas (see docs/wordpress_deep_backfill_guide.md §3):
  - per_page is clamped to 100 by WordPress core.
  - HTTP 400 = "past the last page" → normal end-of-feed, not an error.
  - after/before want ISO-8601 datetimes.
  - 0.5s sleep between pages to stay polite.
  - Sites that lock /wp-json (401/403) fall through cleanly (empty result).
"""

from __future__ import annotations

import time
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup

from src.scraping.common import Article, DEFAULT_HEADERS, build_text_clean


def _strip_html(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup.find_all(["script", "style", "figure", "aside"]):
        tag.decompose()
    return "\n".join(
        p.get_text(" ", strip=True)
        for p in soup.find_all("p")
        if p.get_text(strip=True)
    )


def scrape(*, source: str, wp_api_url: str,
           since_date: date | None = None,
           until_date: date | None = None,
           **_ignored) -> list[Article]:
    """Paginate a WordPress posts endpoint and return Article objects.

    Relevance filtering is applied centrally in run.py after this returns.
    """
    articles: list[Article] = []
    page = 1
    while True:
        params = {"per_page": 100, "page": page, "orderby": "date", "order": "desc"}
        if since_date:
            params["after"] = since_date.isoformat() + "T00:00:00"
        if until_date:
            params["before"] = until_date.isoformat() + "T23:59:59"

        try:
            r = requests.get(wp_api_url, headers=DEFAULT_HEADERS, params=params, timeout=30)
        except requests.RequestException as e:
            print(f"  wordpress_adapter {source}: request failed page {page}: {e}")
            break

        if r.status_code == 400:        # past the last page — done
            break
        if r.status_code != 200:        # /wp-json locked or other error — fall through
            print(f"  wordpress_adapter {source}: HTTP {r.status_code} — stopping")
            break

        try:
            posts = r.json()
        except Exception:
            break
        if not posts:
            break

        for post in posts:
            try:
                title = BeautifulSoup(post["title"]["rendered"], "html.parser").get_text(strip=True)
                body = _strip_html(post["content"]["rendered"])
                articles.append(Article(
                    url=post["link"],
                    title=title,
                    article_date=datetime.fromisoformat(post["date"]).date(),
                    source=source,
                    source_type="web",
                    text=body,
                    text_clean=build_text_clean(title, body),
                ))
            except Exception:
                continue

        if len(posts) < 100:            # short page = final page
            break
        page += 1
        time.sleep(0.5)

    return articles
