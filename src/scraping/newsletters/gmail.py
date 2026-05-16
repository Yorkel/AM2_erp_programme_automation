"""
newsletters/gmail.py
Gmail-API ingestion. NOT IMPLEMENTED YET.

Phase 4 plan: read newsletters from a Gmail account by label/sender,
parse the HTML part with parse_html.parse_newsletter_html, and return
Articles in the same shape as from_disk.py.

Required env vars (when implemented):
    GMAIL_CLIENT_ID
    GMAIL_CLIENT_SECRET
    GMAIL_REFRESH_TOKEN
    GMAIL_LABEL (e.g. "newsletters/erp")

Required deps (when implemented):
    google-api-python-client
    google-auth-oauthlib
    google-auth-httplib2

Until then, use from_disk.py: save newsletters as HTML files into
data/inbound_newsletters/<source>/<YYYY-MM-DD>.html.
"""

from __future__ import annotations

from datetime import date

from src.scraping.common import Article


def scrape(*, source: str, since_date: date | None = None,
           until_date: date | None = None) -> list[Article]:
    raise NotImplementedError(
        "newsletters.gmail.scrape is not implemented yet. "
        "For now, save newsletters as HTML files under data/inbound_newsletters/<source>/ "
        "and use newsletters.from_disk.scrape instead."
    )
