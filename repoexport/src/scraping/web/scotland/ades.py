import requests
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path
import time
from datetime import datetime

# ----------------------------------------------------------
# Config
# ----------------------------------------------------------
API_URL = "https://www.ades.scot/wp-json/wp/v2/posts"

_DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "data" / "test" / "scotland_ades.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


# ----------------------------------------------------------
# Main scraper
# ----------------------------------------------------------
def scrape_ades(since_date: "date | None" = None, until_date: "date | None" = None, output_path: "str | None" = None, append: bool = False) -> list[dict]:
    """Scrape ADES posts via WordPress REST API.

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
    per_page = 10

    print("Starting ADES scrape (WP API)...")

    while True:
        params = {"per_page": per_page, "page": page, "orderby": "date", "order": "desc"}
        if since_date:
            params["after"] = f"{since_date}T00:00:00"
        if until_date:
            params["before"] = f"{until_date}T23:59:59"

        print(f"  Fetching page {page}...")
        try:
            r = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
        except requests.RequestException as e:
            print(f"  Request failed: {e}")
            break

        if r.status_code == 400:
            print(f"  No more pages — stopping.")
            break
        if r.status_code != 200:
            print(f"  HTTP {r.status_code} — stopping.")
            break

        posts = r.json()
        if not posts:
            print(f"  Empty response — stopping.")
            break

        print(f"  Got {len(posts)} posts")

        for post in posts:
            title = BeautifulSoup(post["title"]["rendered"], "html.parser").get_text(strip=True)
            date_str = post["date"][:10]
            url = post["link"]

            # Extract text from rendered content
            content_html = post.get("content", {}).get("rendered", "")
            soup = BeautifulSoup(content_html, "html.parser")
            text = "\n".join(
                p.get_text(" ", strip=True)
                for p in soup.find_all("p")
                if p.get_text(strip=True)
            )

            if not text.strip():
                print(f"    Skipping empty post: {title[:60]}")
                continue

            all_articles.append({
                "url": url,
                "title": title,
                "date": date_str,
                "text": text,
            })

        print(f"  {len(all_articles)} articles collected so far")
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
    scrape_ades(output_path=_DEFAULT_OUTPUT)
