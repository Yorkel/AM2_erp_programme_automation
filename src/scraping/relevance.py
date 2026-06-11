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
from urllib.parse import urlparse


# Hard-block list: URLs from these domains are dropped before the keyword
# filter runs, regardless of `apply_relevance_filter`. Social media + known
# low-quality clickbait that has been observed slipping through.
BLOCKED_DOMAINS: tuple[str, ...] = (
    # Social media — never the original source
    "instagram.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "tiktok.com",
    "youtube.com",
    "youtu.be",
    "linkedin.com",
    # Aggregators / non-primary sources
    "msn.com",
    "pressreader.com",
    "uk.news.yahoo.com",
    # Observed low-signal sources
    "uknip.co.uk",
    "tvguide.co.uk",
    "abplive.com",
    "news-line.co.uk",          # Workers Revolutionary Party paper (earlier guess)
    "wrp.org.uk",                # Workers Revolutionary Party (actual domain)
    "mirror.co.uk",              # UK tabloid
    "standard.co.uk",            # Evening Standard — curator-dropped 2026-06-11
    "smh.com.au",                # Sydney Morning Herald
    "e.vnexpress.net",           # Vietnamese news
)

# Reject URLs whose path contains any of these substrings, regardless of domain.
# Targets non-UK / non-education sections within otherwise-legitimate sites
# (e.g. Guardian's /us-news/, BBC's /sport/ sub-paths).
BLOCKED_URL_PATTERNS: tuple[str, ...] = (
    "/us-news/",
    "/us-education/",
    "/world/india/",
    "/world/us/",
    "/world/asia/",
    "/sport/",
    "/cricket/",
    "/ipl/",
    "/entertainment/",
    "/celebrity/",
    "/film/",
    "/films/",
    "/movies/",
    "/fashion/",
    "/lifestyle/",
    "/travel/",
    "/slade/",
)


def is_blocked_domain(url: str) -> bool:
    """True if `url` is on the hard-block domain list (sub-domains included)."""
    if not isinstance(url, str) or not url:
        return False
    netloc = urlparse(url).netloc.lower().lstrip(".")
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return any(netloc == d or netloc.endswith("." + d) for d in BLOCKED_DOMAINS)


def is_blocked_url_pattern(url: str) -> bool:
    """True if the URL path matches a blocked section pattern (case-insensitive)."""
    if not isinstance(url, str) or not url:
        return False
    path = urlparse(url).path.lower()
    return any(p in path for p in BLOCKED_URL_PATTERNS)


# Country-context terms that disqualify an article as non-UK. Matched on
# title + body together. Conservative — common demonyms like "American"/"Indian"
# are excluded because they appear in legitimately-UK-relevant content
# (e.g. "Indian students in UK universities"). Locations + heads-of-state
# are the surer signal.
NEGATIVE_COUNTRY_KEYWORDS: tuple[str, ...] = (
    # United States
    "usa", "virginia", "texas", "california", "florida", "ohio",
    "new york state", "washington dc", "los angeles", "chicago", "boston",
    "white house", "donald trump", "biden",
    "u.s. department", "us department of education",
    # US universities (added 2026-05-26 after Harvard A-grade story slipped through)
    "harvard", "yale", "stanford", "princeton", "columbia university", "cornell",
    "mit", "berkeley", "ucla",
    # India
    "mumbai", "delhi", "chennai", "kolkata", "bengaluru",
    "narendra modi", "ipl 2026", "ipl 2025", "tamil nadu", "kerala",
    "abp live",
    # Pakistan / South Asia (also covers India spillover)
    "islamabad", "karachi", "lahore",
    # Australia / NZ
    "australia", "australian", "sydney", "melbourne", "brisbane", "canberra", "auckland",
    # Continental Europe (general — not London EU coverage)
    "germany", "berlin", "munich", "frankfurt",
    "paris suburb", "marseille", "france",
    "spain", "madrid", "barcelona",
    "italy", "rome italy", "milan",
    "switzerland", "swiss", "zurich", "geneva",
    # Middle East
    "tehran", "beirut", "damascus",
    "gaza", "west bank", "nakba",
    # East Asia
    "china", "japan", "tokyo", "beijing", "shanghai", "seoul", "pyongyang",
    # Pacific / Commonwealth overseas
    "solomon islands", "honiara", "fiji", "suva", "papua new guinea",
    "vanuatu", "samoa", "tonga", "kiribati",
    # British overseas territories / Crown dependencies covered overseas
    "bermuda", "cayman islands", "british virgin islands", "falkland islands",
    "saint helena", "gibraltar", "anguilla", "turks and caicos",
    # Caribbean
    "jamaica", "trinidad and tobago", "bahamas", "barbados",
    # Africa (UK FCDO sometimes publishes overseas-mission stories)
    "kenya", "uganda", "nigeria", "ghana", "south africa", "zimbabwe",
    "tanzania", "ethiopia", "rwanda", "sierra leone",
    # Other
    "kremlin", "moscow",
)

_NEGATIVE_COUNTRY_PATTERNS: list | None = None  # lazy — compile_keyword_patterns defined below


def is_non_uk_content(title: str | None, body: str | None) -> str | None:
    """Return the matching negative-country keyword if `title+body` reads as
    non-UK content, else None. Used to filter articles that are about
    education-elsewhere rather than UK education."""
    global _NEGATIVE_COUNTRY_PATTERNS
    if _NEGATIVE_COUNTRY_PATTERNS is None:
        _NEGATIVE_COUNTRY_PATTERNS = compile_keyword_patterns(NEGATIVE_COUNTRY_KEYWORDS)
    haystack = ((title or "") + " " + (body or "")).lower()
    if not haystack.strip():
        return None
    for kw, p in zip(NEGATIVE_COUNTRY_KEYWORDS, _NEGATIVE_COUNTRY_PATTERNS):
        if p.search(haystack):
            return kw
    return None


# Approved-domain allowlist. Articles whose URL netloc isn't in this list are
# dropped at scrape time — regardless of which source/alert surfaced them.
# Derived from data/sources_master.csv URLs (+ a few hand-added approved
# domains: bbc.co.uk, teachertapp.com, education-ni.gov.uk). Sub-domains of
# an approved domain also pass (e.g. educationhub.blog.gov.uk matches gov.uk).
# To regenerate after editing sources_master.csv:
#   python -c "from urllib.parse import urlparse; import pandas as pd; \
#     df = pd.read_csv('data/sources_master.csv'); \
#     print(sorted({urlparse(u).netloc.lower().lstrip('.').removeprefix('www.') for u in df['url'].dropna()}))"
APPROVED_DOMAINS: tuple[str, ...] = (
    "5rightsfoundation.com",
    "adalovelaceinstitute.org",
    "ades.scot",
    "ascl.org.uk",
    "bbc.co.uk",
    "belfasttelegraph.co.uk",
    "bera.ac.uk",
    "blogs.gov.scot",
    "blogs.ucl.ac.uk",
    "cfey.org",
    "chartered.college",
    "childreninscotland.org.uk",
    "childrens-participation.org",
    "childrenscommissioner.gov.uk",
    "closer.ac.uk",
    "committees.parliament.uk",
    "cpag.org.uk",
    "cstuk.org.uk",
    "defenddigitalme.org",
    "digitalpovertyalliance.org",
    "durham.ac.uk",
    "edtech.oii.ox.ac.uk",
    "education-ni.gov.uk",
    "educationdevelopmenttrust.com",
    "educationendowmentfoundation.org.uk",
    "epi.org.uk",
    "eppi.ioe.ac.uk",
    "fed.education",
    "ffteducationdatalab.org.uk",
    "futuregenerations.wales",
    "gla.ac.uk",
    "google.co.uk",
    "gov.scot",
    "gov.uk",
    "gov.wales",
    "greatermanchester-ca.gov.uk",
    "gtcs.org.uk",
    "hepi.ac.uk",
    "hwb.gov.wales",
    "instituteforgovernment.org.uk",
    "jacobsfoundation.org",
    "joehallgarten.substack.com",
    "jrf.org.uk",
    "local.gov.uk",
    "lpiphub.bham.ac.uk",
    "magicsmoke.substack.com",
    "matthewevanseducation.substack.com",
    "mmu.ac.uk",
    "naht.org.uk",
    "nesta.org.uk",
    "neu.org.uk",
    "nfer.ac.uk",
    "northernireland.gov.uk",
    "nottingham.ac.uk",
    "nuffieldfoundation.org",
    "oecd.org",
    "parliament.scot",
    "parliament.uk",
    "post.parliament.uk",
    "profbeckyallen.substack.com",
    "publicengagement.ac.uk",
    "ripl.uk",
    "schoolsweek.co.uk",
    "senedd.wales",
    "sera.ac.uk",
    "spice-spotlight.scot",
    "suttontrust.com",
    "teacherselect.org",
    "teachertapp.co.uk",
    "teachertapp.com",
    "tes.com",
    # "theguardian.com",  # REMOVED 2026-05-28 — Gemma curator ask, source dropped
    "theippo.co.uk",
    "tpea.ac.uk",
    "ucl.ac.uk",
    "ukri.org",
    "upen.us14.list-manage.com",
    "wcpp.org.uk",
    "wonkhe.com",
)

# Broad subset of APPROVED_DOMAINS where the keyword filter must additionally
# pass before the article is kept. These are general-purpose sources
# (BBC, Guardian, universities, parliaments, broader policy bodies) that
# publish on many topics, not just education.
BROAD_DOMAINS: tuple[str, ...] = (
    # General news / TV
    "bbc.co.uk",
    "belfasttelegraph.co.uk",
    # "theguardian.com",  # REMOVED 2026-05-28 — Gemma curator ask, source dropped
    # Universities (their news pages publish on every research area)
    "durham.ac.uk",
    "gla.ac.uk",
    "mmu.ac.uk",
    "nottingham.ac.uk",
    "ucl.ac.uk",
    # Government — broad-policy publishers (added 2026-05-26)
    "gov.uk",
    "gov.scot",
    "gov.wales",
    "hwb.gov.wales",
    "northernireland.gov.uk",
    "local.gov.uk",
    # Parliaments + select committees
    "committees.parliament.uk",
    "parliament.scot",
    "parliament.uk",
    "post.parliament.uk",
    "senedd.wales",
    "spice-spotlight.scot",
    # Broader policy / research orgs
    "adalovelaceinstitute.org",
    "closer.ac.uk",
    "futuregenerations.wales",
    "instituteforgovernment.org.uk",
    "jrf.org.uk",
    "nesta.org.uk",
    "oecd.org",
    "theippo.co.uk",
    "ukri.org",
    "wcpp.org.uk",
    # Single-author general-topic Substacks
    "magicsmoke.substack.com",
)


# Title-keyword blocklist — articles whose title contains any of these
# (word-boundary match) are dropped, regardless of source. Editorial scope
# decision: trans-rights coverage is out of scope for the ERP newsletter.
BLOCKED_TITLE_KEYWORDS: tuple[str, ...] = (
    "trans",
    "transgender",
    "private school",
    "rape",
    "sentencing",
    "immigration",
    "transparency data",
    # Routine DfE/gov.uk regulatory notices — not newsletter content.
    # Curator ask 2026-06-09: drop "Notice to improve:" + "warning notice" items.
    "notice to improve",
    "warning notice",
)


# Known paywall domains — articles from these are dropped before the
# approved-domain check, even if the domain were ever added to APPROVED_DOMAINS.
# Belts-and-braces: protects against accidental approval. Curators can add
# observed paywall domains here as they appear.
PAYWALL_DOMAINS: tuple[str, ...] = (
    "telegraph.co.uk",
    "thetimes.com",
    "thetimes.co.uk",
    "thesundaytimes.co.uk",
    "ft.com",
    "spectator.co.uk",
    "spectator.com",
    "thesun.co.uk",  # tabloid, partial paywall
)

_APPROVED_DOMAINS_SET = frozenset(APPROVED_DOMAINS)
_BROAD_DOMAINS_SET = frozenset(BROAD_DOMAINS)
_PAYWALL_DOMAINS_SET = frozenset(PAYWALL_DOMAINS)
_BLOCKED_TITLE_PATTERNS: list | None = None  # lazy-compiled on first use


def _article_netloc(url: str) -> str:
    """Normalise a URL down to its netloc — lowercased, leading dots stripped,
    `www.` stripped. Returns "" for invalid input."""
    if not isinstance(url, str) or not url:
        return ""
    netloc = urlparse(url).netloc.lower().lstrip(".")
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def is_approved_domain(url: str) -> bool:
    """True if `url`'s netloc exactly matches an entry in APPROVED_DOMAINS.

    NOTE: exact match only — sub-domains of an approved domain are NOT
    automatically approved. This avoids accidentally approving e.g.
    argyll-bute.gov.uk (a council on the gov.uk subdomain) when only gov.uk
    is intended. Add new sub-domains explicitly to APPROVED_DOMAINS if needed.
    """
    return _article_netloc(url) in _APPROVED_DOMAINS_SET


def matched_blocked_title_keyword(title: str | None) -> str | None:
    """Return the first matching BLOCKED_TITLE_KEYWORDS entry if `title`
    contains any of them (word-boundary), else None. Used to drop articles
    on out-of-scope topics regardless of which approved source surfaced them."""
    global _BLOCKED_TITLE_PATTERNS
    if not isinstance(title, str) or not title.strip():
        return None
    if _BLOCKED_TITLE_PATTERNS is None:
        _BLOCKED_TITLE_PATTERNS = compile_keyword_patterns(BLOCKED_TITLE_KEYWORDS)
    haystack = title.lower()
    for kw, p in zip(BLOCKED_TITLE_KEYWORDS, _BLOCKED_TITLE_PATTERNS):
        if p.search(haystack):
            return kw
    return None


def is_paywall_domain(url: str) -> bool:
    """True if `url`'s netloc exactly matches a known paywall domain
    (see PAYWALL_DOMAINS). Checked before is_approved_domain() so paywall
    rejections get a specific reason in the rejection log."""
    return _article_netloc(url) in _PAYWALL_DOMAINS_SET


def is_broad_domain(url: str) -> bool:
    """True if `url`'s netloc is on the BROAD_DOMAINS subset of approved
    sources. Broad-domain articles need the education keyword filter to
    pass before being kept (general news / university news / parliaments
    cover many topics, not just education). Exact match only — same rule
    as is_approved_domain()."""
    return _article_netloc(url) in _BROAD_DOMAINS_SET


DEFAULT_EDUCATION_KEYWORDS: tuple[str, ...] = (
    # Core schools + sectors
    "school", "schools", "pupil", "pupils", "student", "students",
    "teacher", "teachers", "teaching", "classroom",
    "primary", "secondary", "nursery", "early years", "eyfs",
    # "trust"/"trusts" removed 2026-05-26 — too broad (matched "undermine
    # trust in government" etc.). Academy trusts still caught by "academy"/
    # "academies"/"trustees"/"governance" below.
    "academy", "academies",
    "college", "colleges", "further education", "sixth form",
    # HE keywords removed 2026-05-26 — newsletter is schools/pre-HE/FE only
    # (university/universities/higher education/campus → out of scope; HE
    # publications like Wonkhe/HEPI are deliberately not re-enabled).
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
    # "dfe" removed 2026-05-26 — generic "DfE Update" bulletins were slipping
    # through. Real DfE policy articles still match via "department for
    # education", "schools", "send", etc.
    "department for education", "department education",
    "schools week", "schoolsweek",
    "select committee", "education committee",
    "minister", "education minister", "education secretary",
    # Pedagogy / research
    "research", "evidence-based", "pedagogy",
    "education research", "education policy",
    # Demographic / broader
    # "young people"/"youth" removed 2026-05-26 — too broad (matched health
    # and social-services content, not just education).
    "child", "children",
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
