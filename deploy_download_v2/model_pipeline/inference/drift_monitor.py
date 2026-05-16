"""
drift_monitor.py

Compute Jensen-Shannon divergence for topic model drift monitoring.

Two types of drift:
  - Within-country: each country's weekly inference vs its own training baseline
  - Cross-country:  compare training baselines between countries

Writes results to Supabase `drift_metrics` table.

Usage:
  python -m model_pipeline.inference.drift_monitor
  python -m model_pipeline.inference.drift_monitor --within-country-only
  python -m model_pipeline.inference.drift_monitor --cross-country-only

Requires .env with SUPABASE_URL and SUPABASE_SERVICE_KEY.
"""

from __future__ import annotations

import argparse
import logging
import os
from collections import defaultdict
from datetime import datetime
from itertools import combinations

import numpy as np
from dotenv import load_dotenv
from scipy.spatial.distance import jensenshannon
from supabase import create_client, Client

load_dotenv()

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1000
COUNTRIES = ["eng", "sco", "irl"]


def get_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise EnvironmentError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")
    return create_client(url, key)


def fetch_topic_probabilities(client: Client, country: str = None, dataset_type: str = None) -> list[dict]:
    """Fetch topic_probabilities from articles_topics with optional filters."""
    articles = []
    page = 0
    while True:
        start = page * CHUNK_SIZE
        query = client.table("articles_topics").select("topic_probabilities, country, week_number, dataset_type")
        if country:
            query = query.eq("country", country)
        if dataset_type:
            query = query.eq("dataset_type", dataset_type)

        response = query.range(start, start + CHUNK_SIZE - 1).execute()
        articles.extend(response.data)
        if len(response.data) < CHUNK_SIZE:
            break
        page += 1
    return articles


def get_topic_keys(articles: list[dict]) -> list[str]:
    """Extract the sorted list of topic keys from topic_probabilities JSONB."""
    keys = set()
    for a in articles:
        probs = a.get("topic_probabilities", {})
        if probs:
            keys.update(probs.keys())
    return sorted(keys)


def compute_topic_distribution(articles: list[dict], topic_keys: list[str]) -> np.ndarray:
    """Compute average topic distribution from articles, using the given topic keys."""
    if not articles or not topic_keys:
        return np.zeros(max(len(topic_keys), 1))

    vectors = []
    for article in articles:
        probs = article.get("topic_probabilities", {})
        if not probs:
            continue
        vec = np.array([probs.get(col, 0.0) for col in topic_keys], dtype=float)
        vectors.append(vec)

    if not vectors:
        return np.zeros(len(topic_keys))

    avg = np.mean(vectors, axis=0)
    total = avg.sum()
    if total > 0:
        avg = avg / total
    return avg


def compute_js_divergence(dist: np.ndarray, baseline: np.ndarray) -> float:
    """Compute JS divergence between two distributions. Returns 0-1."""
    eps = 1e-10
    p = dist + eps
    q = baseline + eps
    p = p / p.sum()
    q = q / q.sum()
    return float(jensenshannon(p, q) ** 2)


def write_drift_metric(client: Client, row: dict) -> None:
    """Write a single drift metric row to Supabase."""
    try:
        client.table("drift_metrics").insert(row).execute()
    except Exception as e:
        logger.error("Failed to write drift metric: %s", e)


# ── Within-country drift ─────────────────────────────────────────────────────

def run_within_country_drift(client: Client, run_id: str) -> None:
    """Compare each country's weekly inference against its own training baseline."""
    logger.info("\n── Within-country drift ──")

    for country in COUNTRIES:
        # Compute this country's training baseline
        training_articles = fetch_topic_probabilities(client, country=country, dataset_type="training")
        if not training_articles:
            logger.warning("No training data for %s. Skipping.", country)
            continue

        topic_keys = get_topic_keys(training_articles)
        baseline = compute_topic_distribution(training_articles, topic_keys)
        logger.info(
            "%s baseline: %d articles, %d topics",
            country, len(training_articles), len(topic_keys),
        )

        # Fetch this country's inference data
        inference_articles = fetch_topic_probabilities(client, country=country, dataset_type="inference")
        weekly_articles = [a for a in inference_articles if a.get("week_number") is not None]

        if not weekly_articles:
            logger.info("No weekly inference data for %s.", country)
            continue

        # Group by week
        weeks = defaultdict(list)
        for a in weekly_articles:
            weeks[int(a["week_number"])].append(a)

        for week_num in sorted(weeks):
            group = weeks[week_num]
            dist = compute_topic_distribution(group, topic_keys)
            js = compute_js_divergence(dist, baseline)

            dominant_topics = set()
            for a in group:
                probs = a.get("topic_probabilities", {})
                if probs:
                    dominant_topics.add(max(probs, key=probs.get))

            row = {
                "week_number": week_num,
                "country": country,
                "js_divergence": round(js, 6),
                "article_count": len(group),
                "unique_topics": len(dominant_topics),
                "model_type": "nmf",
                "period_type": "within_country_weekly",
                "run_id": run_id,
            }

            write_drift_metric(client, row)
            logger.info(
                "  %s week %d: JS=%.4f, articles=%d, unique_topics=%d",
                country, week_num, js, len(group), len(dominant_topics),
            )


# ── Cross-country drift ──────────────────────────────────────────────────────

def run_cross_country_drift(client: Client, run_id: str) -> None:
    """Compare training baselines between each pair of countries.

    Since each country has different topics, we use the union of all topic keys
    and zero-fill missing topics. This gives a comparable vector space.
    """
    logger.info("\n── Cross-country drift ──")

    # Fetch training data and compute baselines per country
    baselines = {}
    all_keys = set()

    for country in COUNTRIES:
        articles = fetch_topic_probabilities(client, country=country, dataset_type="training")
        if not articles:
            logger.warning("No training data for %s. Skipping.", country)
            continue
        keys = get_topic_keys(articles)
        all_keys.update(keys)
        baselines[country] = (articles, keys)

    if len(baselines) < 2:
        logger.warning("Need at least 2 countries for cross-country comparison.")
        return

    # Recompute distributions using the union of all topic keys
    union_keys = sorted(all_keys)
    distributions = {}
    for country, (articles, _) in baselines.items():
        distributions[country] = compute_topic_distribution(articles, union_keys)
        logger.info("%s training: %d articles", country, len(articles))

    # Compare each pair
    for country_a, country_b in combinations(sorted(distributions.keys()), 2):
        js = compute_js_divergence(distributions[country_a], distributions[country_b])

        row = {
            "week_number": None,
            "country": f"{country_a}_vs_{country_b}",
            "js_divergence": round(js, 6),
            "article_count": None,
            "unique_topics": len(union_keys),
            "model_type": "nmf",
            "period_type": "cross_country_training",
            "run_id": run_id,
        }

        write_drift_metric(client, row)
        logger.info(
            "  %s vs %s: JS=%.4f",
            country_a, country_b, js,
        )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
    )

    parser = argparse.ArgumentParser(description="Compute drift metrics per country per period")
    parser.add_argument("--within-country-only", action="store_true", help="Only compute within-country drift")
    parser.add_argument("--cross-country-only", action="store_true", help="Only compute cross-country drift")
    args = parser.parse_args()

    client = get_supabase_client()
    run_id = datetime.now().strftime("%Y-%m-%d_%H%M%S")

    if args.cross_country_only:
        run_cross_country_drift(client, run_id)
    elif args.within_country_only:
        run_within_country_drift(client, run_id)
    else:
        run_within_country_drift(client, run_id)
        run_cross_country_drift(client, run_id)

    print("\nDrift monitoring complete.")


if __name__ == "__main__":
    main()
