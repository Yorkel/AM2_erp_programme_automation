import requests
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path
import time
from datetime import datetime

# ----------------------------------------------------------
# Config
# ----------------------------------------------------------
BASE = "https://childreninscotland.org.uk"
START_URL = "https://childreninscotland.org.uk/news/"

_DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "data" / "test" / "scotland_children_in_scotland.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


# ----------------------------------------------------------
# Extract article links from listing page
# ----------------------------------------------------------
def _extract_links(soup):
    links = []
    for a in soup.select("a.card--news_article"):
        href = a.get("href", "")
        if href and href not in links:
            links.append(href)
    return links


# ----------------------------------------------------------
# Scrape a single article page
# ----------------------------------------------------------
def _scrape_article(url, since_date=None, until_date=None):
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
    except requests.RequestException as e:
        print(f"    Failed: {url} — {e}")
        return None

    if r.status_code != 200:
        print(f"    HTTP {r.status_code}: {url}")
        return None

    soup = BeautifulSoup(r.text, "lxml")

    # Title
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else ""

    # Date — div.simple-hero__body-meta contains "12 Mar, 2026"
    pub_date = None
    date_el = soup.find("div", class_="simple-hero__body-meta")
    if date_el:
        date_text = date_el.get_text(strip=True)
        for fmt in ["%d %b, %Y", "%d %B, %Y", "%d %b %Y", "%d %B %Y"]:
            try:
                pub_date = datetime.strptime(date_text, fmt).date()
                break
            except ValueError:
                continue

    # Date filtering
    if pub_date:
        if since_date and pub_date < since_date:
            return "OLD"
        if until_date and pub_date > until_date:
            return "SKIP"

    # Text — paragraphs inside <main>
    main = soup.find("main")
    if main:
        for t in main.find_all(["script", "style", "figure", "aside", "nav", "footer"]):
            t.decompose()
        text = "\n".join(
            p.get_text(" ", strip=True)
            for p in main.find_all("p")
            if p.get_text(strip=True)
        )
    else:
        text = ""

    if not text.strip():
        return None

    return {
        "url": url,
        "title": title,
        "date": pub_date.strftime("%Y-%m-%d") if pub_date else "",
        "text": text,
    }


# ----------------------------------------------------------
# Main scraper
# ----------------------------------------------------------
def scrape_children_in_scotland(since_date: "date | None" = None, until_date: "date | None" = None, output_path: "str | None" = None, append: bool = False) -> list[dict]:
    """Scrape Children in Scotland news via HTML pagination.

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
    page = 1
    max_pages = 50
    consecutive_old = 0

    print("Starting Children in Scotland scrape...")

    while page <= max_pages:
        url = START_URL if page == 1 else f"{START_URL}?paged={page}"
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
        links = _extract_links(soup)

        if not links:
            print(f"  No links found — stopping.")
            break

        new_links = [l for l in links if l not in seen]
        if not new_links:
            print(f"  No new links — stopping.")
            break

        for link in new_links:
            seen.add(link)
            result = _scrape_article(link, since_date=since_date, until_date=until_date)

            if result == "OLD":
                consecutive_old += 1
                if consecutive_old >= 3:
                    print(f"  {consecutive_old} consecutive old articles — stopping.")
                    break
                continue
            elif result == "SKIP":
                consecutive_old = 0
                continue
            elif result is None:
                consecutive_old = 0
                continue

            consecutive_old = 0
            all_articles.append(result)
            print(f"    {result['date']} | {result['title'][:60]}")

            time.sleep(1)

        if consecutive_old >= 3:
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
    scrape_children_in_scotland(output_path=_DEFAULT_OUTPUT)
