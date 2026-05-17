-- Migration 006: add scoring columns to classify_newsletter
-- Adds output of src/inference/scoring.py (cluster-id + 4 component scores +
-- composite). All NULL-able so old rows survive; new rows from `scoring` step
-- populate them per pipeline run.

alter table public.classify_newsletter
  add column if not exists cluster_id        integer  null,
  add column if not exists cluster_size      integer  null,
  add column if not exists is_cluster_lead   boolean  null,
  add column if not exists source_authority  numeric  null,
  add column if not exists recency_score     numeric  null,
  add column if not exists substance_score   numeric  null,
  add column if not exists composite_score   numeric  null;

create index if not exists idx_classify_newsletter_composite_score
  on public.classify_newsletter using btree (composite_score desc) tablespace pg_default;

create index if not exists idx_classify_newsletter_cluster_id
  on public.classify_newsletter using btree (cluster_id) tablespace pg_default;

-- ─── Update v_dashboard to surface the scoring columns ─────────────────────
-- Re-create the view (CREATE OR REPLACE) so dashboard reads pick up the new
-- columns. Order kept stable for any pinned client-side column references.

create or replace view public.v_dashboard as
select
  a.id              as article_id,
  a.url,
  a.title,
  a.text_clean,
  a.source,
  a.source_type,
  a.article_date,
  a.week_number,
  a.country,
  a.scraped_at,
  -- prediction
  c.top1,
  c.top1_confidence,
  c.top2,
  c.top2_confidence,
  c.confidence_gap,
  c.classified_at,
  -- scoring (added by migration 006)
  c.cluster_id,
  c.cluster_size,
  c.is_cluster_lead,
  c.source_authority,
  c.recency_score,
  c.substance_score,
  c.composite_score
from public.articles a
left join public.classify_newsletter c on a.url = c.url;
