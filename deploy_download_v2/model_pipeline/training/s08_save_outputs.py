"""
s08_save_outputs.py

Step 08: Save outputs (versioned artifacts for reproducibility)

Saves into:
experiments/outputs/runs/<run_id>/

Artifacts:
- fitted TF-IDF vectorizer (joblib)
- trained NMF model (joblib)
- topic mapping (json)
- run metadata (json)
- optional evaluation CSVs (from S07) saved into run folder + data/Interrim/

Run:
python -m model_pipeline.training.s08_save_outputs
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np
import pandas as pd

from model_pipeline.training.s06_topic_allocation import TOPIC_NAMES

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ✅ THIS is the missing constant your S09/S10 expect
RUNS_DIR = PROJECT_ROOT / "experiments" / "outputs" / "runs"


@dataclass
class RunMetadata:
    run_id: str
    created_utc: str
    dataset_name: str
    n_docs: int
    tfidf_shape: tuple[int, int]

    # TF-IDF params (audit trail)
    tfidf_min_df: Optional[float]
    tfidf_max_df: Optional[float]
    tfidf_max_features: Optional[int]
    tfidf_ngram_range: list[int]
    tfidf_vocab_size: Optional[int]

    # NMF params
    nmf_n_topics: int
    nmf_init: str
    nmf_random_state: int
    nmf_max_iter: int

    reconstruction_error: float

    dominant_topic_weight_min: float
    dominant_topic_weight_mean: float
    dominant_topic_weight_max: float


def make_run_id(country: str = "") -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    return f"{country}_{timestamp}" if country else timestamp


def _safe_float(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return float("nan")


def _write_json(obj: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    logger.info("Wrote JSON: %s", path)


def _copy_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
        logger.info("Copied: %s -> %s", src, dst)
    else:
        logger.info("Optional file missing (skipped): %s", src)


def _write_df_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    logger.info("Wrote CSV: %s", path)


def save_run_outputs(
    *,
    run_dir: Path,
    vectorizer,
    nmf_model,
    X,
    dataset_name: str = "full_retro",
    reconstruction_error: Optional[float] = None,
    W: Optional[np.ndarray] = None,
    coherence_df: Optional[pd.DataFrame] = None,
    stability_df: Optional[pd.DataFrame] = None,
) -> Path:
    """
    Persist artifacts + metadata into run_dir.
    Optionally save S07 evaluation outputs into:
      - run_dir/evaluation/
      - data/Interrim/ (so the rest of your project still finds them)
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Saving run artifacts to: %s", run_dir)

    # 1) Artifacts
    vec_path = run_dir / "vectorizer.joblib"
    nmf_path = run_dir / "nmf_model.joblib"
    joblib.dump(vectorizer, vec_path)
    joblib.dump(nmf_model, nmf_path)
    logger.info("Saved: %s", vec_path)
    logger.info("Saved: %s", nmf_path)

    # 2) Topic mapping
    topic_map_path = run_dir / "topic_names.json"
    _write_json({str(k): v for k, v in TOPIC_NAMES.items()}, topic_map_path)

    # 3) Compute W if missing
    if W is None:
        try:
            W = nmf_model.transform(X)
        except Exception:
            W = None

    if reconstruction_error is None:
        reconstruction_error = getattr(nmf_model, "reconstruction_err_", None)

    # 4) TF-IDF params
    ngram = getattr(vectorizer, "ngram_range", (1, 1))
    vocab_size = None
    if hasattr(vectorizer, "vocabulary_") and vectorizer.vocabulary_ is not None:
        vocab_size = len(vectorizer.vocabulary_)

    # 5) Dominant stats
    if W is not None:
        dom = W.max(axis=1)
        dom_min, dom_mean, dom_max = dom.min(), dom.mean(), dom.max()
        n_docs = int(W.shape[0])
        n_topics = int(W.shape[1])
    else:
        dom_min = dom_mean = dom_max = float("nan")
        n_docs = int(X.shape[0])
        n_topics = int(getattr(nmf_model, "n_components", len(TOPIC_NAMES)))

    meta = RunMetadata(
        run_id=run_dir.name,
        created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        dataset_name=dataset_name,
        n_docs=n_docs,
        tfidf_shape=(int(X.shape[0]), int(X.shape[1])),
        tfidf_min_df=getattr(vectorizer, "min_df", None),
        tfidf_max_df=getattr(vectorizer, "max_df", None),
        tfidf_max_features=getattr(vectorizer, "max_features", None),
        tfidf_ngram_range=[int(ngram[0]), int(ngram[1])],
        tfidf_vocab_size=vocab_size,
        nmf_n_topics=n_topics,
        nmf_init=str(getattr(nmf_model, "init", "")),
        nmf_random_state=int(getattr(nmf_model, "random_state", -1) or -1),
        nmf_max_iter=int(getattr(nmf_model, "max_iter", -1)),
        reconstruction_error=_safe_float(reconstruction_error),
        dominant_topic_weight_min=_safe_float(dom_min),
        dominant_topic_weight_mean=_safe_float(dom_mean),
        dominant_topic_weight_max=_safe_float(dom_max),
    )
    _write_json(asdict(meta), run_dir / "run_metadata.json")

    # 6) Save evaluation outputs if provided (country-specific filenames)
    country = dataset_name.split("_")[0]  # eng_training -> eng
    if coherence_df is not None:
        _write_df_csv(coherence_df, run_dir / "evaluation" / "coherence_sweep.csv")
        _write_df_csv(coherence_df, PROJECT_ROOT / "data" / "evaluation_outputs" / f"coherence_sweep_{country}.csv")

    if stability_df is not None:
        _write_df_csv(stability_df, run_dir / "evaluation" / "stability_seeds.csv")
        _write_df_csv(stability_df, PROJECT_ROOT / "data" / "evaluation_outputs" / f"stability_seeds_{country}.csv")

    return run_dir


def generate_summary_json(
    df_alloc: pd.DataFrame,
    model_id: str,
    topic_names: dict[int, str],
    reconstruction_error: float,
    stability: float,
    mean_dominant_weight: float,
    max_dominant_weight: float,
    out_path: Path,
) -> Path:
    """
    Generate a dashboard-ready summary JSON from the pipeline's topic-allocated DataFrame.

    This replaces the notebook-generated summary JSONs, ensuring the summary
    matches the pipeline's preprocessing (correct article count, correct assignments).
    """
    topic_data = []
    n_topics = len(topic_names)

    for i in range(n_topics):
        mask = df_alloc["topic_num"] == i
        count = int(mask.sum())
        if count > 0:
            source_counts = df_alloc.loc[mask, "source"].value_counts()
            top_source = source_counts.index[0]
            top_source_pct = round(float(source_counts.iloc[0] / source_counts.sum()), 2)
        else:
            top_source = "unknown"
            top_source_pct = 0.0

        topic_data.append({
            "topic_num": i,
            "name": topic_names.get(i, f"topic_{i}"),
            "count": count,
            "pct": round(count / len(df_alloc) * 100, 1),
            "top_source": top_source,
            "top_source_pct": top_source_pct,
            "single_source": top_source_pct > 0.90,
        })

    summary = {
        "model_id": model_id,
        "n_topics": n_topics,
        "n_articles": len(df_alloc),
        "metrics": {
            "reconstruction_error": round(reconstruction_error, 4),
            "stability": round(stability, 4),
            "mean_dominant_weight": round(mean_dominant_weight, 4),
            "max_dominant_weight": round(max_dominant_weight, 4),
        },
        "topics": topic_data,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(summary, out_path)
    logger.info("Wrote summary JSON: %s (%d articles, %d topics)", out_path, len(df_alloc), n_topics)
    return out_path


def main() -> None:
    import logging

    from model_pipeline.training.s01_data_loader import load_articles
    from model_pipeline.training.s02_cleaning import run_cleaning
    from model_pipeline.training.s03_spacy_processing import run_spacy_processing
    from model_pipeline.training.s04_vectorisation import run_vectorisation
    from model_pipeline.training.s05_nmf_training import train_nmf
    from model_pipeline.training.s06_topic_allocation import run_topic_allocation, export_analysis_ready_csv
    from model_pipeline.training.s07_evaluation import (
        evaluate_coherence_over_topic_range,
        evaluate_topic_stability,
    )

    logging.basicConfig(level=logging.INFO)
    logging.getLogger("gensim").setLevel(logging.WARNING)

    dataset_name = "full_retro"
    run_id = make_run_id()
    run_dir = RUNS_DIR / run_id

    df = load_articles(dataset_name)
    df = run_cleaning(df)
    df = run_spacy_processing(df)

    vec_out = run_vectorisation(df)
    nmf_out = train_nmf(vec_out.X)

    # S06 export
    df_alloc = run_topic_allocation(df, nmf_model=nmf_out.nmf_model, vectorizer=vec_out.vectorizer)
    analysis_csv = PROJECT_ROOT / "data" / dataset_name / "retro_topics_analysis_ready.csv"
    export_analysis_ready_csv(df_alloc, analysis_csv)

    # S07 evaluation
    coh_df = evaluate_coherence_over_topic_range(
        X=vec_out.X,
        feature_names=vec_out.feature_names,
        texts_tokens=df["tokens_final"].tolist(),
        topic_range=range(5, 80, 5),
        n_top_words=10,
    )
    stab_df = evaluate_topic_stability(X=vec_out.X)

    save_run_outputs(
        run_dir=run_dir,
        vectorizer=vec_out.vectorizer,
        nmf_model=nmf_out.nmf_model,
        X=vec_out.X,
        dataset_name=dataset_name,
        reconstruction_error=nmf_out.reconstruction_error,
        W=nmf_out.W,
        coherence_df=coh_df,
        stability_df=stab_df,
    )

    print("\n✅ Saved run artifacts to:")
    print(run_dir)


if __name__ == "__main__":
    main()