"""
relevance.py
Per-source education-relevance filter. Used by scrapers (currently rss_adapter)
to drop articles that don't contain at least one education-related keyword in
their title or text.

When `apply_relevance_filter=True` is set on a source in sources.yml, the
scraper uses DEFAULT_EDUCATION_KEYWORDS below. Rejected articles are written
to data/archive/rejected/<YYYY-MM-DD>_<source>.csv for audit.

Designed for broad sources (whole-paper feeds, general gov.uk alerts, etc.)
that mix education content with other topics. Narrow sources (Schools Week,
NFER, EEF) don't need this filter and shouldn't have it set.

Keyword list derived 2026-05-17 from 1109 curator-published newsletter items
(train.csv + val.csv). Methodology: most frequent education-relevant unigrams
and bigrams, hand-curated for precision. Tested against 854 backfill articles:
96.4% pass rate overall, 100% pass on the 6 articles that were curator-published.
See docs/decisions/relevance_filter_2026_05_17.md (when written) for the
analysis trail.
"""

from __future__ import annotations

import csv
import re
from datetime import date, datetime
from pathlib import Path
from threading import Lock


DEFAULT_EDUCATION_KEYWORDS: tuple[str, ...] = (
    # Core schools + sectors
    "school", "schools", "pupil", "pupils", "student", "students",
    "teacher", "teachers", "teaching", "classroom",
    "primary", "secondary", "nursery", "early years", "eyfs",
    "academy", "academies", "trust", "trusts",
    "college", "colleges", "further education", "sixth form",
    "university", "universities", "higher education", "campus",
    "education", "educational",
    # Curriculum & assessment
    "curriculum", "gcse", "a-level", "a level", "phonics",
    "literacy", "numeracy", "stem",
    "ofsted", "ofqual", "inspection",
    "exam", "exams", "examination",
    # SEND & inclusion (UK + Scottish terms)
    "send", "ehcp", "special needs", "special educational",
    "additional support for learning", "asl", "additional support needs", "asn",
    "alternative provision",
    "disability", "disabilities",
    "free school meals", "fsm", "disadvantage", "disadvantaged",
    "attendance",
    "safeguarding", "online safety", "behaviour", "exclusion", "exclusions",
    # Workforce
    "recruitment", "retention", "training", "cpd",
    "headteacher", "head teacher",
    "professional learning",
    "early career framework", "ecf",
    "governance", "trustees",
    # Policy bodies / actors
    "dfe", "department for education", "department education",
    "schools week", "schoolsweek",
    "select committee", "education committee",
    "minister", "education minister", "education secretary",
    # Pedagogy / research
    "research", "evidence-based", "pedagogy",
    "education research", "education policy",
    # Demographic / broader
    "child", "children", "young people", "youth",
    "skills", "apprenticeship", "apprenticeships",
    # Specific frequently-newslettered topics
    "white paper", "schools bill", "curriculum assessment",
    "child poverty", "mental health", "wellbeing",
)


def compile_keyword_patterns(keywords: tuple[str, ...] | list[str]) -> list[re.Pattern]:
    """Compile keyword strings into word-boundary regex patterns (case-insensitive)."""
    patterns = []
    for kw in keywords:
        kw_l = kw.lower().strip()
        if not kw_l:
            continue
        if " " in kw_l or "-" in kw_l:
            patterns.append(re.compile(rf"(?<!\w){re.escape(kw_l)}(?!\w)"))
        else:
            patterns.append(re.compile(rf"\b{re.escape(kw_l)}\b"))
    return patterns


def matched_keywords(text: str, patterns: list[re.Pattern],
                     keywords: tuple[str, ...] | list[str] | None = None) -> list[str]:
    """Return the list of keywords that match in `text`. Empty list = filter rejects."""
    if not isinstance(text, str) or not text.strip():
        return []
    t = text.lower()
    if keywords is None:
        # Return abstract markers when caller didn't supply the original keyword list
        return [p.pattern for p in patterns if p.search(t)]
    return [kw for kw, p in zip(keywords, patterns) if p.search(t)]


REJECTION_DIR = Path("data/archive/rejected")
_REJECTION_LOCK = Lock()
_REJECTION_HEADER = (
    "url", "title", "source", "source_type", "article_date",
    "matched_keywords_attempted", "rejected_at"
)


def log_rejection(*, source: str, url: str, title: str, source_type: str,
                  article_date: date | None, matched_keywords_attempted: list[str]) -> None:
    """Append one rejected-article row to data/archive/rejected/<date>_<source>.csv.

    Thread-safe (we use a process-wide lock — scrapers are single-threaded per
    source, but multiple sources may share this module). Idempotent in spirit:
    even if called twice for the same URL, both rows go in — the rejection log
    is an audit trail, not a deduplicated store.
    """
    REJECTION_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REJECTION_DIR / f"{datetime.now().date().isoformat()}_{source}.csv"
    write_header = not out_path.exists()
    row = (
        url,
        title or "",
        source,
        source_type,
        article_date.isoformat() if article_date else "",
        ";".join(matched_keywords_attempted),
        datetime.now().isoformat(timespec="seconds"),
    )
    with _REJECTION_LOCK:
        with open(out_path, "a", newline="") as f:
            w = csv.writer(f)
            if write_header:
                w.writerow(_REJECTION_HEADER)
            w.writerow(row)
