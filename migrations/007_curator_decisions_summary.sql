-- Migration 007: add summary columns to curator_decisions
-- Used by src/inference/summarise.py — populated when the curator clicks
-- "Generate Summary" in the dashboard on an accepted article.

alter table public.curator_decisions
  add column if not exists summary               text  null,
  add column if not exists summary_generated_at  timestamp with time zone  null;

create index if not exists idx_curator_decisions_summary_generated_at
  on public.curator_decisions using btree (summary_generated_at desc nulls last) tablespace pg_default;
