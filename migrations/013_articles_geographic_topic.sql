-- Migration 013: geographic_focus + topic_tags on articles
-- Purpose: enable curator filtering / surfacing in the dashboard by
-- (a) which UK nation an article is about, (b) finer-grained topic tags
-- below the 6 newsletter sections (e.g. "send", "raac", "ai-in-classrooms").
--
-- Values populated by Claude at scrape time (post-summary) — same call
-- gives summary + geographic_focus + topic_tags in one go. Backfilled
-- via scripts/backfill_enrichment.py for existing articles.

-- 1. Add columns. Both nullable so existing rows survive.
--    topic_tags is a text array (PostgreSQL native) so we can filter on
--    array containment from the dashboard later if needed.
alter table public.articles
  add column if not exists geographic_focus text,
  add column if not exists topic_tags text[];

-- Optional: GIN index on topic_tags for fast array containment queries.
-- Useful once the dashboard exposes "filter by topic" — cheap to add now.
create index if not exists idx_articles_topic_tags
  on public.articles using gin (topic_tags);

-- 2. Refresh v_dashboard to expose the new columns (appended at the end,
--    after summary/summary_generated_at — CREATE OR REPLACE can only append).
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
  -- prediction (migration 004)
  c.top1,
  c.top1_confidence,
  c.top2,
  c.top2_confidence,
  c.confidence_gap,
  c.classified_at,
  -- scoring (migration 006)
  c.cluster_id,
  c.cluster_size,
  c.is_cluster_lead,
  c.source_authority,
  c.recency_score,
  c.substance_score,
  c.composite_score,
  -- summary (migration 012)
  a.summary,
  a.summary_generated_at,
  -- enrichment (migration 013, this file)
  a.geographic_focus,
  a.topic_tags
from public.articles a
left join public.classify_newsletter c on a.url = c.url;
