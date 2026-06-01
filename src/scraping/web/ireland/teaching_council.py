import requests
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path
import time
from datetime import datetime

# ----------------------------------------------------------
# Config
# ----------------------------------------------------------
API_URL = "https://www.teachingcouncil.ie/wp-json/wp/v2/posts"

_DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "data" / "training" / "ireland" / "teaching_council.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TeachingCouncilScraper/1.0)"
}


def parse_content_from_api(html):
    """Parse WP API content (used as fallback only)."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["script", "style", "figure", "aside"]):
        tag.decompose()
    return "\n".join(
        p.get_text(" ", strip=True)
        for p in soup.find_all("p")
        if p.get_text(strip=True)
    )


def fetch_full_text(url):
    """Fetch full article text from the HTML page (not WP API excerpt)."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            return ""
        soup = BeautifulSoup(r.text, "lxml")
        main = soup.find("main")
        if not main:
            return ""
        # Remove boilerplate elements
        for tag in main.find_all(["script", "style", "figure", "aside", "nav"]):
            tag.decompose()
        # Skip the "Published" date paragraph
        paras = []
        for p in main.find_all("p"):
            text = p.get_text(strip=True)
            if text and not text.startswith("Published"):
                paras.append(text)
        return "\n".join(paras)
    except Exception:
        return ""


# ----------------------------------------------------------
# Main scraper
# ----------------------------------------------------------
def scrape_teaching_council(since_date: "date | None" = None, until_date: "date | None" = None, output_path: "str | None" = None, append: bool = False) -> list[dict]:
    """Scrape Teaching Council news via WordPress REST API.

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

    print("Starting Teaching Council scrape (WP API)...")

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

        # Skip words for admin/maintenance posts
        SKIP_WORDS = ["maintenance", "downtime", "scheduled outage", "system update"]

        for post in posts:
            pub_date = datetime.fromisoformat(post["date"]).date()
            title = BeautifulSoup(post["title"]["rendered"], "html.parser").get_text(strip=True)
            url = post["link"]

            # Skip admin/maintenance posts
            if any(w in title.lower() for w in SKIP_WORDS):
                print(f"    Skipping admin post: {title[:60]}")
                continue

            # Fetch full text from HTML page
            text = fetch_full_text(url)

            # Fallback to WP API content if HTML fetch fails
            if not text.strip():
                text = parse_content_from_api(post["content"]["rendered"])

            # Skip posts with no text at all
            if not text.strip():
                print(f"    Skipping empty post: {title[:60]}")
                continue

            print(f"    {pub_date} | {title[:60]} ({len(text)} chars)")

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
    scrape_teaching_council(output_path=_DEFAULT_OUTPUT)
