"""
fairness_audit.py

Compute fairness metrics over the latest classification run and write a
headline row to the `fairness_log` Supabase table + a per-source/per-class
detail CSV to data/archive/fairness/.

Checks:
  - Per-source confidence disparity (max - min of mean top1_confidence by source)
  - Per-coverage-area disparity (country) — N/A while inference is England-only
  - Class share distribution (most/least predicted class)
  - Aggregate confidence (mean/median top1, pct below 50%, top1-top2 gap)

Inputs:
  data/modelling/classified_articles.csv  (from classify_via_api / classify_backfill)

Outputs:
  data/archive/fairness/<batch_id>.csv     (per-source x per-class detail)
  fairness_log row in Supabase             (headline metrics)

Usage:
  python -m src.inference.fairness_audit
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv


DATA_DIR = Path("data/modelling")
ARCHIVE_DIR = Path("data/archive/fairness")
DEFAULT_INPUT = DATA_DIR / "classified_articles.csv"
ACTIVE_RUN_FILE = Path("models/runs/active.txt")


def _active_run_id_fallback() -> str:
    if ACTIVE_RUN_FILE.exists():
        return ACTIVE_RUN_FILE.read_text().strip()
    return "unknown"


def per_source_class_detail(df: pd.DataFrame) -> pd.DataFrame:
    """Long-format breakdown: one row per (source, class) combo."""
    return (
        df.groupby(["source", "top1"])
        .agg(
            n=("top1_confidence", "size"),
            mean_top1_conf=("top1_confidence", "mean"),
            median_top1_conf=("top1_confidence", "median"),
            pct_below_50=("top1_confidence", lambda s: (s < 0.50).mean()),
        )
        .reset_index()
        .rename(columns={"top1": "class"})
        .sort_values(["source", "class"])
    )


def per_source_disparity(df: pd.DataFrame) -> dict:
    by_source = df.groupby("source")["top1_confidence"].mean().sort_values()
    return {
        "source_confidence_min": float(by_source.min()),
        "source_confidence_max": float(by_source.max()),
        "source_confidence_disparity": float(by_source.max() - by_source.min()),
        "source_with_lowest_confidence": str(by_source.index[0]),
        "source_with_highest_confidence": str(by_source.index[-1]),
    }


def overall_confidence(df: pd.DataFrame) -> dict:
    out = {
        "mean_top1_confidence": float(df["top1_confidence"].mean()),
        "median_top1_confidence": float(df["top1_confidence"].median()),
        "pct_below_50": float((df["top1_confidence"] < 0.50).mean()),
    }
    if "top2_confidence" in df.columns:
        out["mean_top2_confidence"] = float(df["top2_confidence"].mean())
        out["mean_confidence_gap"] = float(
            (df["top1_confidence"] - df["top2_confidence"]).mean()
        )
    return out


def class_share_summary(df: pd.DataFrame) -> dict:
    counts = df["top1"].value_counts(normalize=True)
    return {
        "n_classes_predicted": int(df["top1"].nunique()),
        "most_predicted_class": str(counts.index[0]),
        "most_predicted_class_share": float(counts.iloc[0]),
        "least_predicted_class": str(counts.index[-1]),
        "least_predicted_class_share": float(counts.iloc[-1]),
    }


def coverage_area_summary(df: pd.DataFrame) -> dict:
    # `country` is England-only at the moment so disparity is meaningless.
    # When Four Nations data lands, this branch wakes up automatically.
    if "country" not in df.columns or df["country"].nunique() <= 1:
        return {
            "coverage_confidence_disparity": None,
            "coverage_class_share_max_disparity": None,
        }
    by_country = df.groupby("country")["top1_confidence"].mean()
    share = pd.crosstab(df["country"], df["top1"], normalize="index")
    return {
        "coverage_confidence_disparity": float(by_country.max() - by_country.min()),
        "coverage_class_share_max_disparity": float(
            (share.max(axis=0) - share.min(axis=0)).max()
        ),
    }


def _push_to_supabase(row: dict) -> None:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("  SUPABASE_URL/SUPABASE_SERVICE_KEY not set — skipping push.")
        return
    from supabase import create_client
    create_client(url, key).table("fairness_log").insert(row).execute()
    print("  Pushed fairness_log row to Supabase.")


def main() -> int:
    load_dotenv()
    if not DEFAULT_INPUT.exists():
        print(f"  ERROR: {DEFAULT_INPUT} not found. Run classify first.")
        return 1

    df = pd.read_csv(DEFAULT_INPUT)
    df = df.dropna(subset=["top1", "top1_confidence", "source"])
    if df.empty:
        print("  ERROR: no rows with predictions to audit.")
        return 1

    print(f"Auditing {len(df)} predictions across {df['source'].nunique()} sources.")

    run_id = (
        str(df["model_run_id"].iloc[0])
        if "model_run_id" in df.columns
        else _active_run_id_fallback()
    )
    batch_id = datetime.now().strftime("%Y-%m-%d_%H%M%S")

    detail = per_source_class_detail(df)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    detail_path = ARCHIVE_DIR / f"{batch_id}.csv"
    detail.to_csv(detail_path, index=False)
    print(f"  Saved detail CSV → {detail_path}")

    row = {
        "run_id": run_id,
        "batch_id": batch_id,
        "n_articles": int(len(df)),
        "n_sources": int(df["source"].nunique()),
        **overall_confidence(df),
        **per_source_disparity(df),
        **coverage_area_summary(df),
        **class_share_summary(df),
        "detail_csv_path": str(detail_path),
    }

    print("\n  Summary row:")
    for k, v in row.items():
        if isinstance(v, float):
            print(f"    {k}: {v:.4f}")
        else:
            print(f"    {k}: {v}")

    _push_to_supabase(row)
    print("  Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
