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
from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from src.serving import metrics as m
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
    bundle = get_model()
    # Stamp model_info gauge so /metrics carries the active run_id label.
    m.model_info.labels(
        run_id=bundle.run_id,
        variant=str(bundle.metadata.get("variant", "unknown")),
    ).set(1)
    yield


app = FastAPI(
    title="AM2 ERP newsletter classifier",
    description="Classifies education-policy articles into one of the six ERP newsletter categories.",
    version="1.0.0",
    lifespan=lifespan,
)

# Adds /metrics + standard HTTP metrics (am2_http_requests_total, latency, etc.)
Instrumentator(
    should_group_status_codes=False,
    excluded_handlers=["/metrics", "/health"],
).instrument(app, metric_namespace="am2", metric_subsystem="").expose(app)


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


@app.get("/claude_probe")
def claude_probe() -> dict:
    """One-off reachability probe: can THIS host reach api.anthropic.com?

    Decides whether the HF Space is a viable host for Claude enrichment
    (incident 2026-06-29: GitHub runners cannot connect to Anthropic). Needs
    no API key and no anthropic SDK — a plain HTTPS request distinguishes
    reachability from a network block:
      - any HTTP response back (e.g. 401 unauthenticated) → host CAN reach Claude
      - a connection error → egress to api.anthropic.com is blocked from here
        (the same failure the runner hits).
    """
    import urllib.error
    import urllib.request

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=b"{}",
        method="POST",
        headers={"content-type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=15)
        return {"reachable": True, "detail": "unexpected 2xx"}
    except urllib.error.HTTPError as e:
        # Got an HTTP status (401/400/...) → the host reached Anthropic fine.
        return {"reachable": True, "status": e.code}
    except urllib.error.URLError as e:
        # No HTTP response at all → connection to the host is blocked.
        return {"reachable": False, "error": str(e.reason)}


@app.post("/v1/messages")
async def anthropic_proxy(request: Request) -> Response:
    """Transparent proxy to api.anthropic.com.

    Lets callers that cannot reach Anthropic directly (the GitHub Actions
    runner — incident 2026-06-29) route Claude calls through this Space, which
    CAN reach it (confirmed via /claude_probe). The caller's API key arrives in
    the x-api-key header, is forwarded as-is, and is NEVER stored or logged
    here. Gated by PROXY_TOKEN: the Space must define it, and callers must send
    the same value as x-proxy-token. This avoids creating an open relay.
    """
    import os

    expected = os.environ.get("PROXY_TOKEN")
    if not expected:
        return Response(content=b'{"error":"proxy not configured"}',
                        status_code=503, media_type="application/json")
    if request.headers.get("x-proxy-token") != expected:
        return Response(content=b'{"error":"forbidden"}', status_code=403,
                        media_type="application/json")

    body = await request.body()
    headers = {"content-type": "application/json"}
    for h in ("x-api-key", "anthropic-version", "anthropic-beta"):
        v = request.headers.get(h)
        if v:
            headers[h] = v

    # Run the blocking upstream call in a worker thread, NOT on the event loop.
    # This handler is async, and a bare urlopen(timeout=120) would otherwise freeze
    # the whole worker's event loop for up to 120s — stalling /health and /predict
    # for every concurrent caller while one Claude call is in flight.
    content, status = await run_in_threadpool(_forward_to_anthropic, body, headers)
    return Response(content=content, status_code=status, media_type="application/json")


def _forward_to_anthropic(body: bytes, headers: dict) -> tuple[bytes, int]:
    """Blocking POST to Anthropic. Returns (response_bytes, status_code). Runs in a
    threadpool via run_in_threadpool so it never blocks the async event loop."""
    import urllib.error
    import urllib.request

    upstream = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body, method="POST",
        headers=headers,
    )
    try:
        with urllib.request.urlopen(upstream, timeout=120) as r:
            return r.read(), r.status
    except urllib.error.HTTPError as e:
        return e.read(), e.code
    except urllib.error.URLError as e:
        return f'{{"error":"upstream unreachable: {e.reason}"}}'.encode(), 502


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
        top1_label = str(classes_arr[i1])
        gap = p1 - p2

        # Emit per-prediction metrics. Histograms record the distribution shape
        # over time; counters give cumulative volume per class / threshold.
        m.top1_confidence.observe(p1)
        m.confidence_gap.observe(gap)
        m.input_text_length.observe(len(article.text_clean))
        m.prediction_class_total.labels(class_name=top1_label).inc()
        if p1 < m.LOW_CONFIDENCE_THRESHOLD:
            m.low_confidence_predictions_total.inc()

        results.append(PredictionResult(
            article_id=article.article_id,
            top1=top1_label,
            top1_confidence=round(p1, 6),
            top2=str(classes_arr[i2]),
            top2_confidence=round(p2, 6),
            confidence_gap=round(gap, 6),
            model_run_id=bundle.run_id,
        ))

    return PredictResponse(
        predictions=results,
        model_run_id=bundle.run_id,
        n_articles=len(results),
    )
