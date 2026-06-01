import requests
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path
import time
from datetime import datetime

# ----------------------------------------------------------
# Config
# ----------------------------------------------------------
API_URL = "https://www.erc.ie/wp-json/wp/v2/posts"

_DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "data" / "training" / "ireland" / "erc.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ERCScraper/1.0)"
}


def parse_content(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["script", "style", "figure", "aside"]):
        tag.decompose()
    # Skip download link text at end of articles
    SKIP_PHRASES = [
        "can be downloaded here",
        "Read the full report here",
        "Check out the infographic here",
        "Explore the appendices",
        "Download the report",
    ]
    lines = []
    for p in soup.find_all("p"):
        t = p.get_text(" ", strip=True)
        if not t:
            continue
        if any(phrase in t for phrase in SKIP_PHRASES):
            continue
        lines.append(t)
    return "\n".join(lines)


# ----------------------------------------------------------
# Main scraper
# ----------------------------------------------------------
def scrape_erc(since_date: "date | None" = None, until_date: "date | None" = None, output_path: "str | None" = None, append: bool = False) -> list[dict]:
    """Scrape Education Research Centre posts via WordPress REST API.

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

    params = {"per_page": 10, "page": page, "orderby": "date", "order": "desc"}
    if since_date:
        params["after"] = f"{since_date.isoformat()}T00:00:00"
    if until_date:
        params["before"] = f"{until_date.isoformat()}T23:59:59"

    print("Starting ERC scrape (WP API)...")

    while True:
        params["page"] = page
        print(f"  Fetching page {page}...")

        r = requests.get(API_URL, headers=HEADERS, params=params, timeout=30)

        if r.status_code == 400:
            print("  No more pages — stopping.")
            break
        if r.status_code != 200:
            print(f"  HTTP {r.status_code} — stopping.")
            break

        posts = r.json()
        if not posts:
            print("  Empty response — stopping.")
            break

        print(f"  Got {len(posts)} posts")

        for post in posts:
            pub_date = datetime.fromisoformat(post["date"]).date()
            title = BeautifulSoup(post["title"]["rendered"], "html.parser").get_text(strip=True)
            text = parse_content(post["content"]["rendered"])
            url = post["link"]

            all_articles.append({
                "url": url,
                "title": title,
                "date": pub_date.strftime("%Y-%m-%d"),
                "text": text,
            })

        print(f"  {len(all_articles)} articles collected so far")
        page += 1
        time.sleep(0.5)

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
    scrape_erc(output_path=_DEFAULT_OUTPUT)
