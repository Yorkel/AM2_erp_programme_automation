# Render free-tier memory limit — diagnosis and mitigation (2026-05-17)

## What happened

When the inference pipeline first called the deployed Render service (`POST /predict` with 50 articles per batch), every request returned **HTTP 502 Bad Gateway**. Render logs showed:

```
Instance failed: cwk25
Ran out of memory (used over 512MB) while running your code.
```

The kernel killed the FastAPI worker mid-request; Render's edge proxy then returned 502 to the client.

## Why it happened

The sentence-transformer model (~90MB on disk → ~200MB in RAM) + Python + FastAPI + Prometheus + tokenisation buffers all sit close to 400MB at idle. Encoding 50 articles in one batch triggers ~150MB peak for attention matrices → over 512MB ceiling, kernel kills the worker, Render edge returns 502.

## How it was diagnosed

1. Pipeline first observed via the orchestrator script (`classify_via_api.py`): three POST attempts in a row got 502 errors with retry/backoff between them — pointing at a server-side problem, not transient network noise.
2. `/health` endpoint responded successfully (returned active `run_id` etc.), confirming the service was up and the model was loaded.
3. Cross-checked against Render logs in the service dashboard — the OOM message was visible there, conclusively naming the cause.

## What was changed

Reduced batch size from 50 → 10 per POST. This brings each request well within the per-request memory envelope (~30-50MB extra for tokenisation/embedding instead of ~150MB).

Trade-offs accepted:
- More HTTP round-trips per pipeline run (86 batches instead of 18)
- Slightly higher overall latency (cold start aside, ~1 minute extra)
- Predictable behaviour within the 512MB free-tier ceiling

## AM2 evidence — criteria this evidences

- **K15 / S19 (distinction)** — Justifies how their consideration of risk and implications has impacted on the security and scalability of machine learning and AI infrastructure
- **S22 / S24 (distinction)** — Evaluates how systems are robust as a result of monitoring
- **K20** — Sources of error and algorithmic bias (operational failure modes count here too)

## Suggested write-up paragraph

> I deployed the FastAPI classifier to Render's free tier and encountered the 512MB memory ceiling on batch inference. Diagnosed via Render logs (`Instance failed: Ran out of memory`), I reduced batch size from 50 → 10 to stay within the per-request memory envelope. Trade-off accepted: more HTTP round-trips, slightly higher overall latency, but predictable behaviour within the free-tier resource constraints. A production deployment would either upgrade to a paid tier (Starter $7/mo → 2GB RAM, no sleep) or shift inference to a worker queue (Celery + Redis, or a managed equivalent).

## What a production deployment would do differently

- **Render Starter plan ($7/mo)** — 2GB RAM, no sleep, faster cold starts. Same Docker image; just plan upgrade. One-line change in `render.yaml`.
- **Worker queue for batch inference** — POST puts articles on a queue; background workers process them, results returned via webhook or polled endpoint. Eliminates the synchronous-request memory pressure entirely.
- **Smaller model** — distilled or quantised version of the embedding model (e.g. `all-MiniLM-L6-v2` int8). Half the RAM but a small accuracy hit.

## What stays the same regardless

The choice of inference architecture (deployed API, not local script) is the right one. The memory limit is a quantitative tuning question, not a qualitative architectural problem.

## Resolution — migrated to Hugging Face Spaces (2026-05-17)

After diagnosing the OOM and demonstrating that even batch=5 worked but ran the risk of failure on the next memory accumulation cycle, the decision was to migrate the deployment to a platform with sufficient headroom — at zero ongoing cost.

> I evaluated the model's memory profile (~400MB resident at idle) against Render's 512MB free tier and identified insufficient headroom. Migrated the deployment to Hugging Face Spaces (16GB RAM free tier), which is purpose-built for ML model serving. The same Docker image deployed unchanged; the memory ceiling no longer constrained batch size.

### Why Hugging Face Spaces specifically

- **16GB RAM free** — 32× the headroom of Render free tier
- **2 vCPU free** — comparable compute
- **Purpose-built for ML model serving** — sentence-transformers is HF-native, the same organisation hosts the model artefact and the deployment
- **Same Docker image** deployed unchanged — no architectural change required
- **Public URL** with a stable subdomain (`<owner>-<space>.hf.space`)

### Trade-offs accepted

- Cold-start times are similar to Render free tier (~30-60s after extended idle)
- Public by default on the free tier (acceptable for this stateless classifier; no PII passes through)
- Auto-deploy is via Git push to the Space repo, slightly different operational model from Render's GitHub integration

### AM2 evidence this generates

- **K11 / S22** — Platform architecture decision evidenced by a deliberate evaluation of alternatives and migration
- **K15 / S19 (distinction)** — Risk-informed scalability decision, with measured memory profile driving the platform choice
- **S25** — Decommissioning consideration: the Render service was retained as a fallback during migration and can be cleanly retired once the HF deployment is stable.

## Related

- `docs/decisions/data_layer_design.md` — overall data layer architecture
- `docs/decisions/old_test_set_archived_2026_05_17.md` — earlier evaluation evidence
- `models/runs/v1_2026-05-16/run_metadata.json` — active model artefact
- `render.yaml` — deployment config
