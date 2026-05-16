"""
api.py
FastAPI app that serves the active classifier.

Endpoints:
  GET  /health   — readiness probe; returns active run_id + variant + classes
  POST /predict  — accepts a batch of articles, returns top-1/top-2 predictions

The model is loaded once at startup via the `lifespan` hook; subsequent
requests reuse the cached ModelBundle.

Run locally:
  uvicorn src.serving.api:app --reload --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.serving.model_loader import get_model


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class ArticleIn(BaseModel):
    """One article to classify. text_clean is what the classifier sees."""
    article_id: str = Field(..., description="Caller-supplied id (echoed back in response).")
    text_clean: str = Field(..., description="The text the model classifies. Title + first ~80 words is the training-time shape.")


class PredictRequest(BaseModel):
    articles: list[ArticleIn]


class PredictionResult(BaseModel):
    article_id: str
    top1: str
    top1_confidence: float
    top2: str
    top2_confidence: float
    confidence_gap: float
    model_run_id: str = Field(..., description="Which model version produced this prediction (audit trail).")


class PredictResponse(BaseModel):
    predictions: list[PredictionResult]
    model_run_id: str
    n_articles: int


class HealthResponse(BaseModel):
    status: str
    run_id: str
    variant: str | None
    n_classes: int
    classes: list[str]


# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Eagerly load the model at server startup so the first /predict isn't slow.
    get_model()
    yield


app = FastAPI(
    title="AM2 ERP newsletter classifier",
    description="Classifies education-policy articles into one of the six ERP newsletter categories.",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    bundle = get_model()
    return HealthResponse(
        status="ok",
        run_id=bundle.run_id,
        variant=bundle.metadata.get("variant"),
        n_classes=len(bundle.classes),
        classes=bundle.classes,
    )


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest) -> PredictResponse:
    if not request.articles:
        raise HTTPException(status_code=422, detail="articles list is empty")

    bundle = get_model()

    # 1. Embed all texts in one batch (much faster than one-by-one).
    texts = [a.text_clean for a in request.articles]
    embeddings = bundle.embedder.encode(texts, show_progress_bar=False)

    # 2. Get the full probability distribution for every article.
    proba = bundle.classifier.predict_proba(embeddings)  # shape: (n_articles, n_classes)

    # 3. For each article, pull top-1 + top-2 indices and translate to labels.
    classes_arr = np.array(bundle.classes)
    top2_idx = np.argsort(proba, axis=1)[:, -2:][:, ::-1]   # (n_articles, 2)

    results: list[PredictionResult] = []
    for i, article in enumerate(request.articles):
        i1, i2 = int(top2_idx[i, 0]), int(top2_idx[i, 1])
        p1, p2 = float(proba[i, i1]), float(proba[i, i2])
        results.append(PredictionResult(
            article_id=article.article_id,
            top1=str(classes_arr[i1]),
            top1_confidence=round(p1, 6),
            top2=str(classes_arr[i2]),
            top2_confidence=round(p2, 6),
            confidence_gap=round(p1 - p2, 6),
            model_run_id=bundle.run_id,
        ))

    return PredictResponse(
        predictions=results,
        model_run_id=bundle.run_id,
        n_articles=len(results),
    )
