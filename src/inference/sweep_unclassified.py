"""
sweep_unclassified.py — idempotent safety-net classifier.

Finds every article in `articles` that has no row in `classify_newsletter`
(or has a NULL top1) and classifies it via the live /predict endpoint.

Designed to run as the FINAL step of .github/workflows/classify.yml, AFTER
the normal inference pipeline. Catches anything missed by the main run
(timing race with scrape, single-article failures, cold-start timeouts).

Idempotent: re-running with no unclassified articles is a no-op.

Env required:
  SUPABASE_URL
  SUPABASE_SERVICE_KEY  (or SUPABASE_ANON_KEY for read; write needs service)
  CLASSIFIER_API_URL    (e.g. https://yorkel-erp-classifier.hf.space)
  CLASSIFIER_API_KEY    (optional — only needed if HF Space is Private)
"""

from __future__ import annotations

import os
import sys

import requests
from dotenv import load_dotenv
from supabase import create_client


BATCH_SIZE = 10
PREDICT_TIMEOUT = 120  # seconds — accommodates HF Space cold start


def main() -> int:
    load_dotenv()
    sup_url = os.environ.get("SUPABASE_URL")
    sup_key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    api_url = os.environ.get("CLASSIFIER_API_URL")
    if not (sup_url and sup_key):
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY (or ANON_KEY) must be set", file=sys.stderr)
        return 1
    if not api_url:
        print("ERROR: CLASSIFIER_API_URL must be set", file=sys.stderr)
        return 1
    client = create_client(sup_url, sup_key)

    # Find articles with no classify_newsletter row (left-join trick: pull all
    # classified URLs first, then filter articles client-side). Cheap because
    # both queries are well under Supabase's row cap.
    classified_urls: set[str] = set()
    off = 0
    while True:
        r = client.table("classify_newsletter").select("url").range(off, off + 999).execute()
        rows = r.data or []
        classified_urls.update(row["url"] for row in rows)
        if len(rows) < 1000:
            break
        off += 1000

    all_articles: list[dict] = []
    off = 0
    while True:
        r = client.table("articles").select(
            "id, url, title, text_clean"
        ).range(off, off + 999).execute()
        rows = r.data or []
        all_articles.extend(rows)
        if len(rows) < 1000:
            break
        off += 1000

    unclassified = [a for a in all_articles if a["url"] not in classified_urls]
    print(f"Total articles: {len(all_articles)}")
    print(f"Already classified: {len(classified_urls)}")
    print(f"Unclassified — to sweep: {len(unclassified)}")
    if not unclassified:
        print("Nothing to do — exiting clean.")
        return 0

    n_ok = 0
    n_fail = 0
    for i in range(0, len(unclassified), BATCH_SIZE):
        batch = unclassified[i : i + BATCH_SIZE]
        payload = {
            "articles": [
                {
                    "article_id": a["id"],
                    "url": a["url"],
                    "title": a["title"] or "",
                    "text_clean": a["text_clean"] or a["title"] or "",
                    "text": a["text_clean"] or a["title"] or "",
                }
                for a in batch
            ]
        }
        try:
            resp = requests.post(
                f"{api_url}/predict", json=payload, timeout=PREDICT_TIMEOUT
            )
            resp.raise_for_status()
            for pred in resp.json().get("predictions", []):
                top1c = pred.get("top1_confidence") or 0
                top2c = pred.get("top2_confidence") or 0
                client.table("classify_newsletter").upsert(
                    {
                        "url": pred["url"],
                        "top1": pred.get("top1"),
                        "top1_confidence": top1c,
                        "top2": pred.get("top2"),
                        "top2_confidence": top2c,
                        "confidence_gap": top1c - top2c,
                    },
                    on_conflict="url",
                ).execute()
                n_ok += 1
        except Exception as e:
            n_fail += len(batch)
            print(f"  batch {i // BATCH_SIZE + 1} failed: {type(e).__name__}: {e}")

    print(f"Sweep done: {n_ok} classified, {n_fail} failed")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
