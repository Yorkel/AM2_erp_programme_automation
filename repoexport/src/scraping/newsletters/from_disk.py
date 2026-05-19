"""
newsletters/from_disk.py
Reads inbound newsletter HTML files from data/inbound_newsletters/ and
extracts candidate articles. This is the no-OAuth path: save a newsletter
.html file (or .eml's HTML part) into the inbound directory and the
pipeline picks it up next run.

Directory layout expected:
    data/inbound_newsletters/
      ├── wonkhe/
      │   └── 2026-05-12.html
      ├── epi/
      │   └── 2026-05-14.html
      └── ...

The subdirectory name is the source code. The filename's date prefix
(YYYY-MM-DD) is used as default_date when the newsletter's own header
doesn't yield one.

NOTE: data/newsletters_html/ is the TRAINING corpus (past ERP newsletters).
This module deliberately does NOT touch that directory.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from src.scraping.common import Article
from src.scraping.newsletters.parse_html import (
    extract_issue_date,
    fetch_link_bodies,
    parse_newsletter_html,
)

INBOUND_DIR = Path("data/inbound_newsletters")

_DATE_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def _date_from_filename(name: str) -> date | None:
    m = _DATE_PREFIX_RE.match(name)
    if not m:
        return None
    try:
        return date.fromisoformat(m.group(1))
    except ValueError:
        return None


def scrape(*, source: str, since_date: date | None = None,
           until_date: date | None = None, follow_links: bool = True,
           inbound_dir: Path | None = None) -> list[Article]:
    """Parse all files under data/inbound_newsletters/<source>/ for one source.

    `follow_links=True` (the default) fetches each link's article body and
    rebuilds text_clean from the real article. Set False for fast iteration
    or when the curator description is enough.
    """
    root = (inbound_dir or INBOUND_DIR) / source
    if not root.exists():
        print(f"  no inbound directory for source={source} ({root})")
        return []

    all_rows: list[Article] = []
    for path in sorted(root.glob("*.html")):
        html = path.read_text(encoding="utf-8", errors="ignore")
        issue_date = extract_issue_date(html) or _date_from_filename(path.name)
        if since_date and issue_date and issue_date < since_date:
            continue
        if until_date and issue_date and issue_date > until_date:
            continue

        rows = parse_newsletter_html(html, source=source, default_date=issue_date)
        print(f"  {path.name}: {len(rows)} candidate articles")
        all_rows.extend(rows)

    if follow_links and all_rows:
        print(f"  fetching link bodies for {len(all_rows)} articles...")
        fetch_link_bodies(all_rows)

    return all_rows
