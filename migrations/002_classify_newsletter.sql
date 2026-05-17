-- Migration 002: classify_newsletter
-- Stores model predictions per article. One row per URL — re-classifying upserts.
-- Foreign key to articles(url) ensures referential integrity.
-- Lean (A2) schema: no duplication of article metadata. Use v_dashboard view to read articles + predictions together.

create table public.classify_newsletter (
  id uuid not null default gen_random_uuid (),
  url text not null,
  top1 text not null,
  top1_confidence numeric not null,
  top2 text null,
  top2_confidence numeric null,
  confidence_gap numeric null,
  classified_at timestamp with time zone not null default now(),
  constraint classify_newsletter_pkey primary key (id),
  constraint classify_newsletter_url_key unique (url),
  constraint classify_newsletter_url_fkey foreign key (url)
    references public.articles (url) on delete cascade
) TABLESPACE pg_default;

create index IF not exists idx_classify_newsletter_url
  on public.classify_newsletter using btree (url) TABLESPACE pg_default;

create index IF not exists idx_classify_newsletter_top1
  on public.classify_newsletter using btree (top1) TABLESPACE pg_default;

create index IF not exists idx_classify_newsletter_classified_at
  on public.classify_newsletter using btree (classified_at desc) TABLESPACE pg_default;
