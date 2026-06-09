-- Migration 015: curator_resets
-- Records each "Start a new week" reset on the curator dashboard. The most
-- recent reset_at is the WEEK BOUNDARY: Categorise + Draft only show curator
-- decisions made at/after it, so last week's kept/categorised articles drop
-- out of those pages for a fresh week. Non-destructive — curator_decisions
-- rows are never deleted, so kept/rejected articles keep their status and do
-- NOT reappear in Review; un-actioned (pending) articles are untouched.
--
-- Append-only log. To undo a reset, delete its row (the boundary falls back to
-- the previous reset, or to "show everything" if none remain).

create table public.curator_resets (
  id uuid not null default gen_random_uuid (),
  reset_at timestamp with time zone not null default now(),
  week_label text not null,                 -- e.g. 'week up to Mon 08 Jun 2026'
  n_archived integer not null default 0,    -- decisions snapshotted at this reset
  constraint curator_resets_pkey primary key (id)
) TABLESPACE pg_default;

create index IF not exists idx_curator_resets_reset_at
  on public.curator_resets using btree (reset_at desc) TABLESPACE pg_default;
