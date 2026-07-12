-- Migration 014: curator_decisions_archive
-- Snapshot store for the weekly "Start new week" reset on the curator dashboard.
-- When the curator starts a new week, every current curator_decisions row is
-- copied here (as a JSONB snapshot of the whole row) under a week_label, and
-- the working curator_decisions table is then cleared so the new week starts
-- blank. JSONB payload (not mirrored columns) keeps this archive stable even
-- if curator_decisions gains/loses columns in future migrations.
--
-- Append-only: never updated or deleted by the app. Read by notebooks / audits.

create table if not exists public.curator_decisions_archive (
  id uuid not null default gen_random_uuid (),
  week_label text not null,                 -- e.g. 'week ending Mon 8 Jun 2026'
  archived_at timestamp with time zone not null default now(),
  url text not null,                        -- denormalised for convenient querying
  decision jsonb not null,                  -- full snapshot of the curator_decisions row
  constraint curator_decisions_archive_pkey primary key (id)
) TABLESPACE pg_default;

create index IF not exists idx_cda_week
  on public.curator_decisions_archive using btree (week_label) TABLESPACE pg_default;

create index IF not exists idx_cda_archived_at
  on public.curator_decisions_archive using btree (archived_at desc) TABLESPACE pg_default;

create index IF not exists idx_cda_url
  on public.curator_decisions_archive using btree (url) TABLESPACE pg_default;
