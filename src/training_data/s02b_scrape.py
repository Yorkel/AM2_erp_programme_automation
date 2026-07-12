"""
s02b_scrape.py
For each new newsletter item, fetches the article URL and extracts a short
snippet from the article body. Updates the `text` column (title + snippet)
so it matches what the model was trained on (title + short description text).

Only used in the --new-newsletter pipeline path. Historical training data
already has curator descriptions which serve the same purpose.

Falls back to title only if scraping fails (paywall, timeout, 404, etc.).

Input:  data/preprocessed/newsletters_preprocessed.csv
Output: data/preprocessed/newsletters_preprocessed.csv (updates `text` in place,
        adds `scraped_snippet` column)

Runtime: scrapes URLs with 10 threads — usually under 2 minutes for one newsletter.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests
from bs4 import BeautifulSoup

# -----------------------------
# CONFIG
# -----------------------------
INPUT_CSV  = "data/preprocessed/newsletters_preprocessed.csv"
OUTPUT_CSV = "data/preprocessed/newsletters_preprocessed.csv"

MAX_SNIPPET_WORDS = 80
REQUEST_TIMEOUT   = 8
MAX_WORKERS       = 10

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; ERP-newsletter-research-bot/1.0)"
    )
}

# Domains we can't scrape usefully
SKIP_DOMAINS = {
    "www.ft.com", "www.thetimes.com", "www.telegraph.co.uk",
    "twitter.com", "x.com", "www.linkedin.com",
    "www.youtube.com", "youtu.be", "youtube.com", "vimeo.com",
}


# -----------------------------
# SCRAPING
# -----------------------------

def extract_snippet(html: str, max_words: int) -> str:
    """Pull the first N words of paragraph text from raw HTML."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer",
                     "aside", "form", "noscript"]):
        tag.decompose()

    container = (
        soup.find("article")
        or soup.find("main")
        or soup.find(attrs={"role": "main"})
        or soup
    )

    paragraphs = container.find_all("p")
    text = " ".join(p.get_text(" ", strip=True) for p in paragraphs[:10])
    words = text.split()[:max_words]
    return " ".join(words)


def scrape_url(url: str, domain: str) -> str | None:
    if domain in SKIP_DOMAINS or not url:
        return None
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers=HEADERS,
                            allow_redirects=True)
        resp.raise_for_status()
        if "html" not in resp.headers.get("Content-Type", ""):
            return None
        snippet = extract_snippet(resp.text, MAX_SNIPPET_WORDS)
        return snippet.strip() or None
    except Exception:
        return None


# -----------------------------
# MAIN
# -----------------------------

def main():
    print("Loading preprocessed data...")
    df = pd.read_csv(INPUT_CSV)
    print(f"  Loaded {len(df)} rows")

    links   = df["link"].fillna("").tolist()
    domains = df["domain"].fillna("").tolist()
    snippets = [None] * len(df)
    completed = 0

    print(f"\nScraping {len(df)} URLs ({MAX_WORKERS} threads)...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_idx = {
            executor.submit(scrape_url, link, domain): i
            for i, (link, domain) in enumerate(zip(links, domains))
            if link
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                snippets[idx] = future.result()
            except Exception:
                snippets[idx] = None
            completed += 1

    df["scraped_snippet"] = snippets

    # Build text: title + scraped snippet, fall back to title alone
    def build_text(row):
        title   = str(row["title"]) if pd.notna(row["title"]) else ""
        snippet = row["scraped_snippet"]
        if snippet and str(snippet).strip():
            return (title + " " + str(snippet)).strip()
        return title.strip()

    df["text"] = df.apply(build_text, axis=1)
    df["text_length_words"] = df["text"].str.split().str.len()

    scraped_ok = df["scraped_snippet"].notna().sum()
    print(f"  Scraped successfully: {scraped_ok}/{len(df)} rows")
    print(f"  Fell back to title only: {len(df) - scraped_ok} rows")

    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
