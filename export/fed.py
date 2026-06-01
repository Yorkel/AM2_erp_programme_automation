import requests
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path
import time
from datetime import datetime

BASE_URL = "https://fed.education/news-resources/"
PAGE_URL = "https://fed.education/news-resources/page/{}/"

_DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "data" / "training" / "england" / "fed.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; FEDScraper/1.0)"
}


# ---------------------------------------------------------
# Extract article links from listing page
# ---------------------------------------------------------
def extract_links(html):
    soup = BeautifulSoup(html, "html.parser")
    links = []

    for a in soup.select("a.elementor-post__thumbnail__link[href]"):
        links.append(a["href"])

    for a in soup.select("h3.elementor-post__title a[href]"):
        links.append(a["href"])

    return list(dict.fromkeys(links))


# ---------------------------------------------------------
# Extract full article
# ---------------------------------------------------------
def scrape_article(url, since_date=None, until_date=None):
    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")

    # TITLE
    title_tag = soup.select_one("h1.elementor-heading-title")
    if not title_tag:
        return None
    title = title_tag.get_text(strip=True)

    # DATE
    date_tag = soup.select_one("time")
    if not date_tag:
        return None

    try:
        pub_date = datetime.strptime(date_tag.get_text(strip=True), "%B %d, %Y")
    except ValueError:
        return None

    if since_date and pub_date.date() < since_date:
        return "STOP"

    if until_date and pub_date.date() > until_date:
        return "SKIP"

    # CONTENT
    content = soup.select_one("div.elementor-widget-theme-post-content")
    if not content:
        return None

    paragraphs = []
    for p in content.find_all("p"):
        text = p.get_text(strip=True)

        if "The FED are happy to share blogs" in text:
            break

        if text:
            paragraphs.append(text)

    return {
        "url": url,
        "title": title,
        "date": pub_date.strftime("%Y-%m-%d"),
        "text": "\n".join(paragraphs),
    }


# ---------------------------------------------------------
# Main scraper
# ---------------------------------------------------------
def scrape_fed(since_date: "date | None" = None, until_date: "date | None" = None, output_path: "str | None" = None, append: bool = False) -> list[dict]:
    """Scrape Foundation for Educational Development news via HTML pagination.

    Args:
        since_date: Earliest publication date to include.
        until_date: Latest publication date to include.
        output_path: Path to save CSV output.
        append: If True, append to existing CSV instead of overwriting.

    Returns:
        List of dicts with keys: url, title, date, text
    """
    all_articles = []
    page = 1

    print("🚀 Starting FED News & Resources scrape…")

    while True:
        page_url = BASE_URL if page == 1 else PAGE_URL.format(page)
        print(f"\n📄 Scraping page {page}: {page_url}")

        r = requests.get(page_url, headers=HEADERS)
        links = extract_links(r.text)

        print(f"🔗 Found {len(links)} article links")

        if not links:
            print("⛔ No more pages — stopping.")
            break

        stop = False
        for link in links:
            print(f"   📰 Scraping: {link}")
            article = scrape_article(link, since_date=since_date, until_date=until_date)

            if article == "STOP":
                print("⛔ Reached cutoff date — stopping scrape.")
                stop = True
                break

            if article == "SKIP":
                continue

            if article:
                all_articles.append(article)

            time.sleep(1)

        if stop:
            break

        page += 1
        time.sleep(1)

    _save(all_articles, output_path, append)
    return all_articles


def _save(articles, output_path, append):
    if output_path is None:
        return
    out = Path(output_path)
    df = pd.DataFrame(articles)
    mode = "a" if append else "w"
    header = not (append and out.exists())
    df.to_csv(out, mode=mode, header=header, index=False)
    print(f"💾 Saved {len(df)} articles → {out}")


# ---------------------------------------------------------
# Run
# ---------------------------------------------------------
if __name__ == "__main__":
    scrape_fed(output_path=_DEFAULT_OUTPUT)
