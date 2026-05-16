"""
Basic smoke tests for the AtlasED pipeline.

Run with: python -m pytest tests/ -v
"""

import os
import sys
import numpy as np
import pandas as pd
import pytest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ── Test 1: Supabase connection ──────────────────────────────────────────────

@pytest.mark.skipif(
    not os.environ.get("SUPABASE_URL"),
    reason="SUPABASE_URL not set — skipping integration test"
)
def test_supabase_connection():
    """Sync script can connect to Supabase and fetch data."""
    from dotenv import load_dotenv
    load_dotenv()
    from supabase import create_client

    client = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"]
    )
    r = client.table("articles_raw").select("id", count="exact").limit(1).execute()
    assert r.count > 0, "articles_raw should have data"


# ── Test 2: Preprocessing pipeline ──────────────────────────────────────────

def test_cleaning_produces_text_clean():
    """s02 cleaning produces text_clean column."""
    from model_pipeline.training.s02_cleaning import run_cleaning

    df = pd.DataFrame({
        "text": ["This is a test article about education policy in England."],
        "url": ["https://example.com/test"],
        "date": ["2025-01-01"],
        "source": ["test"],
    })
    result = run_cleaning(df)
    assert "text_clean" in result.columns
    assert len(result) == 1
    assert len(result["text_clean"].iloc[0]) > 0


def test_spacy_produces_text_final():
    """s03 spaCy processing produces text_final and tokens_final."""
    from model_pipeline.training.s02_cleaning import run_cleaning
    from model_pipeline.training.s03_spacy_processing import run_spacy_processing

    df = pd.DataFrame({
        "text": ["Teachers in England are concerned about recruitment and retention of staff."],
        "url": ["https://example.com/test"],
        "date": ["2025-01-01"],
        "source": ["test"],
    })
    df = run_cleaning(df)
    result = run_spacy_processing(df)
    assert "text_final" in result.columns
    assert "tokens_final" in result.columns
    assert len(result["text_final"].iloc[0]) > 0


# ── Test 3: Inference produces topic assignments ────────────────────────────

def test_inference_produces_topics():
    """Saved model can transform new text into topic assignments."""
    import joblib

    runs_dir = Path("experiments/outputs/runs")
    if not runs_dir.exists():
        pytest.skip("No model runs found")

    latest_run = sorted(runs_dir.iterdir())[-1]
    vectorizer = joblib.load(latest_run / "vectorizer.joblib")
    nmf_model = joblib.load(latest_run / "nmf_model.joblib")

    test_text = ["teacher recruitment retention bursary training workforce shortage"]
    X = vectorizer.transform(test_text)
    W = nmf_model.transform(X)

    assert W.shape == (1, 30), f"Expected (1, 30), got {W.shape}"
    assert W.sum() > 0, "Topic weights should be non-zero"
    assert W.argmax() >= 0, "Should have a dominant topic"


# ── Test 4: Drift monitor computes JS divergence ───────────────────────────

def test_js_divergence_computation():
    """JS divergence returns sensible values."""
    from model_pipeline.inference.drift_monitor import compute_js_divergence

    # Identical distributions should have ~0 divergence
    dist = np.array([0.1, 0.2, 0.3, 0.4])
    js = compute_js_divergence(dist, dist)
    assert js < 0.001, f"Identical distributions should have ~0 JS, got {js}"

    # Very different distributions should have high divergence
    dist_a = np.array([0.9, 0.05, 0.03, 0.02])
    dist_b = np.array([0.02, 0.03, 0.05, 0.9])
    js = compute_js_divergence(dist_a, dist_b)
    assert js > 0.3, f"Very different distributions should have high JS, got {js}"
    assert js <= 1.0, f"JS should be bounded at 1.0, got {js}"


# ── Test 5: Topic names are consistent ──────────────────────────────────────

def test_topic_names_complete():
    """TOPIC_NAMES has exactly 30 entries."""
    from model_pipeline.training.s06_topic_allocation import TOPIC_NAMES

    assert len(TOPIC_NAMES) == 30, f"Expected 30 topics, got {len(TOPIC_NAMES)}"
    assert all(isinstance(k, int) for k in TOPIC_NAMES.keys())
    assert all(isinstance(v, str) for v in TOPIC_NAMES.values())
    assert set(TOPIC_NAMES.keys()) == set(range(30))
