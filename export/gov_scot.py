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
BASE = "https://www.gov.scot"

# Education-filtered search pages (same approach as gov.ie)
SEARCH_URLS = [
    "https://www.gov.scot/news/?cat=filter&topic=education&sort=date",
    "https://www.gov.scot/publications/?cat=filter&topic=education&sort=date",
]

_DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "data" / "test" / "scotland_gov_scot.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Date regex for "17 March 2026" etc.
_DATE_RE = re.compile(r"(\d{1,2}\s+\w+\s+\d{4})")


# ----------------------------------------------------------
# Get results from search listing pages
# ----------------------------------------------------------
def _get_search_results(base_url, since_date=None, until_date=None):
    """Paginate through a gov.scot search page and return list of {url, title, date}."""
    results = []
    seen = set()
    page = 1

    while True:
        url = f"{base_url}&page={page}" if page > 1 else base_url
        print(f"  Page {page}: {url}")

        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
        except requests.RequestException as e:
            print(f"    Request failed: {e}")
            break

        if r.status_code != 200:
            print(f"    HTTP {r.status_code} — stopping")
            break

        soup = BeautifulSoup(r.text, "lxml")
        items = soup.find_all("li", class_="ds_search-result")

        if not items:
            print(f"  No results on page — stopping.")
            break

        new_this_page = 0
        skipped_future = 0
        stop_early = False

        for item in items:
            # Title + URL
            link = item.find("a", class_="ds_search-result__link")
            if not link:
                continue
            href = link.get("href", "")
            if not href.startswith("http"):
                href = BASE + href
            if href in seen:
                continue
            seen.add(href)

            title = link.get_text(strip=True)

            # Date from metadata
            pub_date = None
            for dd in item.find_all("dd"):
                text = dd.get_text(strip=True)
                m = _DATE_RE.search(text)
                if m:
                    try:
                        pub_date = datetime.strptime(m.group(1), "%d %B %Y").date()
                    except ValueError:
                        continue

            # Date filtering (must come BEFORE content filter so skipped_future counts correctly)
            if pub_date:
                if until_date and pub_date > until_date:
                    skipped_future += 1
                    continue  # skip future articles but keep paginating
                if since_date and pub_date < since_date:
                    stop_early = True
                    break  # results are newest-first, so stop

            # Skip administrative publications (FOIs, minutes, impact assessments)
            title_lower = title.lower()
            SKIP_PATTERNS = [
                "foi release", "foi review", "foi request",
                "minutes:", "minutes -", "meeting minutes",
                "equality impact assessment", "impact assessment",
                "child rights and wellbeing impact",
                "terms of reference",
            ]
            if any(pat in title_lower for pat in SKIP_PATTERNS):
                continue

            results.append({"url": href, "title": title, "date": pub_date})
            new_this_page += 1
            print(f"    {pub_date} | {title[:60]}")

        print(f"  {len(results)} articles so far")

        if stop_early:
            print(f"  Reached since_date cutoff — stopping.")
            break

        if new_this_page == 0 and skipped_future == 0:
            print(f"  No results on page — stopping.")
            break

        page += 1
        time.sleep(1)

    return results


# ----------------------------------------------------------
# Scrape a single article page
# ----------------------------------------------------------
def _scrape_article(url):
    """Fetch full text from a gov.scot article page."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
    except requests.RequestException:
        return ""

    if r.status_code != 200:
        return ""

    soup = BeautifulSoup(r.text, "lxml")

    # Main content — gov.scot uses <main> tag
    content = soup.find("main") or soup.find("div", class_="body-content") or soup.find("article")
    if content:
        for t in content.find_all(["script", "style", "figure", "aside", "nav"]):
            t.decompose()
        text = "\n".join(
            p.get_text(" ", strip=True)
            for p in content.find_all("p")
            if p.get_text(strip=True)
        )
        return text

    return ""


# ----------------------------------------------------------
# Main scraper
# ----------------------------------------------------------
def scrape_gov_scot(since_date: "date | None" = None, until_date: "date | None" = None, output_path: "str | None" = None, append: bool = False) -> list[dict]:
    """Scrape Scottish Government education news and publications via search page HTML.

    Args:
        since_date: Earliest publication date to include.
        until_date: Latest publication date to include.
        output_path: Path to save CSV output.
        append: If True, append to existing CSV instead of overwriting.

    Returns:
        List of dicts with keys: url, title, date, text
    """
    all_articles = []

    print("Starting Scottish Government scrape (education-filtered search)...")

    for search_url in SEARCH_URLS:
        label = "News" if "/news/" in search_url else "Publications"
        print(f"\n  --- {label} ---")
        results = _get_search_results(search_url, since_date=since_date, until_date=until_date)

        for item in results:
            print(f"    Fetching: {item['url'][:70]}")
            text = _scrape_article(item["url"])
            all_articles.append({
                "url": item["url"],
                "title": item["title"],
                "date": item["date"].strftime("%Y-%m-%d") if item["date"] else "",
                "text": text,
            })
            time.sleep(0.5)

    print(f"\n  Done. {len(all_articles)} articles total.")
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
    scrape_gov_scot(output_path=_DEFAULT_OUTPUT)
