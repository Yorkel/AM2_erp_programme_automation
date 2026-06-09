-- Migration 016: articles.topic_sentence
-- Stores an EXTRACTIVE lead sentence (copied verbatim from the article) separate
-- from the abstractive a.summary. Curator feedback (Gemma, 2026-06-01): a verbatim
-- sentence is faster to trust than an AI-written summary. Design:
--   - Triage page shows topic_sentence (fast keep/reject verification)
--   - Draft page shows summary (the polished newsletter copy)
-- Both are stored so each page can show the form that suits it.

alter table public.articles
  add column if not exists topic_sentence text,
  add column if not exists topic_sentence_generated_at timestamp with time zone;

-- Recreate the dashboard view to expose topic_sentence (mirrors migration 013,
-- + the new column).
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
  -- enrichment (migration 013)
  a.geographic_focus,
  a.topic_tags,
  -- extractive lead sentence (migration 016, this file)
  a.topic_sentence,
  a.topic_sentence_generated_at
from public.articles a
left join public.classify_newsletter c on a.url = c.url;
