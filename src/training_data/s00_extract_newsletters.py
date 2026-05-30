"""
s00_extract_newsletters.py
Scrapes all HTML newsletter files and outputs a structured CSV.
Covers issues 1–104 (all files in newsletters_html/).
"""

import os
import re
import uuid
from glob import glob
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode

from bs4 import BeautifulSoup
import pandas as pd

# -----------------------------
# CONFIG
# -----------------------------
FOLDER = "/workspaces/AM2_erp_programme_automataion/data/newsletters_html"
OUTPUT_CSV = "/workspaces/AM2_erp_programme_automataion/data/interim/extracted_newsletters.csv"

# Theme & subtheme bar colours
DARK_BLUE_BG = {c.upper() for c in [
    "#002060", "#1F3864", "#203864", "#00205B", "#042854", "#001F60"
]}
GREY_BG = {c.upper() for c in [
    "#DEEAF6", "#E7E6E6", "#D9D9D9", "#A5DAE9", "#D9E2F3", "#DAE3F3"
]}

CALLOUT_PREFIXES = re.compile(
    r'^(Full\s+(story|report|paper|article)|Read\s+more|Helpful\s+infographic|More|See\s+more|Watch|Recording)\b',
    re.I
)

# Footer/boilerplate boundary — everything from here down is the unsubscribe +
# feedback blurb, NOT newsletter items. Stop parsing when a block matches.
FOOTER_RE = re.compile(
    r'(You have indicated that you are|Do you find this newsletter useful|'
    r'Answer these short questions|To unsubscribe)',
    re.I
)

ANCHOR_ONLY_TOKENS = {
    "more", "read more", "report", "paper", "full report", "full story",
    "youtube", "tes", "gov.uk", "schoolsweek", "bera", "book now", "book on this link"
}

SAFE_HOSTS = {
    "eur01.safelinks.protection.outlook.com",
    "safelinks.protection.outlook.com",
    "nam01.safelinks.protection.outlook.com",
    "emea01.safelinks.protection.outlook.com",
}

TRACK_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "mkt_tok", "mc_cid", "mc_eid", "gclid", "fbclid", "igshid", "utm_name"
}

# -----------------------------
# URL HELPERS
# -----------------------------
def is_safelink(u: str) -> bool:
    try:
        return urlparse(u).netloc.lower() in SAFE_HOSTS
    except Exception:
        return False

def strip_tracking(u: str) -> str:
    try:
        p = urlparse(u)
        q = parse_qs(p.query, keep_blank_values=True)
        q2 = {k: v for k, v in q.items() if k.lower() not in TRACK_PARAMS}
        return urlunparse(p._replace(query=urlencode(q2, doseq=True)))
    except Exception:
        return u

def canonical_url(u: str) -> str:
    if not u:
        return ""
    u = u.strip()
    if is_safelink(u):
        try:
            q = parse_qs(urlparse(u).query)
            inner = q.get("url", []) or q.get("URL", [])
            if inner:
                u = inner[0]
        except Exception:
            pass
    u = strip_tracking(u)
    try:
        p = urlparse(u)
        path = p.path.rstrip("/") or "/"
        u = urlunparse((p.scheme.lower() or "https", p.netloc.lower(), path, "", p.query, ""))
    except Exception:
        pass
    return u

def slug_title(t: str) -> str:
    t = (t or "").strip().lower()
    t = re.sub(r'\s+', ' ', t)
    t = re.sub(r'\s*\(paid subscription required\)\s*$', '', t)
    return t

# -----------------------------
# COLOUR HELPERS
# -----------------------------
def _rgb_to_hex(raw: str):
    if not raw:
        return None
    m = re.search(r'rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)', raw, re.I)
    if not m:
        return None
    r, g, b = (int(m.group(i)) for i in (1, 2, 3))
    return f"#{r:02X}{g:02X}{b:02X}"

def _extract_bg_from_style(style: str):
    style = style or ""
    m = re.search(r'background(?:-color)?:\s*([^;]+)', style, re.I)
    if not m:
        return None
    raw = m.group(1).strip()
    return _rgb_to_hex(raw) or raw

def get_bg_color(tag):
    if not tag:
        return None
    c = _extract_bg_from_style(tag.get("style"))
    if not c:
        c = (tag.get("bgcolor") or "").strip()
    if not c and tag.name == "table":
        td = tag.find("td")
        if td:
            c = _extract_bg_from_style(td.get("style")) or (td.get("bgcolor") or "").strip()
    c = _rgb_to_hex(c) or c
    return c.upper() if c else None

# -----------------------------
# TEXT HELPERS
# -----------------------------
def first_text(el):
    return " ".join(el.get_text(" ", strip=True).split())

def prefer_original_href(a):
    return a.get("originalsrc") or a.get("href")

def find_newsletter_number_and_date(soup, filename=""):
    full_text = soup.get_text(" ", strip=True)
    num = None

    # Try to extract from text content
    m = re.search(r'\bERP?\s*Newsletter\s*[–—-]?\s*#?\s*(\d+)\b', full_text, re.I)
    if m:
        num = int(m.group(1))
    else:
        m2 = re.search(r'\bNewsletter\s*[–—-]?\s*#?\s*(\d+)\b', full_text, re.I)
        if m2:
            num = int(m2.group(1))

    # Fallback: extract from filename
    if num is None:
        fm = re.search(r'Newsletter\s+(\d+)', filename, re.I)
        if fm:
            num = int(fm.group(1))

    d = None
    md = re.search(r'\b(\d{1,2}\s+[A-Za-z]+\s+\d{4})\b', full_text)
    if md:
        d = md.group(1)

    return num, d

def _is_visually_bold(el):
    if el.find(["b", "strong"]):
        return True
    style = (el.get("style") or "").lower()
    if "font-weight" in style and ("bold" in style or re.search(r'font-weight\s*:\s*(6|7|8|9)\d{2}', style)):
        return True
    if el.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        return True
    return False

def _mostly_link_text(el):
    text = first_text(el)
    if not text:
        return False
    links = el.find_all("a")
    if not links:
        return False
    link_text = " ".join(a.get_text(" ", strip=True) for a in links)
    return len(link_text) >= 0.8 * len(text)

def _is_anchor_only(el):
    txt = first_text(el).strip().lower()
    only_a = (len(el.find_all()) == 1 and el.find("a") is not None)
    return (txt in ANCHOR_ONLY_TOKENS) or (only_a and txt in ANCHOR_ONLY_TOKENS)

def is_title_candidate(el):
    if not _is_visually_bold(el):
        return False
    text = first_text(el)
    if not text:
        return False
    if len(text.split()) > 28:
        return False
    if CALLOUT_PREFIXES.search(text):
        return False
    if _mostly_link_text(el):
        return False
    if _is_anchor_only(el):
        return False
    return True

def iter_blocks(soup):
    body = soup.body or soup
    queue = []

    def collect(node):
        for child in getattr(node, "children", []):
            name = getattr(child, "name", None)
            if name in ("table", "p", "h1", "h2", "h3", "h4", "h5", "h6"):
                queue.append(child)
            elif name in ("div", "section"):
                collect(child)

    collect(body)
    return queue

# -----------------------------
# FALLBACK PARSER
# -----------------------------
def fallback_parse_by_link(soup, newsletter_no, issue_date):
    rows = []
    blocks = iter_blocks(soup)

    current_theme = None
    current_subtheme = None
    title = None
    desc_parts = []
    link = None

    def flush_item():
        nonlocal title, desc_parts, link
        t = " ".join((title or "").split())
        if t and (desc_parts or link):
            rows.append({
                "id": str(uuid.uuid4()),
                "newsletter_number": newsletter_no,
                "issue_date": issue_date,
                "theme": current_theme,
                "subtheme": current_subtheme,
                "title": t,
                "description": " ".join(" ".join(desc_parts).split()) or None,
                "link": canonical_url(link) if link else ""
            })
        title, desc_parts, link = None, [], None

    for el in blocks:
        if FOOTER_RE.search(first_text(el)):
            break
        if el.name == "table":
            bg = get_bg_color(el)
            if bg and (bg in DARK_BLUE_BG or bg in GREY_BG):
                flush_item()
            if bg and bg in DARK_BLUE_BG:
                current_theme = first_text(el)
                current_subtheme = None
                continue
            elif bg and bg in GREY_BG:
                current_subtheme = first_text(el)
                continue

        if el.name == "p" and (current_theme or current_subtheme):
            txt = first_text(el)
            a = el.find("a")
            href = canonical_url(prefer_original_href(a) or "") if a else ""

            if not title and txt and not CALLOUT_PREFIXES.search(txt) and not _is_anchor_only(el):
                title = txt
            elif txt and not CALLOUT_PREFIXES.search(txt):
                desc_parts.append(txt)

            if href and not link:
                link = href
                flush_item()

    flush_item()
    return rows

# -----------------------------
# PLAINTEXT FALLBACK (for PDF-export newsletters with no tables, e.g. #90, #91, #103, #104)
# -----------------------------
# Known theme headings used in plaintext newsletters
KNOWN_THEMES = [
    "Updates from the Programme",
    "Teacher recruitment, retention & development",
    "EdTech",
    "Ed Tech",
    "Political environment and key organisations",
    "Four Nations",
    "Research – Practice – Policy",
    "Research - Practice - Policy",
    "What matters in education?",
    "Calls for evidence",
    "DfE",
    "Curriculum and Assessment",
    "Events",
    "Ofsted",
    "SEND",
    "Early Years",
    "School funding",
    "Wellbeing",
]

LINK_TOKENS = {
    "more", "book now", "register", "sign up", "here",
    "sign up here", "book on this link",
}

def _normalise_theme(text):
    """Match text against known themes (case-insensitive, whitespace-normalised)."""
    t = " ".join(text.split()).strip()
    for theme in KNOWN_THEMES:
        if t.lower() == theme.lower():
            return theme
        # Handle broken characters like "T e acher" -> "Teacher"
        collapsed = re.sub(r'(?<=\w)\s+(?=\w)', '', t)
        theme_collapsed = re.sub(r'(?<=\w)\s+(?=\w)', '', theme)
        if collapsed.lower() == theme_collapsed.lower():
            return theme
    return None

def plaintext_parse(soup, newsletter_no, issue_date):
    """Parse newsletters that are plain divs/spans with no tables (PDF exports)."""
    # Get all text-bearing divs in order
    divs = soup.find_all("div")
    lines = []
    for d in divs:
        text = " ".join(d.get_text(" ", strip=True).split())
        a = d.find("a")
        href = ""
        if a:
            href = prefer_original_href(a) or ""
        if text:
            lines.append((text, href))

    rows = []
    current_theme = None
    title = None
    desc_parts = []
    link = ""

    # Skip email header lines (Subject, Date, From, To, CC, Attachments, etc.)
    start_idx = 0
    header_pattern = re.compile(r'^(Subject|Date|From|To|CC|Attachments|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b', re.I)
    for i, (text, _) in enumerate(lines):
        if re.match(r'^ERP Newsletter\s*#?\d+', text, re.I):
            start_idx = i + 1
            break
        # Also skip past date line right after newsletter title
    # Skip the date line too
    if start_idx < len(lines):
        date_match = re.match(r'^\d{1,2}\s+\w+\s+\d{4}$', lines[start_idx][0])
        if date_match:
            start_idx += 1

    def flush_item():
        nonlocal title, desc_parts, link
        t = " ".join((title or "").split())
        if t:
            rows.append({
                "id": str(uuid.uuid4()),
                "newsletter_number": newsletter_no,
                "issue_date": issue_date,
                "theme": current_theme,
                "subtheme": None,
                "title": t,
                "description": " ".join(" ".join(desc_parts).split()) or None,
                "link": canonical_url(link) if link else ""
            })
        title, desc_parts, link = None, [], ""

    skip_tokens = {"1 of 2", "2 of 2", "1 of 3", "2 of 3", "3 of 3"}

    for text, href in lines[start_idx:]:
        # Skip pagination markers
        if text.strip() in skip_tokens:
            continue

        # Skip unsubscribe/footer
        if "unsubscribe" in text.lower() or "you have indicated" in text.lower():
            break

        # Check if this is a theme heading
        theme = _normalise_theme(text)
        if theme:
            flush_item()
            current_theme = theme
            continue

        # Check if this is a link token ("More", "Book now", etc.)
        if text.strip().lower() in LINK_TOKENS:
            if href:
                link = href
            flush_item()
            continue
        # "Sign up here" with link inside
        if href and text.strip().lower().startswith("sign up"):
            link = href
            flush_item()
            continue

        if not current_theme:
            continue

        # First text after theme (or after previous item flush) is the title
        if not title:
            title = text
            if href:
                link = href
        else:
            desc_parts.append(text)
            if href and not link:
                link = href

    flush_item()
    return rows

# -----------------------------
# MAIN PARSER
# -----------------------------
def parse_file(path):
    filename = os.path.basename(path)
    html = open(path, "r", encoding="utf-8", errors="ignore").read()
    soup = BeautifulSoup(html, "html.parser")

    newsletter_no, issue_date = find_newsletter_number_and_date(soup, filename)
    current_theme = None
    current_subtheme = None

    rows = []
    blocks = iter_blocks(soup)
    i = 0
    while i < len(blocks):
        el = blocks[i]

        # Stop at the unsubscribe/feedback footer — nothing below is an item.
        if FOOTER_RE.search(first_text(el)):
            break

        if el.name == "table":
            bg = get_bg_color(el)
            if bg and bg in DARK_BLUE_BG:
                current_theme = first_text(el)
                current_subtheme = None
                i += 1
                continue
            elif bg and bg in GREY_BG:
                current_subtheme = first_text(el)
                i += 1
                continue

        if el.name in ("p", "h1", "h2", "h3", "h4", "h5", "h6") and is_title_candidate(el) and (current_theme or current_subtheme):
            title = first_text(el)

            link = ""
            a_in_title = el.find("a")
            if a_in_title:
                href = (prefer_original_href(a_in_title) or "").strip()
                if href:
                    link = canonical_url(href)

            desc_parts = []
            j = i + 1
            while j < len(blocks):
                nxt = blocks[j]

                if nxt.name == "table":
                    bg = get_bg_color(nxt)
                    if bg and (bg in DARK_BLUE_BG or bg in GREY_BG):
                        break

                if nxt.name in ("p", "h1", "h2", "h3", "h4", "h5", "h6") and is_title_candidate(nxt):
                    break

                if nxt.name == "p":
                    txt = first_text(nxt)
                    if txt and not CALLOUT_PREFIXES.search(txt) and not _is_anchor_only(nxt):
                        desc_parts.append(txt)
                    if not link:
                        a = nxt.find("a")
                        if a:
                            href = (prefer_original_href(a) or "").strip()
                            if href:
                                link = canonical_url(href)
                j += 1

            description = " ".join(desc_parts).strip() or None
            rows.append({
                "id": str(uuid.uuid4()),
                "newsletter_number": newsletter_no,
                "issue_date": issue_date,
                "theme": current_theme,
                "subtheme": current_subtheme,
                "title": title,
                "description": description,
                "link": link
            })
            i = j
            continue

        i += 1

    extra = fallback_parse_by_link(soup, newsletter_no, issue_date)

    # If both parsers found nothing, try the plaintext parser (PDF-export format)
    if not rows and not extra:
        return plaintext_parse(soup, newsletter_no, issue_date)

    # Merge & dedupe
    def score_row(r):
        link = r.get("link") or ""
        desc = r.get("description") or ""
        return (0 if is_safelink(link) else 1, 1 if link else 0, len(desc))

    def row_key(r):
        t = slug_title(r.get("title"))
        l = canonical_url(r.get("link") or "")
        if l:
            return ("t+l", t, l)
        return ("t+theme", t, (r.get("theme") or "").strip().lower())

    bucket = {}
    for r in rows + extra:
        r["title"] = (r.get("title") or "").strip()
        r["link"] = canonical_url(r.get("link") or "")
        k = row_key(r)
        if k not in bucket or score_row(r) > score_row(bucket[k]):
            if k in bucket:
                existing = bucket[k]
                if not existing.get("description"):
                    existing["description"] = r.get("description")
                for fld in ("id", "newsletter_number", "issue_date", "theme", "subtheme", "title", "link"):
                    existing[fld] = r.get(fld, existing.get(fld))
            else:
                bucket[k] = r

    return list(bucket.values())

# -----------------------------
# DRIVER
# -----------------------------
def main():
    all_rows = []
    files = sorted(glob(os.path.join(FOLDER, "*.html")))
    if not files:
        print(f"No HTML files found in {FOLDER}")
        return

    print(f"Found {len(files)} files...")
    for fp in files:
        try:
            rows = parse_file(fp)
            if not rows:
                print(f"  WARNING: No rows parsed from {os.path.basename(fp)}")
            else:
                print(f"  OK: {os.path.basename(fp)} -> {len(rows)} rows")
            all_rows.extend(rows)
        except Exception as e:
            print(f"  ERROR: {os.path.basename(fp)}: {e}")

    df = pd.DataFrame(all_rows, columns=[
        "id", "newsletter_number", "issue_date",
        "theme", "subtheme", "title", "description", "link"
    ])
    df = df.sort_values("newsletter_number", na_position="last").reset_index(drop=True)

    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nDone. Wrote {len(df)} rows to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
