"""
model_loader.py
Loads the active classifier (sklearn) + embedder (sentence-transformer) at
server startup and caches them. Reads the active version from
models/runs/active.txt and loads from models/runs/<run_id>/.

Layout this expects:

    models/runs/
        active.txt                              # one line: the active run_id
        v1_2026-05-16/
            classifier.joblib                   # joblib of the sklearn classifier
            run_metadata.json                   # what this version is

Decommissioning / rollback procedure: see docs/MODEL_LIFECYCLE.md
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = PROJECT_ROOT / "models" / "runs"
ACTIVE_FILE = RUNS_DIR / "active.txt"


@dataclass
class ModelBundle:
    """Everything the API needs to make a prediction."""
    classifier: Any           # sklearn classifier (LogReg here)
    embedder: Any             # sentence-transformers SentenceTransformer
    run_id: str               # which version is loaded
    metadata: dict            # contents of run_metadata.json
    classes: list[str]        # ordered class labels (from classifier.classes_)


_bundle: ModelBundle | None = None


def get_model() -> ModelBundle:
    """Return the cached bundle, loading it on first call."""
    global _bundle
    if _bundle is None:
        _bundle = _load()
    return _bundle


def _resolve_active_run_id() -> str:
    """Read models/runs/active.txt and return the run_id."""
    if not ACTIVE_FILE.exists():
        raise RuntimeError(
            f"No active.txt found at {ACTIVE_FILE}. "
            f"Create it with one line — the run_id to load (e.g. 'v1_2026-05-16')."
        )
    run_id = ACTIVE_FILE.read_text().strip()
    if not run_id:
        raise RuntimeError(f"{ACTIVE_FILE} is empty.")
    return run_id


def _load() -> ModelBundle:
    run_id = _resolve_active_run_id()
    run_dir = RUNS_DIR / run_id
    if not run_dir.exists():
        raise RuntimeError(
            f"active.txt points at run_id={run_id!r} but {run_dir} doesn't exist."
        )

    logger.info("Loading active model: %s", run_id)

    # 1. Classifier (sklearn, joblib-serialized) — fast (~0.1s)
    classifier_path = run_dir / "classifier.joblib"
    classifier = joblib.load(classifier_path)

    # 2. Metadata (records what this version is)
    metadata_path = run_dir / "run_metadata.json"
    metadata: dict = {}
    if metadata_path.exists():
        with metadata_path.open(encoding="utf-8") as f:
            metadata = json.load(f)

    # 3. Embedder (sentence-transformer) — slow (3-5s, downloads ~80MB the first time)
    #    Import is lazy so this module can be imported without the dep
    #    just to inspect run_id / metadata.
    from sentence_transformers import SentenceTransformer
    embedding_model_name = (
        metadata.get("embedding_model")
        or "sentence-transformers/all-MiniLM-L6-v2"
    )
    logger.info("Loading embedder: %s", embedding_model_name)
    embedder = SentenceTransformer(embedding_model_name)

    classes = list(getattr(classifier, "classes_", []))

    logger.info(
        "Model loaded. run_id=%s, classes=%d, variant=%s",
        run_id, len(classes), metadata.get("variant", "?"),
    )

    return ModelBundle(
        classifier=classifier,
        embedder=embedder,
        run_id=run_id,
        metadata=metadata,
        classes=classes,
    )
