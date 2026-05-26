-- Migration 012: pre-generated Claude summaries on articles
-- Purpose: store an LLM summary on each article at scrape time so curators
-- see summaries instantly on Triage / Select Categories / Draft pages,
-- instead of waiting ~5–10s for on-demand generation.
--
-- Display fallback order (in pages):
--   curator_decisions.summary  (if curator edited)
--   articles.summary           (pre-generated at scrape time)
--   ""                         (empty — Generate Summary button still available)
--
-- Cost: ~$0.04 per ~100 articles per weekly scrape (Claude Haiku 4.5 with prompt caching).

-- 1. Add the two new columns. Both nullable so existing 846 articles get NULL
--    (no summary yet) — next scrape will populate going forward, and the
--    Triage page treats NULL as "no pre-gen summary, click Generate to make one".
alter table public.articles
  add column if not exists summary text,
  add column if not exists summary_generated_at timestamp with time zone;

-- 2. Refresh v_dashboard to expose the new column to the dashboard reader.
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
  a.summary,                         -- NEW
  a.summary_generated_at,            -- NEW
  c.top1,
  c.top1_confidence,
  c.top2,
  c.top2_confidence,
  c.confidence_gap,
  c.classified_at
from public.articles a
left join public.classify_newsletter c on a.url = c.url;
