-- Migration 005: fairness_log
-- One row per classification run. Records summary fairness metrics across:
--   - per-source confidence disparity
--   - per-coverage-area confidence disparity
--   - per-class share disparity
-- Detailed per-source/per-class breakdowns are saved alongside as a CSV archive
-- (data/archive/fairness/<date>_<week>.csv); this table holds the headlines.

create table if not exists public.fairness_log (
  id uuid not null default gen_random_uuid (),
  run_id text not null,                              -- model run id (matches models/runs/active.txt)
  batch_id text not null,                            -- pipeline batch identifier (e.g. timestamp + week)
  computed_at timestamp with time zone not null default now(),

  -- Sample size
  n_articles integer not null,
  n_sources integer not null,
  n_classes_predicted integer not null,

  -- Overall confidence
  mean_top1_confidence numeric not null,
  median_top1_confidence numeric,
  pct_below_50 numeric,
  mean_top2_confidence numeric,
  mean_confidence_gap numeric,

  -- Per-source confidence disparity
  source_confidence_min numeric,
  source_confidence_max numeric,
  source_confidence_disparity numeric,               -- max - min
  source_with_lowest_confidence text,
  source_with_highest_confidence text,

  -- Per-coverage-area disparity (England vs Four Nations etc.)
  coverage_confidence_disparity numeric,
  coverage_class_share_max_disparity numeric,        -- biggest per-class share difference across coverage areas

  -- Class share — distributional sanity
  most_predicted_class text,
  most_predicted_class_share numeric,
  least_predicted_class text,
  least_predicted_class_share numeric,

  -- Pointer to detail file
  detail_csv_path text,

  constraint fairness_log_pkey primary key (id)
) TABLESPACE pg_default;

create index IF not exists idx_fairness_log_computed_at
  on public.fairness_log using btree (computed_at desc) TABLESPACE pg_default;

create index IF not exists idx_fairness_log_run_id
  on public.fairness_log using btree (run_id) TABLESPACE pg_default;

create index IF not exists idx_fairness_log_batch_id
  on public.fairness_log using btree (batch_id) TABLESPACE pg_default;
