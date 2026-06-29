# Sustainability: Environmental Footprint & Longevity

Sustainability governance artefact. An order-of-magnitude carbon estimate, the
design choices that keep it low, and operational longevity after the funded
period. Supports the Sustainability theme (AM1) and S25 / governance value-adds.
Pairs with `docs/decisions/sustainability_platform.md` (5-year hosting options).

## Footprint — order of magnitude (rough, clearly-stated assumptions)
The whole system is **CPU-only, no GPU, no training loop in production**, so the
footprint is small. A back-of-envelope estimate:

| Activity | Compute | Frequency | Rough energy |
|---|---|---|---|
| Model training | minutes of CPU (MiniLM embeddings + LogReg on ~1.1k items) | one-off / rare retrain | ~0.05 kWh per run |
| Scrape + classify + monitor | a few CPU-minutes on a shared GitHub runner + Render free tier | ~2×/week | ~0.1–0.3 kWh/week |
| Claude enrichment | API calls (compute is Anthropic-side, ~$0.05/wk) | weekly | not locally accounted; small |

**Estimate:** on the order of **~0.1–0.3 kWh/week** locally attributable. Using a
UK grid intensity of roughly **~0.2 kg CO₂e/kWh**, that is on the order of
**tens of grams of CO₂e per week** — i.e. negligible, comparable to a short video
call. (Stated as order-of-magnitude; the dominant compute, Claude inference, sits
with the provider and isn't directly metered here.)

## Design choices that keep the footprint low
- **No GPU; a small frozen model** (`all-MiniLM-L6-v2`, ~22M params) + a linear
  classifier — chosen over fine-tuned DistilBERT partly for exactly this reason.
- **No retraining loop** in production — a frozen model is served between rare,
  triggered retrains.
- **Incremental scraping** (`--since-last-run`) — only the weekly delta is fetched.
- **Batched, scheduled inference** (twice weekly, off-peak) rather than always-on.
- **Free-tier shared infrastructure** (GitHub Actions, Render, HF Space) — high
  utilisation of shared hardware rather than dedicated idle servers.

## Operational longevity (sustainability beyond the funded period)
- **Versioned, hand-over-ready:** the live model is pinned in
  `models/runs/active.txt`; rollback is a one-line repoint; decommissioning is
  documented in `model_lifecycle.md`.
- **Low running cost** (~£0/month hosting + ~£0.20/month enrichment) means the
  pipeline can survive on minimal resource after the funded phase.
- **Platform durability** is the open question, analysed in
  `sustainability_platform.md` (Streamlit → Next.js vs Reflex vs Airtable over a
  5-year horizon) — a deliberate, documented decision still to be finalised.

## Honest limitation
No direct energy metering or carbon accounting tooling is in place; the figures
above are an order-of-magnitude estimate, not measured. Adding lightweight
tracking (e.g. CodeCarbon on the training job) is a sensible, low-effort next step.
