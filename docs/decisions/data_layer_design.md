# Data layer design — 2026-05-17

The Supabase data layer for the ERP automation pipeline. Three normalised tables, each with one responsibility, plus a read-only view that joins them for downstream consumers (dashboard, analysis notebooks, drift monitoring).

## Tables

```
articles       (raw scrape)         — exists
classify_newsletter   (model predictions)  — migration 002
curator_decisions     (curator feedback)   — migration 003
v_dashboard           (read view)          — migration 004
```

| Table | Holds | Updated when | Unique constraint |
|---|---|---|---|
| `articles` | URL, title, text, source, article_date, week_number, status | A new article is scraped | `url` |
| `classify_newsletter` | URL, top1, top1_conf, top2, top2_conf, confidence_gap, classified_at | Model runs (re-classifies) | `url` |
| `curator_decisions` | URL, action, label, decided_at, notes | Curator clicks accept/reject in dashboard | `url` |
| `v_dashboard` | `articles` JOIN `classify_newsletter` only — articles + predictions, NOT decisions | Auto (view, always fresh) | n/a (read-only) |

## Data flow

```
                          ┌─→ articles ──┐
   Scraper ───────────────┘                     │
                                                ├── v_dashboard ──→ DASHBOARD reads
   s10 writes ───→ classify_newsletter ─────────┘                       │
                                                                        │
                                                      curator clicks accept/reject
                                                                        │
                                                                        ↓
                                                            curator_decisions (Supabase)
                                                                        │
                                                                        ↓ pull via supabase-py
                                                                        │
                                                            analysis notebooks (local repo)
```

- **Scraper** writes raw articles to `articles`. URL is the unique key — re-scraping the same article does not duplicate.
- **`s10_push_supabase.py`** writes model predictions to `classify_newsletter`, upserting on URL.
- **Dashboard reads** `v_dashboard` (articles + predictions, JOINed on URL). Past curator decisions are NOT shown back in the dashboard.
- **Dashboard writes** decisions to `curator_decisions`, upserting on URL. One-way flow — decisions never return to the dashboard.
- **Analysis notebooks** pull `curator_decisions` from Supabase via `supabase-py` for offline analysis (accuracy, fairness, calibration, etc.).

One direction of flow per table. No table is read AND written by more than one process.

## Design choices considered and rejected

| Considered | Why rejected |
|---|---|
| **A1 — Denormalised separate table** (predictions table duplicates url/title/source from articles) | Risk of DB drift: if article metadata changes (e.g. re-scrape with updated content), the duplicated copy in the predictions table goes stale. Even if unlikely in this pipeline, the design admits the bug. |
| **B — Predictions table with `classifier_run_id` versioning** (one row per (url, run_id) pair, historical predictions retained) | Overkill for a settled production model. Versioning belongs in a model-experimentation context, not a single-model production pipeline. Can be added later via `ALTER TABLE` if a retrain comparison becomes needed. |
| **C — Prediction columns added directly to `articles`** (no new table, single-table reads) | Mixes raw scraped data with derived model output in the same table. Harder to drop/regenerate predictions without affecting source data. Asymmetric once `curator_decisions` is also added — predictions live in one place, decisions in another. |

## Why this is the "top-class" choice (AM2 evidence)

| AM2 criterion | How this design evidences it |
|---|---|
| **K11 / S22** (platform architecture) | Standard ML platform pattern — three tables separating raw / derived / human-labelled data, exposed via a read view |
| **S25** (decommissioning) | Can `TRUNCATE classify_newsletter` and re-run inference without touching articles or decisions — clean model lifecycle support |
| **S6 / S17** (compliance, audit) | Each table has its own `*_at` timestamp (scraped_at / classified_at / decided_at), giving a full audit trail at each lifecycle stage |
| **K15 / S19** (scalability) | Predictions can be regenerated independently of source data and curator labels. Supports rolling model retrains without churn in upstream or downstream tables |
| **K21 / S27** (stakeholder integration) | Dashboard reads predictions via `v_dashboard` and writes decisions to `curator_decisions`. Curators interact via the same data layer the model writes to — no parallel data path. Decisions flow one-way out of the dashboard, keeping the curator workflow lightweight (no "what did I previously decide" lookup) |

Five criteria evidenced by one architectural decision.

## Trade-offs accepted

- **Three tables means JOINs** for any cross-cutting query. Mitigated by the `v_dashboard` view — consumers query the view as if it were one table, never write JOIN logic themselves.
- **No model versioning** (no `classifier_run_id` column). Acceptable while there is one active production model. If a v2 model is ever trained for comparison against v1, this can be added via migration.
- **Curator decision history is not preserved** — `curator_decisions` upserts on URL, so a changed decision overwrites the previous. If decision history becomes important (e.g. tracking curator agreement over time), drop the URL UNIQUE constraint and add `decided_at` to the key.

## Code touchpoints

- `migrations/002_classify_newsletter.sql` — creates predictions table + indexes + FK
- `migrations/003_curator_decisions.sql` — creates decisions table + indexes + FK
- `migrations/004_dashboard_view.sql` — creates `v_dashboard`
- `src/inference/s10_push_supabase.py` — writes to `classify_newsletter` (lean upsert, no duplicated article columns)
- Dashboard code — reads from `v_dashboard`, writes to `curator_decisions` on accept/reject

## Recovery / rollback

All migrations are additive (CREATE TABLE / CREATE VIEW). To roll back: `DROP VIEW v_dashboard; DROP TABLE curator_decisions; DROP TABLE classify_newsletter;`. `articles` is untouched.
