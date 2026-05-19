-- Migration 004 (template variant): v_dashboard
-- Read-only view of articles. The original ERP repo joins on classify_newsletter
-- to add classifier predictions; this template variant drops that join because
-- the template assumes no classifier (curators bucket articles manually).
--
-- The view emits null columns for top1/top2/confidence so dashboard code that
-- references them continues to work — those fields just render as empty.

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
  null::text       as top1,
  null::float      as top1_confidence,
  null::text       as top2,
  null::float      as top2_confidence,
  null::float      as confidence_gap,
  null::timestamptz as classified_at
from public.articles a;
