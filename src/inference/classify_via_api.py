"""
classify_via_api.py
Classify articles by calling the deployed FastAPI service on Render.

Replaces the previous s08_predict.py local-model approach. Single source of
truth for predictions is now the deployed `/predict` endpoint — the same
model+code that serves any other consumer of the API.

Behaviour:
  - Reads pulled articles from `data/modelling/supabase_inference_articles.csv`
    (produced by pull_articles.py / s07_pull_supabase.py).
  - Batches them (default 50 per request) and POSTs each batch to the API.
  - Handles Render free-tier cold starts: first request retried up to 3 times
    with exponential backoff.
  - Writes the predictions to two places:
      1. `data/modelling/classified_articles.csv` — working file (overwritten,
         consumed by push_predictions.py / s10_push_supabase.py).
      2. `data/archive/classified/<YYYY-MM-DD>_week<N>.csv` — timestamped
         snapshot (NEVER overwritten — periodic archive per the design memo).

Env:
  CLASSIFIER_API_URL  — e.g. https://am2-classifier.onrender.com  (required)
  CLASSIFIER_API_KEY  — optional; sent as Bearer token if set (Render service
                        does not currently require auth, but the wiring is here
                        for when it does)

CLI:
  python -m src.inference.classify_via_api
  python -m src.inference.classify_via_api --batch-size 100
  python -m src.inference.classify_via_api --input <path> --output <path>
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv


# ── Config ────────────────────────────────────────────────────────────────────

DATA_DIR = Path("data/modelling")
ARCHIVE_DIR = Path("data/archive/classified")
DEFAULT_INPUT = DATA_DIR / "supabase_inference_articles.csv"
DEFAULT_OUTPUT = DATA_DIR / "classified_articles.csv"
DEFAULT_BATCH_SIZE = 50
COLD_START_TIMEOUT = 120    # seconds — HF Space free tier sleeps when idle and
                            # the overnight cron slot is when it's coldest; give
                            # the wake-up longer than a single 60s read timeout.
WARM_TIMEOUT = 30           # seconds — once warm, requests are fast
MAX_RETRIES = 5             # health-probe + batch POST attempts (was 3). With a
                            # sleeping Space, 3x60s wasn't enough to wake it.
BACKOFF_BASE = 2            # seconds; doubled each retry


# ── HTTP client ───────────────────────────────────────────────────────────────

def _api_url() -> str:
    url = os.getenv("CLASSIFIER_API_URL")
    if not url:
        raise RuntimeError(
            "CLASSIFIER_API_URL must be set in .env "
            "(e.g. https://am2-classifier.onrender.com)"
        )
    return url.rstrip("/")


def _auth_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    key = os.getenv("CLASSIFIER_API_KEY")
    if key:
        headers["Authorization"] = f"Bearer {key}"
    return headers


def _wake_up_service(base_url: str) -> dict[str, Any]:
    """Hit /health to warm the deployed instance + verify it's healthy.
    Returns the health response (used to log the active run_id)."""
    print(f"  Probing {base_url}/health (free tier may cold-start)...")
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(
                f"{base_url}/health",
                headers=_auth_headers(),
                timeout=COLD_START_TIMEOUT,
            )
            r.raise_for_status()
            data = r.json()
            print(f"  Service ready. Active run_id: {data.get('run_id')} "
                  f"(variant={data.get('variant')}, {data.get('n_classes')} classes)")
            return data
        except requests.exceptions.RequestException as e:
            wait = BACKOFF_BASE * (2 ** attempt)
            print(f"  Health probe attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                print(f"  Retrying in {wait}s...")
                time.sleep(wait)
    raise RuntimeError(f"Could not reach {base_url}/health after {MAX_RETRIES} attempts")


def _post_batch(base_url: str, articles: list[dict]) -> list[dict]:
    """POST one batch of articles to /predict. Returns list of prediction dicts."""
    payload = {"articles": articles}
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.post(
                f"{base_url}/predict",
                json=payload,
                headers=_auth_headers(),
                timeout=WARM_TIMEOUT,
            )
            r.raise_for_status()
            return r.json()["predictions"]
        except requests.exceptions.RequestException as e:
            wait = BACKOFF_BASE * (2 ** attempt)
            print(f"    Batch POST attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(wait)
    raise RuntimeError(f"Batch POST failed after {MAX_RETRIES} attempts")


# ── Pipeline ──────────────────────────────────────────────────────────────────

def classify(input_path: Path, batch_size: int) -> pd.DataFrame:
    """Read articles CSV, classify via API, return DataFrame with predictions joined."""
    df = pd.read_csv(input_path)
    print(f"  Input: {len(df)} articles from {input_path}")

    # Drop missing text — same rule as the local s08_predict.py
    missing = df["text_clean"].isna() | (df["text_clean"].astype(str).str.strip() == "")
    if missing.any():
        print(f"  Dropped {missing.sum()} articles with missing text")
        df = df[~missing].copy()

    base_url = _api_url()
    health = _wake_up_service(base_url)

    df = df.reset_index(drop=True)
    # article_id MUST be a string; if the DataFrame doesn't have one we use the
    # row index. The API only uses this to echo back; downstream we join on it.
    if "article_id" not in df.columns:
        df["article_id"] = df.index.astype(str)
    df["article_id"] = df["article_id"].astype(str)

    n_batches = (len(df) + batch_size - 1) // batch_size
    print(f"  Calling /predict in {n_batches} batch(es) of {batch_size}...")

    all_predictions: list[dict] = []
    for i in range(0, len(df), batch_size):
        batch_df = df.iloc[i:i + batch_size]
        articles = [
            {"article_id": str(row["article_id"]), "text_clean": str(row["text_clean"])}
            for _, row in batch_df.iterrows()
        ]
        batch_num = i // batch_size + 1
        print(f"    Batch {batch_num}/{n_batches}: {len(articles)} articles...")
        predictions = _post_batch(base_url, articles)
        all_predictions.extend(predictions)

    pred_df = pd.DataFrame(all_predictions)
    print(f"  Got {len(pred_df)} predictions back.")

    # Join predictions back onto the article rows (one-to-one by article_id)
    merged = df.merge(pred_df, on="article_id", how="inner", suffixes=("", "_pred"))
    if len(merged) != len(df):
        print(f"  WARNING: merged ({len(merged)}) != input ({len(df)}) — some predictions missing")

    return merged


def write_outputs(df: pd.DataFrame, working_output: Path, archive_dir: Path,
                  batch_id: str | None = None) -> tuple[Path, Path]:
    """Write the working CSV (overwritten) and a timestamped archive (never overwritten)."""
    working_output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(working_output, index=False)
    print(f"  Saved working CSV → {working_output} ({len(df)} rows)")

    archive_dir.mkdir(parents=True, exist_ok=True)
    if batch_id is None:
        batch_id = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    archive_path = archive_dir / f"{batch_id}.csv"
    df.to_csv(archive_path, index=False)
    print(f"  Saved archive snapshot → {archive_path}")

    return working_output, archive_path


def summarise(df: pd.DataFrame) -> None:
    if "top1" not in df.columns:
        return
    dist = df["top1"].value_counts()
    print("\n  Prediction distribution:")
    for cls, count in dist.items():
        print(f"    {cls:<45} {count:>4} ({count / len(df):.1%})")
    if "top1_confidence" in df.columns:
        print(f"\n  Mean top1 confidence: {df['top1_confidence'].mean():.3f}")
        print(f"  Below 50%: {(df['top1_confidence'] < 0.50).mean():.1%}")
    if "model_run_id" in df.columns:
        print(f"  Model run_id (from API): {df['model_run_id'].iloc[0]}")


def _run(input_path: Path, output_path: Path, archive_dir: Path,
         batch_size: int, batch_id: str | None) -> int:
    if not input_path.exists():
        print(f"  ERROR: {input_path} not found. Run pull_articles.py / s07 first.")
        return 1

    df = classify(input_path, batch_size=batch_size)
    write_outputs(df, output_path, archive_dir, batch_id=batch_id)
    summarise(df)
    print("  Done.")
    return 0


def main() -> int:
    """Module entry point — called by pipeline.py / classify.yml workflow.
    Uses env vars + defaults; no argparse so calling code's sys.argv doesn't clash."""
    load_dotenv()
    batch_size = int(os.getenv("CLASSIFIER_BATCH_SIZE", str(DEFAULT_BATCH_SIZE)))
    return _run(DEFAULT_INPUT, DEFAULT_OUTPUT, ARCHIVE_DIR, batch_size, batch_id=None)


if __name__ == "__main__":
    # CLI mode — argparse parses sys.argv. Never called by pipeline.py.
    load_dotenv()
    p = argparse.ArgumentParser(description="Classify articles via the deployed API.")
    p.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument("--archive-dir", type=Path, default=ARCHIVE_DIR)
    p.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    p.add_argument("--batch-id", default=None,
                   help="Identifier for the archive filename. Defaults to current timestamp.")
    args = p.parse_args()
    sys.exit(_run(args.input, args.output, args.archive_dir, args.batch_size, args.batch_id))
