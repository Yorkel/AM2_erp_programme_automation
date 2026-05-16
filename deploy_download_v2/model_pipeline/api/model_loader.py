"""
model_loader.py

Loads the trained vectorizer and NMF model from the most recent run in
experiments/outputs/runs/. Models are loaded once at startup and cached.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import joblib

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = PROJECT_ROOT / "experiments" / "outputs" / "runs"


@dataclass
class ModelBundle:
    vectorizer: object
    nmf_model: object
    topic_names: dict
    run_id: str


_bundle: ModelBundle | None = None


def get_model() -> ModelBundle:
    global _bundle
    if _bundle is None:
        _bundle = _load()
    return _bundle


def _load() -> ModelBundle:
    run_dirs = sorted(
        [p for p in RUNS_DIR.iterdir() if p.is_dir()]
    ) if RUNS_DIR.exists() else []

    if not run_dirs:
        raise RuntimeError(f"No run folders found in {RUNS_DIR}")

    run_dir = run_dirs[-1]
    run_id = run_dir.name
    logger.info("Loading model artifacts from run: %s", run_id)

    vectorizer = joblib.load(run_dir / "vectorizer.joblib")
    nmf_model = joblib.load(run_dir / "nmf_model.joblib")

    with open(run_dir / "topic_names.json", encoding="utf-8") as f:
        raw = json.load(f)
    topic_names = {int(k): v for k, v in raw.items()}

    logger.info("Model loaded. Topics: %d", len(topic_names))
    return ModelBundle(
        vectorizer=vectorizer,
        nmf_model=nmf_model,
        topic_names=topic_names,
        run_id=run_id,
    )
