"""
s09_mlflow_logging.py

Step 09: MLflow logging (file-based store: experiments/mlruns)

- Lazy imports mlflow so S10 can still run without MLflow installed.
- Logs params/metrics + artifacts (run_dir + analysis CSV)

Run:
python -m model_pipeline.training.s09_mlflow_logging
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MLRUNS_DIR = PROJECT_ROOT / "experiments" / "mlruns"


def _safe_float(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return float("nan")


def _set_file_tracking_uri(mlflow, mlruns_dir: Path = MLRUNS_DIR) -> None:
    mlruns_dir.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(mlruns_dir.resolve().as_uri())
    logger.info("MLflow tracking URI set to: %s", mlruns_dir.resolve().as_uri())


def log_run_to_mlflow(
    *,
    experiment_name: str,
    run_name: str,
    dataset_name: str,
    X_shape: tuple[int, int],
    vectorizer,
    nmf_model,
    reconstruction_error: float,
    run_dir: Path,
    df_alloc_path: Optional[Path] = None,
) -> str:
    try:
        import mlflow  # ✅ lazy import
    except ImportError as e:
        raise ImportError("MLflow is not installed. Install with: pip install mlflow") from e

    _set_file_tracking_uri(mlflow)
    mlflow.set_experiment(experiment_name)

    ngram = getattr(vectorizer, "ngram_range", (1, 1))
    vocab_size = None
    if hasattr(vectorizer, "vocabulary_") and vectorizer.vocabulary_ is not None:
        vocab_size = len(vectorizer.vocabulary_)

    params = {
        "dataset_name": dataset_name,
        "n_docs": int(X_shape[0]),
        "n_features": int(X_shape[1]),
        "tfidf_min_df": getattr(vectorizer, "min_df", None),
        "tfidf_max_df": getattr(vectorizer, "max_df", None),
        "tfidf_max_features": getattr(vectorizer, "max_features", None),
        "tfidf_ngram_min": int(ngram[0]),
        "tfidf_ngram_max": int(ngram[1]),
        "tfidf_vocab_size": vocab_size,
        "nmf_n_topics": int(getattr(nmf_model, "n_components", -1)),
        "nmf_init": str(getattr(nmf_model, "init", "")),
        "nmf_random_state": int(getattr(nmf_model, "random_state", -1) or -1),
        "nmf_max_iter": int(getattr(nmf_model, "max_iter", -1)),
    }
    metrics = {"reconstruction_error": _safe_float(reconstruction_error)}

    with mlflow.start_run(run_name=run_name) as active_run:
        run_id = active_run.info.run_id

        mlflow.log_params({k: v for k, v in params.items() if v is not None})
        mlflow.log_metrics(metrics)

        if run_dir.exists():
            mlflow.log_artifacts(str(run_dir), artifact_path="pipeline_run")

        if df_alloc_path is not None and df_alloc_path.exists():
            mlflow.log_artifact(str(df_alloc_path), artifact_path="analysis_outputs")

        mlflow.set_tags(
            {
                "pipeline": "AM1_topic_modelling",
                "storage": "file-based",
                "run_dir": str(run_dir),
            }
        )

        logger.info("MLflow run created: %s", run_id)
        return run_id


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
    from model_pipeline.training.s08_save_outputs import save_run_outputs, RUNS_DIR, make_run_id

    logging.basicConfig(level=logging.INFO)
    logging.getLogger("gensim").setLevel(logging.WARNING)

    dataset_name = "full_retro"
    run_name = make_run_id()
    run_dir = RUNS_DIR / run_name

    df = load_articles(dataset_name)
    df = run_cleaning(df)
    df = run_spacy_processing(df)

    vec_out = run_vectorisation(df)
    nmf_out = train_nmf(vec_out.X)

    df_alloc = run_topic_allocation(df, nmf_model=nmf_out.nmf_model, vectorizer=vec_out.vectorizer)
    analysis_csv = PROJECT_ROOT / "data" / dataset_name / "retro_topics_analysis_ready.csv"
    export_analysis_ready_csv(df_alloc, analysis_csv)

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

    mlflow_run_id = log_run_to_mlflow(
        experiment_name="AM1_topic_modelling",
        run_name=run_name,
        dataset_name=dataset_name,
        X_shape=(int(vec_out.X.shape[0]), int(vec_out.X.shape[1])),
        vectorizer=vec_out.vectorizer,
        nmf_model=nmf_out.nmf_model,
        reconstruction_error=nmf_out.reconstruction_error,
        run_dir=run_dir,
        df_alloc_path=analysis_csv,
    )

    print("\n✅ MLflow run_id:", mlflow_run_id)
    print("✅ MLruns dir:", (PROJECT_ROOT / "experiments" / "mlruns").as_posix())


if __name__ == "__main__":
    main()