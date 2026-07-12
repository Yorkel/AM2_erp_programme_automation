-- Migration 003: curator_decisions
-- Stores curator's accept/reject decisions per article. One row per URL — latest decision wins (upsert).
-- Foreign key to articles(url) ensures referential integrity.
-- Written by the dashboard; read by analysis notebooks via the supabase-py client. NOT read back into the dashboard.

create table if not exists public.curator_decisions (
  id uuid not null default gen_random_uuid (),
  url text not null,
  action text not null,        -- 'accept_top1', 'accept_top2', 'reject', 'custom_label'
  label text null,              -- the class chosen (top1, top2, or a custom category)
  decided_at timestamp with time zone not null default now(),
  notes text null,
  constraint curator_decisions_pkey primary key (id),
  constraint curator_decisions_url_key unique (url),
  constraint curator_decisions_url_fkey foreign key (url)
    references public.articles (url) on delete cascade
) TABLESPACE pg_default;

create index IF not exists idx_curator_decisions_url
  on public.curator_decisions using btree (url) TABLESPACE pg_default;

create index IF not exists idx_curator_decisions_action
  on public.curator_decisions using btree (action) TABLESPACE pg_default;

create index IF not exists idx_curator_decisions_label
  on public.curator_decisions using btree (label) TABLESPACE pg_default;

create index IF not exists idx_curator_decisions_decided_at
  on public.curator_decisions using btree (decided_at desc) TABLESPACE pg_default;
