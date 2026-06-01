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
BASE = "https://www.rte.ie"
START_URL = "https://www.rte.ie/news/education/"

_DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "data" / "test" / "ireland_rte_full.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# RTÉ article URL pattern: /news/.../YYYY/MMDD/NNNNNNN-slug/
_ARTICLE_RE = re.compile(r"/news/.*?/\d{4}/\d{4}/\d+-")


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
        if _ARTICLE_RE.search(href) and href not in links:
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

    if r.status_code != 200:
        print(f"  HTTP {r.status_code} for {url}")
        return None

    soup = BeautifulSoup(r.text, "html.parser")

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # Date parsing — try <time> tag, then meta tag, then URL pattern
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
        meta = soup.find("meta", {"property": "article:published_time"})
        if meta and meta.get("content"):
            try:
                pub_date = datetime.fromisoformat(meta["content"].replace("Z", "+00:00")).date()
            except ValueError:
                pass

    # Fallback: extract date from URL  /news/.../2026/0312/...
    if not pub_date:
        m = re.search(r"/(\d{4})/(\d{2})(\d{2})/", url)
        if m:
            try:
                pub_date = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date()
            except ValueError:
                pass

    if pub_date:
        if since_date and pub_date < since_date:
            return "STOP"
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
def scrape_rte(since_date: "date | None" = None, until_date: "date | None" = None, output_path: "str | None" = None, append: bool = False) -> list[dict]:
    """Scrape RTÉ News education section via HTML pagination.

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
    max_pages = 10  # RTÉ only keeps ~37 stories, no point going further
    no_new_articles = 0

    print("Starting RTÉ News Education scrape...")

    for page_num in range(max_pages):
        if page_num == 0:
            url = START_URL
        else:
            url = f"{START_URL}?page={page_num}"

        print(f"  Page {page_num}: {url}")

        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
        except requests.RequestException as e:
            print(f"  Request failed: {e}")
            break

        if r.status_code != 200:
            print(f"  HTTP {r.status_code} — stopping.")
            break

        links = _extract_links(r.text)
        new_links = [l for l in links if l not in seen]
        print(f"  Found {len(links)} links ({len(new_links)} new)")

        if not links:
            print("  No links — end of pages.")
            break

        articles_before = len(all_articles)
        stop = False
        for link in new_links:
            seen.add(link)
            print(f"    {link}")

            result = _scrape_article(link, since_date=since_date, until_date=until_date)

            if result == "STOP":
                print("  Reached since_date cutoff — stopping.")
                stop = True
                break
            if result == "SKIP":
                continue
            if result:
                all_articles.append(result)

            time.sleep(1)

        if stop:
            break

        # Stop if no new articles were added on this page
        if len(all_articles) == articles_before:
            no_new_articles += 1
            if no_new_articles >= 2:
                print("  No new articles for 2 pages — end of archive.")
                break
        else:
            no_new_articles = 0

        print(f"  {len(all_articles)} articles so far")
        time.sleep(1)

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
    scrape_rte(output_path=_DEFAULT_OUTPUT)
