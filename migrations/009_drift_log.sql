-- Migration 009: drift_log
-- One row per drift-monitor run. Mirrors fairness_log in shape; together
-- they form the weekly model-audit pair (run by drift.yml + fairness.yml).
-- Per-class distribution lives in JSONB so changing the label set later
-- doesn't need another migration.

create table if not exists public.drift_log (
  id uuid not null default gen_random_uuid (),
  run_id text not null,                              -- model run id (matches models/runs/active.txt)
  batch_id text not null,                            -- timestamp identifier
  computed_at timestamp with time zone not null default now(),

  -- Window the run was scoped to (set by pipeline.py via INFERENCE_SINCE/UNTIL)
  week_start text,
  week_end text,

  -- Sample size
  n_articles integer not null,

  -- Confidence
  mean_confidence numeric not null,
  median_confidence numeric,
  pct_below_50 numeric,
  pct_below_30 numeric,

  -- Embedding drift vs training centroids
  mean_similarity numeric,
  min_similarity numeric,
  n_drift_flagged integer,

  -- Distributional checks
  class_distribution jsonb,                          -- { "edtech": 0.10, "four_nations": 0.15, ... }
  distribution_alerts jsonb,                         -- [ "edtech: 5% → 18% (delta +13%)", ... ]

  constraint drift_log_pkey primary key (id)
) TABLESPACE pg_default;

create index IF not exists idx_drift_log_computed_at
  on public.drift_log using btree (computed_at desc) TABLESPACE pg_default;

create index IF not exists idx_drift_log_run_id
  on public.drift_log using btree (run_id) TABLESPACE pg_default;

create index IF not exists idx_drift_log_batch_id
  on public.drift_log using btree (batch_id) TABLESPACE pg_default;
