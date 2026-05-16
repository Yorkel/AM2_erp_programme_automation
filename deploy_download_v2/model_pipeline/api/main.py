"""
main.py

FastAPI app for NMF topic model inference.

Endpoints:
  GET  /health   — confirm model is loaded and return run metadata
  POST /predict  — accept batch of raw articles, return topic assignments

Run:
  uvicorn model_pipeline.api.main:app --reload
"""

from contextlib import asynccontextmanager

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from model_pipeline.api.model_loader import get_model
from model_pipeline.training.s02_cleaning import run_cleaning
from model_pipeline.training.s03_spacy_processing import run_spacy_processing


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class ArticleIn(BaseModel):
    article_id: str
    text: str


class PredictRequest(BaseModel):
    articles: list[ArticleIn]


class TopicResult(BaseModel):
    article_id: str
    topic_id: int
    topic_name: str
    confidence: float
    all_weights: dict[str, float]


class PredictResponse(BaseModel):
    predictions: list[TopicResult]
    run_id: str
    n_articles: int


class HealthResponse(BaseModel):
    status: str
    run_id: str
    n_topics: int


# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    get_model()  # load models once at startup
    yield


app = FastAPI(title="Topic Model API", lifespan=lifespan)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
def health():
    bundle = get_model()
    return HealthResponse(
        status="ok",
        run_id=bundle.run_id,
        n_topics=len(bundle.topic_names),
    )


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest):
    if not request.articles:
        raise HTTPException(status_code=422, detail="articles list is empty")

    bundle = get_model()

    # Build DataFrame matching the expected pipeline input
    df = pd.DataFrame([
        {"article_id": a.article_id, "text": a.text}
        for a in request.articles
    ])

    # Full preprocessing pipeline (mirrors s02 → s03)
    df = run_cleaning(df)
    df = run_spacy_processing(df)

    # Vectorize (transform only — vectorizer was fitted on training data)
    X = bundle.vectorizer.transform(df["text_final"].fillna("").astype(str))

    # NMF inference → document-topic weight matrix W (n_docs x n_topics)
    W = bundle.nmf_model.transform(X)

    dominant_ids = W.argmax(axis=1)
    dominant_weights = W.max(axis=1)

    predictions = []
    for i, article in enumerate(request.articles):
        topic_id = int(dominant_ids[i])
        all_weights = {
            bundle.topic_names[j]: round(float(W[i, j]), 6)
            for j in range(W.shape[1])
        }
        predictions.append(TopicResult(
            article_id=article.article_id,
            topic_id=topic_id,
            topic_name=bundle.topic_names[topic_id],
            confidence=round(float(dominant_weights[i]), 6),
            all_weights=all_weights,
        ))

    return PredictResponse(
        predictions=predictions,
        run_id=bundle.run_id,
        n_articles=len(predictions),
    )
