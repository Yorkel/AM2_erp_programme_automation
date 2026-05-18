-- Migration 010: persist newsletter picks + category overrides
-- The Organise page lets the curator (a) shortlist accepted articles for the
-- next newsletter and (b) move articles between categories. Both were stored
-- in `st.session_state` only — wiped when the session ends. Now persisted
-- alongside the existing decision row (one row per URL).

alter table public.curator_decisions
  add column if not exists selected_for_newsletter      boolean not null default false,
  add column if not exists newsletter_category_override text    null;

-- Partial index — most rows will be false, only ~10s will be true at any
-- given time, so a predicate index keeps the dashboard's "selected" query fast.
create index if not exists idx_curator_decisions_selected
  on public.curator_decisions using btree (selected_for_newsletter)
  tablespace pg_default
  where selected_for_newsletter = true;
