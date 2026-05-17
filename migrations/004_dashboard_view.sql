-- Migration 004: v_dashboard
-- Read-only joined view of articles + their latest predictions.
-- Dashboard reads from this view. Does NOT include curator_decisions —
-- decisions flow one-way OUT of the dashboard (writes only) and are not displayed back.

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
  c.top1,
  c.top1_confidence,
  c.top2,
  c.top2_confidence,
  c.confidence_gap,
  c.classified_at
from public.articles a
left join public.classify_newsletter c on a.url = c.url;
