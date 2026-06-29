---
title: ERP Classifier
emoji: 📰
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8000
pinned: false
---

# ERP Newsletter Automation

Production automation for the weekly ESRC Education Research Programme newsletter.

The system monitors education-policy sources, ingests relevant articles, classifies each item into the newsletter's editorial sections, enriches articles with AI-assisted summaries and topic metadata, and presents the review workflow in a curator dashboard. It is a human-in-the-loop editorial tool: the model accelerates triage and sorting, while curators keep control of judgement, selection, edits, and publication.

Before automation, newsletter production involved roughly 7 hours per week of manual source scanning, deduplication, sectioning, and summary writing. This repo turns that work into a monitored pipeline plus a Streamlit review app.

> Status: live production system. Daily weekday ingestion feeds a weekly curator cycle.

---

## What it does

```text
100+ configured sources
(custom web scrapers, RSS feeds, Google Alerts)
        |
        v
Scraping pipeline
        |
        v
Supabase / Postgres
articles, predictions, curator decisions, monitoring logs
        |
        +----------------------+
        |                      |
        v                      v
Classifier API            Claude enrichment
FastAPI + Docker          summaries, topic sentence,
Hugging Face Space        geography/topic tags
        |
        v
Streamlit curator dashboard
Triage -> Select Categories -> Newsletter Draft -> Sources
        |
        v
Curator finalises and publishes the newsletter
```

GitHub Actions orchestrate scraping, classification, enrichment sweeps, weekly reset, health checks, drift monitoring, fairness audit, and Supabase backups.

---

## Key features

- **Source ingestion:** 101 active source entries in `src/scraping/sources.yml`, split across custom web scrapers, RSS feeds, and Google Alerts.
- **Article normalisation:** shared URL cleanup, text extraction, date handling, relevance filtering, deduplication, and Supabase upserts.
- **Section classifier:** sentence-transformer embeddings (`sentence-transformers/all-MiniLM-L6-v2`) with a scikit-learn classifier.
- **Model serving:** FastAPI Docker service deployed on a Hugging Face Space, exposing `/health`, `/predict`, and Prometheus `/metrics`.
- **AI enrichment:** Claude-assisted summaries, topic sentences, and geography/topic tags, with production fallback handling for runner connectivity issues (see `docs/decisions/`).
- **Curator dashboard:** Streamlit app for triage, categorisation, draft assembly, source feedback, and password-gated write actions.
- **Monitoring:** pipeline health checks, self-healing sweeps for missing classifications/summaries, drift logging, and a fairness audit.
- **Decision records:** production incidents, modelling choices, data-layer design, monitoring design, and security notes are documented in `docs/decisions/`.

---

## Results

The classifier is intentionally scoped to the six newsletter sections that can be learned from historical newsletter data. Two internal update sections are written manually and excluded from classification. It is an assistive ranking/triage layer, not an autonomous publishing system.

| Metric | Score |
|---|---|
| Held-out macro F1 | **0.725** (bootstrap 95% CI [0.644, 0.796]) |
| Held-out weighted F1 | 0.705 |
| Held-out top-2 accuracy | 0.879 |
| Validation macro F1 (baseline) | 0.750 |
| Real-world weighted F1 (264 manually-labelled production articles) | 0.630 |

The held-out vs real-world gap (0.705 → 0.630 weighted) is analysed in [`docs/decisions/evaluation_findings.md`](docs/decisions/evaluation_findings.md).

### Newsletter sections

| Curator-facing section | Model label |
|---|---|
| Teacher recruitment, retention & development | `teacher_rrd` |
| EdTech | `edtech` |
| Political environment & key organisations | `political_environment_key_organisations` |
| Four Nations | `four_nations` |
| Research – Practice – Policy | `policy_practice_research` |
| What matters in education? | `what_matters_ed` |

Manual-only sections (never classified): *Update from Programme*, *Update from PI*.

---

## Tech stack

Python · Supabase/Postgres · scikit-learn · sentence-transformers · FastAPI · Docker · Hugging Face Spaces · Streamlit · GitHub Actions · Anthropic Claude · Prometheus metrics.

---

## Repository layout

| Path | Purpose |
|---|---|
| `src/scraping/` | Source registry, scrapers, RSS/Google-Alert adapters, relevance filters, enrichment sweeps |
| `src/inference/` | Supabase pulls, classifier API calls, scoring, push-back, drift/fairness utilities |
| `src/serving/` | FastAPI classifier service (the deployed model API) |
| `src/classify/` | Training, embedding, evaluation, and baseline scripts |
| `src/training_data/` | Historical newsletter extraction, cleaning, preprocessing, splits |
| `src/monitoring/` | Pipeline health checks and production verification |
| `dashboard/` | Streamlit curator dashboard |
| `migrations/` | Supabase schema migrations and view definitions |
| `models/runs/` | Versioned model artefacts and the active-model pointer |
| `.github/workflows/` | Scheduled scraping, classification, monitoring, reset, and backup workflows |
| `docs/decisions/` | Engineering decisions, model card, incident write-ups, threat model, lifecycle notes |
| `notebooks/` | Modelling, evaluation, drift, SHAP, and analysis notebooks |
| `paper/` | Research manuscript and write-up material |
| `experiments/agent_draft/` | Experimental newsletter-drafting agent trials + a construct-validity finding for the paper |

---

## Production deployment

The live classifier API runs as a Docker-based Hugging Face Space. The root `Dockerfile` builds the serving image for `src/serving/api.py`, and the Space reads the YAML frontmatter at the top of this README (`sdk: docker`, `app_port: 8000`).

`render.yaml` remains in the repo as legacy infrastructure-as-code from an earlier Render deployment; Render is **not** the current production target. See [`docs/deployment/huggingface_spaces_setup.md`](docs/deployment/huggingface_spaces_setup.md).

---

## Local setup

Install dependencies (full pipeline, or API only):

```bash
pip install -r requirements.txt
pip install -r requirements-api.txt   # classifier API only
```

Create a local `.env` with the variables for the parts you want to run:

```bash
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_KEY=<service-role-key>
SUPABASE_ANON_KEY=<anon-key>
ANTHROPIC_API_KEY=<anthropic-key>
CLASSIFIER_API_URL=https://<owner>-<space>.hf.space
CLASSIFIER_API_KEY=<hf-token-if-space-is-private>
# Optional: when the runner routes Claude through the Space proxy
ANTHROPIC_BASE_URL=https://<owner>-<space>.hf.space
PROXY_TOKEN=<shared-secret-for-the-proxy>
```

For the Streamlit dashboard, also set a Streamlit secret:

```toml
CURATOR_PASSWORD = "<dashboard-password>"
```

---

## Running locally

```bash
# Serve the classifier API
uvicorn src.serving.api:app --reload --port 8000

# Run the curator dashboard
streamlit run dashboard/app.py

# Scrape a date window
python -m src.scraping.run --since 2026-05-12 --until 2026-05-15

# Weekly inference against Supabase
python src/pipeline.py --inference

# Classify an existing local pull without re-pulling
python src/pipeline.py --classify-only

# Dry-run a single source
python -m src.scraping.try_source --source dfe --since 2026-05-01 --save
```

---

## Development / verification

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -q
python -m pip check
python -c "from fastapi.testclient import TestClient; from src.serving.api import app; c=TestClient(app); print(c.get('/health').json())"
```

The pytest suite is intentionally lightweight and network-free; it covers URL
normalisation, scraper helpers, and the Anthropic proxy-token client wiring.

---

## Automation (GitHub Actions)

| Workflow | Purpose |
|---|---|
| `weekly_reset.yml` | Archives curator decisions and starts the new weekly cycle |
| `scrape.yml` | Weekday source ingestion + summary/tag enrichment sweeps |
| `classify.yml` | Calls the deployed classifier and writes predictions to Supabase |
| `health_check.yml` | Self-heals missing classifications/summaries; fails loudly if unresolved |
| `drift.yml` | Logs distribution, confidence, and embedding drift |
| `fairness.yml` | Runs section/source fairness checks |
| `backup.yml` | Dumps operational Supabase tables for recovery |

---

## Data model

| Object | Purpose |
|---|---|
| `articles` | Canonical ingested article records |
| `classify_newsletter` | Model predictions, confidence scores, ranking signals |
| `curator_decisions` | Curator accept/reject/category/edit decisions |
| `curator_feedback` | Dashboard/source feedback from curators |
| `drift_log` | Drift-monitor outputs |
| `fairness_log` | Fairness-audit outputs |
| `v_dashboard` | Joined article + prediction view consumed by Streamlit |

Apply the migrations in `migrations/` when bootstrapping a new Supabase project. The data layer is documented in [`docs/decisions/data_layer_design.md`](docs/decisions/data_layer_design.md).

---

## Model governance

The classifier is treated as decision support, not editorial authority.

- The production model **excludes metadata features**, because SHAP analysis showed metadata encouraged source-type shortcuts.
- It predicts only the six learnable editorial sections.
- Curators can override labels, reject articles, edit summaries, and choose final inclusion.
- Monitoring checks drift, low confidence, missing summaries/classifications, and class/source distribution shifts.
- Retraining criteria and lifecycle notes are in [`docs/decisions/model_lifecycle.md`](docs/decisions/model_lifecycle.md) and the [model card](docs/decisions/model_card.md).

---

## Documentation highlights

Start here for the engineering story:

- [`docs/decisions/model_card.md`](docs/decisions/model_card.md)
- [`docs/decisions/data_layer_design.md`](docs/decisions/data_layer_design.md)
- [`docs/decisions/model_lifecycle.md`](docs/decisions/model_lifecycle.md)
- [`docs/decisions/monitoring_redesign_2026_06_11.md`](docs/decisions/monitoring_redesign_2026_06_11.md)
- [`docs/decisions/evaluation_findings.md`](docs/decisions/evaluation_findings.md)
- [`docs/decisions/threat_model_and_security.md`](docs/decisions/threat_model_and_security.md)
- [`docs/deployment/huggingface_spaces_setup.md`](docs/deployment/huggingface_spaces_setup.md)
- [`docs/deployment/deployment_challenges.md`](docs/deployment/deployment_challenges.md)

---

## License

See [`LICENSE`](LICENSE).
