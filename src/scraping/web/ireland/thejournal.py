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
BASE = "https://www.thejournal.ie"
START_URL = "https://www.thejournal.ie/education/news/"

_DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "data" / "test" / "ireland_thejournal_full.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Date regex for "7 Aug 2025", "26 Feb 2026" etc.
_DATE_RE = re.compile(
    r"\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}",
    re.IGNORECASE,
)


# ----------------------------------------------------------
# Extract article links from listing page
# ----------------------------------------------------------
def _extract_links(html):
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href.startswith("http"):
            href = BASE + href
        # TheJournal article URLs contain a numeric ID and month+year
        # e.g. /baptism-problems-relationship-6975786-Mar2026/
        if re.search(r"-\d{5,}-\w{3}\d{4}", href) and href not in links:
            links.append(href)
    return links


# ----------------------------------------------------------
# Scrape a single article
# ----------------------------------------------------------
def _scrape_article(url, since_date=None, until_date=None):
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
    except requests.RequestException as e:
        print(f"  Failed to fetch {url}: {e}")
        return None

    if r.status_code == 429:
        print(f"    Rate limited — waiting 30s and retrying: {url}")
        time.sleep(30)
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
        except requests.RequestException:
            return None
    if r.status_code != 200:
        print(f"  HTTP {r.status_code} for {url}")
        return None

    soup = BeautifulSoup(r.text, "html.parser")

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # Date parsing — try <time> tag first, then regex on page text
    pub_date = None
    time_tag = soup.find("time")
    if time_tag:
        dt = time_tag.get("datetime", "")
        if dt:
            try:
                pub_date = datetime.fromisoformat(dt.replace("Z", "+00:00")).date()
            except ValueError:
                pass

    if not pub_date:
        page_text = soup.get_text(" ", strip=True)
        m = _DATE_RE.search(page_text)
        if m:
            try:
                pub_date = datetime.strptime(m.group(), "%d %b %Y").date()
            except ValueError:
                pass

    if pub_date:
        if since_date and pub_date < since_date:
            return "OLD"
        if until_date and pub_date > until_date:
            return "SKIP"

    # Main content
    content = soup.find("article") or soup.find("div", class_=lambda c: c and "article" in c.lower() if c else False)
    if content:
        for t in content.find_all(["script", "style", "figure", "aside", "nav", "footer"]):
            t.decompose()
        text = "\n".join(
            p.get_text(" ", strip=True)
            for p in content.find_all("p")
            if p.get_text(strip=True)
        )
    else:
        text = ""

    return {
        "url": url,
        "title": title,
        "date": pub_date.strftime("%Y-%m-%d") if pub_date else "",
        "text": text,
    }


# ----------------------------------------------------------
# Main scraper
# ----------------------------------------------------------
def scrape_thejournal(since_date: "date | None" = None, until_date: "date | None" = None, output_path: "str | None" = None, append: bool = False) -> list[dict]:
    """Scrape TheJournal.ie education news via HTML pagination.

    Args:
        since_date: Earliest publication date to include.
        until_date: Latest publication date to include.
        output_path: Path to save CSV output.
        append: If True, append to existing CSV instead of overwriting.

    Returns:
        List of dicts with keys: url, title, date, text
    """
    all_articles = []
    seen = set()
    max_pages = 100

    print("Starting TheJournal.ie Education scrape...")

    for page in range(1, max_pages + 1):
        url = START_URL if page == 1 else f"{START_URL}page/{page}/"
        print(f"  Page {page}: {url}")

        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
        except requests.RequestException as e:
            print(f"  Request failed: {e}")
            break

        if r.status_code == 429:
            print(f"  Rate limited — waiting 30s and retrying page {page}")
            time.sleep(30)
            try:
                r = requests.get(url, headers=HEADERS, timeout=30)
            except requests.RequestException:
                break
        if r.status_code != 200:
            print(f"  HTTP {r.status_code} — stopping.")
            break

        links = _extract_links(r.text)
        print(f"  Found {len(links)} article links")

        if not links:
            print("  No links — end of pages.")
            break

        old_count = 0
        stop = False
        for link in links:
            if link in seen:
                continue
            seen.add(link)
            print(f"    {link}")

            result = _scrape_article(link, since_date=since_date, until_date=until_date)

            if result == "OLD":
                old_count += 1
                if old_count >= 5:
                    print("  5 consecutive old articles — stopping.")
                    stop = True
                    break
                continue
            if result == "SKIP":
                old_count = 0
                continue
            if result:
                old_count = 0
                all_articles.append(result)

            time.sleep(5)

        if stop:
            break

        print(f"  {len(all_articles)} articles so far")
        time.sleep(5)

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
    scrape_thejournal(output_path=_DEFAULT_OUTPUT)
