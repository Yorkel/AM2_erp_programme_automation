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
BASE = "https://www.gtcs.org.uk"
START_URL = "https://www.gtcs.org.uk/news"

_DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "data" / "test" / "scotland_gtcs.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

_DATE_RE = re.compile(r"(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})")


# ----------------------------------------------------------
# Extract articles (link + date) from listing page
# ----------------------------------------------------------
def _extract_articles_from_listing(soup):
    """Extract article URLs and dates from the listing page."""
    articles = []
    seen_hrefs = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if "/news/news-and-updates/" not in href:
            continue
        if not href.startswith("http"):
            href = BASE + href
        if href in seen_hrefs:
            continue
        seen_hrefs.add(href)

        # Find date in parent/grandparent text
        pub_date = None
        for ancestor in [a.parent, a.parent.parent if a.parent else None]:
            if ancestor is None:
                continue
            text = ancestor.get_text(" ", strip=True)
            m = _DATE_RE.search(text)
            if m:
                try:
                    pub_date = datetime.strptime(m.group(1), "%d %B %Y").date()
                except ValueError:
                    pass
                break

        articles.append({"url": href, "date": pub_date})

    return articles


# ----------------------------------------------------------
# Scrape a single article page for title + text
# ----------------------------------------------------------
def _scrape_article(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
    except requests.RequestException as e:
        print(f"    Failed: {url} — {e}")
        return "", ""

    if r.status_code != 200:
        print(f"    HTTP {r.status_code}: {url}")
        return "", ""

    soup = BeautifulSoup(r.text, "lxml")

    # Title
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else ""

    # Text — paragraphs inside <main>
    main = soup.find("main")
    if main:
        for t in main.find_all(["script", "style", "figure", "aside", "nav", "footer", "header"]):
            t.decompose()
        text = "\n".join(
            p.get_text(" ", strip=True)
            for p in main.find_all("p")
            if p.get_text(strip=True)
        )
    else:
        text = ""

    return title, text


# ----------------------------------------------------------
# Check pagination — find next page link
# ----------------------------------------------------------
def _find_next_page(soup):
    # Look for pagination links
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True).lower()
        if text in ["next", "next page", "›", "»", "next ›"]:
            href = a["href"].strip()
            if not href.startswith("http"):
                href = BASE + href
            return href

    # Also check for numbered pages
    current_page = soup.find("span", class_=lambda c: c and "current" in c.lower() if c else False)
    if current_page:
        next_a = current_page.find_next("a", href=True)
        if next_a:
            href = next_a["href"].strip()
            if not href.startswith("http"):
                href = BASE + href
            return href

    return None


# ----------------------------------------------------------
# Main scraper
# ----------------------------------------------------------
def scrape_gtcs(since_date: "date | None" = None, until_date: "date | None" = None, output_path: "str | None" = None, append: bool = False) -> list[dict]:
    """Scrape GTC Scotland news via HTML pagination.

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
    url = START_URL
    page = 1
    max_pages = 20

    print("Starting GTCS scrape...")

    while page <= max_pages:
        if page == 1:
            url = START_URL
        else:
            url = f"{START_URL}?f308a811_page={page}"

        print(f"  Page {page}: {url}")

        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
        except requests.RequestException as e:
            print(f"    Request failed: {e}")
            break

        if r.status_code != 200:
            print(f"    HTTP {r.status_code} — stopping.")
            break

        soup = BeautifulSoup(r.text, "lxml")
        listing = _extract_articles_from_listing(soup)
        print(f"  Found {len(listing)} article links")

        if not listing:
            print("  No links found — stopping.")
            break

        new_this_page = 0
        stop_early = False
        for item in listing:
            if item["url"] in seen:
                continue
            seen.add(item["url"])

            pub_date = item["date"]

            # Date filtering
            if pub_date:
                if until_date and pub_date > until_date:
                    continue
                if since_date and pub_date < since_date:
                    stop_early = True
                    break

            # Fetch article text
            title, text = _scrape_article(item["url"])

            if not text.strip():
                print(f"    No text: {item['url'][:60]}")
                continue

            all_articles.append({
                "url": item["url"],
                "title": title,
                "date": pub_date.strftime("%Y-%m-%d") if pub_date else "",
                "text": text,
            })
            new_this_page += 1
            print(f"    {pub_date} | {title[:60]}")
            time.sleep(1)

        if stop_early:
            print(f"  Reached since_date cutoff — stopping.")
            break

        if new_this_page == 0:
            print(f"  No new articles — stopping.")
            break

        print(f"  {len(all_articles)} articles so far")
        page += 1
        time.sleep(1)

    print(f"\n  Done. {len(all_articles)} articles.")
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
    scrape_gtcs(output_path=_DEFAULT_OUTPUT)
