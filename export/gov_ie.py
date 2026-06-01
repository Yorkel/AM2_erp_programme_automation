import requests
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path
import time
from datetime import datetime

# ----------------------------------------------------------
# Config
# ----------------------------------------------------------
BASE = "https://www.gov.ie"

SEARCH_URLS = [
    "https://www.gov.ie/en/search/?category=Press+release&organisation=Department+of+Education+and+Youth",
    "https://www.gov.ie/en/search/?category=Publication&organisation=Department+of+Education+and+Youth",
]

_DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "data" / "test" / "ireland_gov_ie_full.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


# ----------------------------------------------------------
# Scrape a single article page for full text
# ----------------------------------------------------------
def scrape_article(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
    except requests.RequestException as e:
        print(f"    Failed: {e}")
        return ""

    soup = BeautifulSoup(r.text, "lxml")

    content = soup.find("main") or soup.find("article")
    if content:
        for t in content.find_all(["script", "style", "figure", "aside", "nav"]):
            t.decompose()
        text = "\n".join(
            p.get_text(" ", strip=True)
            for p in content.find_all("p")
            if p.get_text(strip=True)
        )
    else:
        text = ""

    # Strip gov.ie boilerplate
    text = text.replace("From: Department of Education and Youth", "").strip()
    text = text.replace("(PDF)", "").strip()

    return text


# ----------------------------------------------------------
# Main scraper
# ----------------------------------------------------------
def scrape_gov_ie(since_date: "date | None" = None, until_date: "date | None" = None, output_path: "str | None" = None, append: bool = False) -> list[dict]:
    """Scrape Irish Dept of Education press releases and publications via search page HTML.

    Args:
        since_date: Earliest publication date to include.
        until_date: Latest publication date to include.
        output_path: Path to save CSV output.
        append: If True, append to existing CSV instead of overwriting.

    Returns:
        List of dicts with keys: url, title, date, text
    """
    all_articles = []
    seen_urls = set()

    print("Starting Irish Government (Dept of Education) scrape...")

    for search_url in SEARCH_URLS:
        category = "Press releases" if "Press+release" in search_url else "Publications"
        print(f"\n  --- {category} ---")

        page = 1
        new_on_page = 0

        while True:
            url = f"{search_url}&page={page}" if page > 1 else search_url
            print(f"  Page {page}: {url}")

            try:
                r = requests.get(url, headers=HEADERS, timeout=30)
            except requests.RequestException as e:
                print(f"  Request failed: {e}")
                break

            if r.status_code != 200:
                print(f"  HTTP {r.status_code} — stopping.")
                break

            soup = BeautifulSoup(r.text, "lxml")
            cards = soup.find_all("div", class_="gi-card")

            if not cards:
                print("  No more results.")
                break

            stop = False
            new_on_page = 0

            for card in cards:
                date_str = card.get("data-createdat", "")
                title = card.get("data-title", "")
                link_tag = card.find("a", href=True)
                href = link_tag["href"] if link_tag else ""
                if href and not href.startswith("http"):
                    href = BASE + href

                # Skip duplicates
                if href in seen_urls:
                    continue
                seen_urls.add(href)

                # Parse date from data-createdat attribute
                pub_date = None
                if date_str:
                    try:
                        pub_date = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
                    except ValueError:
                        pass

                # Date filters
                if pub_date and until_date and pub_date > until_date:
                    continue  # too recent, skip
                if pub_date and since_date and pub_date < since_date:
                    stop = True
                    break

                if href and title:
                    new_on_page += 1
                    print(f"    {date_str} | {title[:60]}")
                    text = scrape_article(href)
                    all_articles.append({
                        "url": href,
                        "title": title,
                        "date": date_str,
                        "text": text,
                    })
                    time.sleep(0.5)

            print(f"  {len(all_articles)} articles so far")

            if stop:
                print(f"  Reached since_date cutoff — stopping {category}.")
                break

            # If no new articles on this page, stop
            if new_on_page == 0:
                print(f"  No new articles on page — stopping {category}.")
                break

            page += 1
            time.sleep(1)

        old_streak = 0  # reset for next category

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
    scrape_gov_ie(output_path=_DEFAULT_OUTPUT)
