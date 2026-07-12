-- Migration 008: curator_feedback + source_suggestions
-- Both are append-only logs written by the dashboard; read by analysis notebooks.

create table if not exists public.curator_feedback (
  id uuid not null default gen_random_uuid (),
  submitted_at timestamp with time zone not null default now(),
  accuracy_rating text null,                -- 'Very poor' | 'Poor' | 'OK' | 'Good' | 'Excellent'
  problem_categories text[] null,            -- list of category keys flagged by the curator
  missing_sources text null,
  suggestions text null,
  constraint curator_feedback_pkey primary key (id)
) TABLESPACE pg_default;

create index if not exists idx_curator_feedback_submitted_at
  on public.curator_feedback using btree (submitted_at desc) tablespace pg_default;


create table if not exists public.source_suggestions (
  id uuid not null default gen_random_uuid (),
  suggested_at timestamp with time zone not null default now(),
  source_name text not null,                 -- curator's name for the source
  url text null,                              -- their best-guess root URL
  coverage_hint text null,                    -- what they think it covers
  notes text null,
  status text not null default 'pending',     -- 'pending' | 'added' | 'rejected'
  constraint source_suggestions_pkey primary key (id)
) TABLESPACE pg_default;

create index if not exists idx_source_suggestions_status
  on public.source_suggestions using btree (status, suggested_at desc) tablespace pg_default;
