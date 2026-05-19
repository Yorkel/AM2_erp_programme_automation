import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from pathlib import Path
import time
from urllib.parse import urlparse

BASE_URL = "https://ffteducationdatalab.org.uk/blog/"
PAGE_URL = "https://ffteducationdatalab.org.uk/blog/page/{}/"

_DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "data" / "training" / "england" / "fft_education_datalab.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; FFTDatalabScraper/1.0)"
}

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

# ---------------------------------------------------------
# Extract article links (exclude archive pages)
# ---------------------------------------------------------
def extract_links(html):
    soup = BeautifulSoup(html, "html.parser")
    links = []

    for a in soup.find_all("a", href=True):
        href = a["href"]

        if href.startswith("https://ffteducationdatalab.org.uk/20"):
            path_parts = urlparse(href).path.strip("/").split("/")

            # Expect: YYYY / MM / slug
            if len(path_parts) >= 3:
                links.append(href)

    # preserve order, remove duplicates
    return list(dict.fromkeys(links))


# ---------------------------------------------------------
# Extract full article
# ---------------------------------------------------------
def scrape_article(url, since_date=None, until_date=None):
    r = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")

    # ---------------------------
    # TITLE
    # ---------------------------
    title_tag = soup.select_one("h2.entry-title")
    if not title_tag:
        print(f"⚠️ Missing title: {url}")
        return None

    title = title_tag.get_text(strip=True)

    # ---------------------------
    # DATE
    # ---------------------------
    meta = soup.select_one("div.fusion-meta-info-wrapper")
    if not meta:
        print(f"⚠️ Missing meta block: {url}")
        return None

    pub_date = None
    for span in meta.find_all("span"):
        text = span.get_text(strip=True)

        if any(month in text for month in MONTHS):
            for fmt in (
                "%dth %B %Y",
                "%dst %B %Y",
                "%dnd %B %Y",
                "%drd %B %Y",
                "%d %B %Y",
            ):
                try:
                    pub_date = datetime.strptime(text, fmt)
                    break
                except ValueError:
                    continue

        if pub_date:
            break

    if not pub_date:
        print(f"⚠️ Failed to parse date: {url}")
        return None

    if since_date and pub_date.date() < since_date:
        return "STOP"

    if until_date and pub_date.date() > until_date:
        return "SKIP"

    # ---------------------------
    # CONTENT (STOP AT NOTES)
    # ---------------------------
    content = soup.select_one("div.post-content")
    if not content:
        print(f"⚠️ Missing content: {url}")
        return None

    # Remove Notes / footnotes section
    footnotes = content.find("div", id="footnotes_section")
    if footnotes:
        footnotes.decompose()

    for tag in content.find_all(["script", "style", "aside"]):
        tag.decompose()

    paragraphs = [
        p.get_text(strip=True)
        for p in content.find_all("p")
        if p.get_text(strip=True)
    ]

    text = "\n".join(paragraphs)

    return {
        "url": url,
        "title": title,
        "date": pub_date.strftime("%Y-%m-%d"),
        "text": text,
    }


# ---------------------------------------------------------
# Main scraper
# ---------------------------------------------------------
def scrape_fft_datalab(since_date: "date | None" = None, until_date: "date | None" = None, output_path: "str | None" = None, append: bool = False) -> list[dict]:
    """Scrape FFT Education Datalab blog posts via HTML pagination.

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

    print("🚀 Starting FFT Education Datalab scrape…")

    while True:
        page_url = BASE_URL if page == 1 else PAGE_URL.format(page)
        print(f"\n📄 Scraping page {page}: {page_url}")

        r = requests.get(page_url, headers=HEADERS)
        links = extract_links(r.text)

        print(f"🔗 Found {len(links)} article links")

        if not links:
            break

        stop = False
        for link in links:
            print(f"   📰 Scraping: {link}")
            result = scrape_article(link, since_date=since_date, until_date=until_date)

            if result == "STOP":
                print(f"⛔ Reached cutoff date — stopping scraper.")
                stop = True
                break

            if result == "SKIP":
                continue

            if result:
                all_articles.append(result)

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
    df = pd.DataFrame(articles, columns=["url", "title", "date", "text"])
    mode = "a" if append else "w"
    header = not (append and out.exists())
    df.to_csv(out, mode=mode, header=header, index=False)
    print(f"💾 Saved {len(df)} articles → {out}")


# ---------------------------------------------------------
# Run scraper
# ---------------------------------------------------------
if __name__ == "__main__":
    scrape_fft_datalab(output_path=_DEFAULT_OUTPUT)
