import requests
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path
import time
import re
from datetime import datetime

# ----------------------------------------------------------
# Config
# ----------------------------------------------------------
BASE = "https://www.esri.ie"

# Pre-filtered URLs — ESRI covers all policy areas, these narrow to education
NEWS_URL = "https://www.esri.ie/news?keywords=education"                          # 26 pages
PUBS_URL = "https://www.esri.ie/publications/browse?research_areas[]=63"          # 47 pages (education = area 63)

_DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "data" / "test" / "ireland_esri_full.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Regex for dates like "February 26, 2026" or "26 February 2026"
_DATE_RE = re.compile(
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2},?\s+\d{4}"
    r"|"
    r"\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{4}",
    re.IGNORECASE,
)


# ----------------------------------------------------------
# Helpers
# ----------------------------------------------------------
def _parse_date(text):
    """Try to parse a date string in common formats."""
    cleaned = text.replace(",", "").strip()
    for fmt in ["%B %d %Y", "%d %B %Y", "%Y-%m-%d"]:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def _extract_links(html, prefix):
    """Extract article/publication links from a listing page."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href.startswith("http"):
            href = BASE + href
        path = href.replace(BASE, "")
        # Match individual items under the given prefix (e.g. /news/ or /publications/)
        if path.startswith(prefix) and len(path) > len(prefix) and "?" not in href:
            if href not in links:
                links.append(href)
    return links


def _scrape_article(url, since_date=None, until_date=None):
    """Scrape a single news article or publication page."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
    except requests.RequestException as e:
        print(f"  Failed to fetch {url}: {e}")
        return None

    soup = BeautifulSoup(r.text, "html.parser")

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # Date parsing — ESRI uses plain text dates, no <time> tags
    pub_date = None
    page_text = soup.get_text(" ", strip=True)
    date_match = _DATE_RE.search(page_text)
    if date_match:
        pub_date = _parse_date(date_match.group())

    if pub_date:
        if since_date and pub_date < since_date:
            return "STOP"
        if until_date and pub_date > until_date:
            return "SKIP"

    # Main content — get all <p> tags, strip footer boilerplate
    FOOTER_MARKERS = [
        "The Economic and Social Research Institute Whitaker Square",
        "ESRI Accessibility Statement",
        "ESRI Governance Policies",
        "Web Design and Development by Annertech",
    ]
    paragraphs = soup.find_all("p")
    lines = []
    for p in paragraphs:
        t = p.get_text(" ", strip=True)
        if not t:
            continue
        if any(marker in t for marker in FOOTER_MARKERS):
            break  # stop at footer
        lines.append(t)
    text = "\n".join(lines)

    return {
        "url": url,
        "title": title,
        "date": pub_date.strftime("%Y-%m-%d") if pub_date else "",
        "text": text,
    }


def _scrape_section(base_url, link_prefix, section_name,
                    since_date=None, until_date=None, max_pages=60):
    """Scrape one section (news or publications) page by page."""
    all_articles = []
    seen = set()

    print(f"\n  === {section_name} ===")

    for page in range(max_pages):
        url = base_url if page == 0 else f"{base_url}&page={page}" if "?" in base_url else f"{base_url}?page={page}"
        print(f"  Page {page}: {url}")

        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
        except requests.RequestException as e:
            print(f"  Request failed: {e}")
            break

        if r.status_code != 200:
            print(f"  HTTP {r.status_code} — stopping section.")
            break

        links = _extract_links(r.text, link_prefix)
        print(f"  Found {len(links)} links")

        if not links:
            print("  No links — end of section.")
            break

        stop = False
        for link in links:
            if link in seen:
                continue
            seen.add(link)
            print(f"    {link}")

            result = _scrape_article(link, since_date=since_date, until_date=until_date)

            if result == "STOP":
                print("  Reached since_date cutoff — stopping.")
                stop = True
                break
            if result == "SKIP":
                continue
            if result:
                all_articles.append(result)

            time.sleep(1)

        if stop:
            break

        print(f"  {len(all_articles)} education articles so far")
        page += 1
        time.sleep(1)

    return all_articles


# ----------------------------------------------------------
# Main scraper
# ----------------------------------------------------------
def scrape_esri(since_date: "date | None" = None, until_date: "date | None" = None, output_path: "str | None" = None, append: bool = False) -> list[dict]:
    """Scrape ESRI education-filtered news and publications via HTML pagination.

    Args:
        since_date: Earliest publication date to include.
        until_date: Latest publication date to include.
        output_path: Path to save CSV output.
        append: If True, append to existing CSV instead of overwriting.

    Returns:
        List of dicts with keys: url, title, date, text
    """
    print("Starting ESRI scrape (education-filtered news + publications)...")

    # Scrape education news
    news = _scrape_section(
        NEWS_URL, "/news/", "ESRI News (education keyword)",
        since_date=since_date, until_date=until_date, max_pages=30,
    )

    # Scrape education publications
    pubs = _scrape_section(
        PUBS_URL, "/publications/", "ESRI Publications (education research area)",
        since_date=since_date, until_date=until_date, max_pages=50,
    )

    all_articles = news + pubs
    print(f"\nTotal: {len(news)} news + {len(pubs)} publications = {len(all_articles)} articles")

    _save(all_articles, output_path, append)
    return all_articles


def _save(articles, output_path, append):
    if output_path is None:
        return
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(articles)
    mode = "a" if append else "w"
    header = not (append and out.exists())
    df.to_csv(out, mode=mode, header=header, index=False)
    print(f"  Saved {len(df)} articles -> {out}")


if __name__ == "__main__":
    scrape_esri(output_path=_DEFAULT_OUTPUT)
