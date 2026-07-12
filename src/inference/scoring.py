"""
scoring.py
Compute per-article composite scores for curator priority sorting. Runs after
classify_via_api, before push_predictions.

NOTE: near-duplicate CLUSTERING was REMOVED 2026-06-22 (it grouped distinct
articles as "the same story" and hid them in the dashboard). cluster_id /
cluster_size / is_cluster_lead are still written as trivial singletons (own id,
size 1, own lead) so the table schema and dashboard reads don't break.

Outputs added to each article record:
  - cluster_id, cluster_size, is_cluster_lead — trivial singletons (no clustering)
  - source_authority, recency_score, substance_score, composite_score — the
    composite is a defensible default for sort order; individual components
    are kept too so the dashboard can re-sort by any of them.

Source authority weights live in `src/scraping/source_authority.yml`; the
curator can edit those without touching code. Composite formula:

    composite =  0.30 * source_authority
              +  0.25 * top1_confidence
              +  0.20 * recency_score
              +  0.15 * substance_score
              +  0.10 * 1.0   (cluster-lead term, now a uniform constant)

All in [0, 1]; composite is too.
"""

from __future__ import annotations

from datetime import datetime, date
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from dotenv import load_dotenv


DATA_DIR = Path("data/modelling")
ARCHIVE_DIR = Path("data/archive/scored")
DEFAULT_INPUT = DATA_DIR / "classified_articles.csv"
DEFAULT_OUTPUT = DATA_DIR / "classified_articles.csv"   # overwrites with extra columns

AUTHORITY_YAML = Path("src/scraping/source_authority.yml")

# Composite weights
W_AUTHORITY  = 0.30
W_CONFIDENCE = 0.25
W_RECENCY    = 0.20
W_SUBSTANCE  = 0.15
W_LEAD_BONUS = 0.10


# ─── Component scores ────────────────────────────────────────────────────────

def load_authority_table(path: Path = AUTHORITY_YAML) -> dict[str, float]:
    """Read the curator-editable source authority table.
    Falls back to a small built-in default if the file doesn't exist yet."""
    if path.exists():
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return {k.lower(): float(v) for k, v in data.items()}
    # Built-in fallback — replace by curating source_authority.yml
    return {
        "_default": 0.6,
        "gov.uk": 1.0, "dfe": 1.0, "ofsted": 1.0,
        "schoolsweek.co.uk": 0.95, "schoolsweek": 0.95,
        "tes.com": 0.9,
        "bbc.co.uk": 0.85, "bbc_education": 0.85,
        "theguardian.com": 0.85, "the_guardian": 0.85,
        "epi": 0.9, "epi.org.uk": 0.9,
        "wonkhe.com": 0.3, "hepi.ac.uk": 0.3,
    }


def authority_score(source: str, table: dict[str, float]) -> float:
    """Lookup with fallback. Source matching is case-insensitive."""
    if not isinstance(source, str) or not source:
        return table.get("_default", 0.6)
    return table.get(source.lower(), table.get("_default", 0.6))


def recency_score(article_date: date | str | None, today: date | None = None) -> float:
    """0.95^days_old, clipped to [0, 1]. ~0.49 at 14 days, ~0.21 at 30 days."""
    if article_date is None:
        return 0.0
    if isinstance(article_date, str):
        try:
            article_date = pd.to_datetime(article_date).date()
        except Exception:
            return 0.0
    if today is None:
        today = date.today()
    days_old = max(0, (today - article_date).days)
    return float(np.clip(0.95 ** days_old, 0.0, 1.0))


def substance_score(text: str) -> float:
    """word_count / 500, clamped to [0.3, 1.0]. Very short pieces capped at 0.3."""
    if not isinstance(text, str):
        return 0.3
    n = len(text.split())
    return float(np.clip(n / 500.0, 0.3, 1.0))



# ─── Composite & pipeline ────────────────────────────────────────────────────

def add_scores_to_df(df: pd.DataFrame, *, authority_table: dict[str, float],
                     today: date | None = None) -> pd.DataFrame:
    """Add cluster_id, cluster_size, is_cluster_lead (trivial singletons — no
    clustering), the four component scores, and composite_score columns to `df`.

    Requires the input to have already been classified (top1_confidence column
    present). No embeddings are needed — clustering was removed 2026-06-22.
    """
    if today is None:
        today = date.today()

    df = df.copy().reset_index(drop=True)

    # Near-duplicate CLUSTERING REMOVED (2026-06-22): it grouped distinct articles
    # as "the same story" and hid them behind "+N similar" in the dashboard, so
    # real content went missing (e.g. two separate IfG early-years pieces). Every
    # article is now its own singleton. The cluster_* columns are kept (size 1,
    # each its own lead) so the classify_newsletter schema and dashboard reads
    # don't break. No embeddings are computed anymore.
    df["cluster_id"] = df.index
    df["cluster_size"] = 1
    df["is_cluster_lead"] = True

    # Component scores (kept — used for content ordering)
    df["source_authority"] = df["source"].apply(
        lambda s: authority_score(s, authority_table)
    )
    df["recency_score"] = df["article_date"].apply(
        lambda d: recency_score(d, today=today)
    )
    df["substance_score"] = df["text_clean"].apply(substance_score)

    # Composite. The cluster-lead term is now a uniform constant (every article is
    # its own lead), so it no longer affects ordering — kept only for score
    # continuity with historical rows.
    df["composite_score"] = (
        W_AUTHORITY  * df["source_authority"]
      + W_CONFIDENCE * df["top1_confidence"].fillna(0.0)
      + W_RECENCY    * df["recency_score"]
      + W_SUBSTANCE  * df["substance_score"]
      + W_LEAD_BONUS * 1.0
    ).clip(0.0, 1.0)

    return df


def main() -> int:
    """Module entry point (called by pipeline.py). Reads classified_articles.csv,
    adds scoring columns in place, writes back. Also writes a timestamped
    snapshot to data/archive/scored/."""
    load_dotenv()
    if not DEFAULT_INPUT.exists():
        print(f"  ERROR: {DEFAULT_INPUT} not found. Run classify_via_api first.")
        return 1

    df = pd.read_csv(DEFAULT_INPUT)
    print(f"  Loaded {len(df)} classified articles")

    authority_table = load_authority_table()
    print(f"  Authority table: {len(authority_table)} sources curated "
          f"(default={authority_table.get('_default', 0.6)})")

    df = add_scores_to_df(df, authority_table=authority_table)

    # Working file
    df.to_csv(DEFAULT_OUTPUT, index=False)
    print(f"  Wrote {len(df)} rows with scoring columns → {DEFAULT_OUTPUT}")

    # Snapshot
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    snap = ARCHIVE_DIR / f"{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.csv"
    df.to_csv(snap, index=False)
    print(f"  Snapshot → {snap}")

    # Summary
    n_clusters = df["cluster_id"].nunique()
    n_singletons = (df["cluster_size"] == 1).sum()
    n_multi = len(df) - n_singletons
    print(f"\n  Clustering: {n_clusters} clusters, {n_singletons} singletons, "
          f"{n_multi} articles in multi-article clusters")

    print("\n  Composite score quartiles:")
    print(df["composite_score"].describe()[["min", "25%", "50%", "75%", "max"]].to_string())

    top = df.nlargest(5, "composite_score")[
        ["source", "title", "composite_score", "cluster_size", "is_cluster_lead"]
    ]
    print("\n  Top 5 by composite score:")
    print(top.to_string(index=False))

    print("  Done.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
