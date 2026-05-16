-- 001_articles_topics.sql
-- Schema for the in-house scraping pipeline.
--
-- Two tables:
--   articles_topics  -- scraped articles awaiting classification (read by s07_pull_supabase)
--   scrape_runs      -- one row per source per run, for monitoring/eval
--
-- Column names in articles_topics are chosen to match what
-- src/inference/s07_pull_supabase.py already SELECTs, so the inference
-- pipeline keeps working unchanged once we cut over from atlas-ed-data.

create extension if not exists "pgcrypto";

-- ----------------------------------------------------------------
-- articles_topics
-- ----------------------------------------------------------------
create table if not exists articles_topics (
    id              uuid        primary key default gen_random_uuid(),
    url             text        not null unique,
    title           text,
    article_date    date,
    source          text        not null,         -- short code, e.g. 'gov_uk_education'
    source_type     text        not null,         -- 'web' | 'newsletter' | 'rss'
    text            text,                         -- full article body
    text_clean      text,                         -- title + first ~80 words (model input)
    country         text        default 'eng',    -- kept for backwards compat with s07_pull
    dataset_type    text        default 'inference',
    week_number     int,
    scraped_at      timestamptz not null default now(),
    classification_status text  default 'pending' -- 'pending' | 'classified' | 'failed'
);

create index if not exists idx_articles_topics_date    on articles_topics (article_date);
create index if not exists idx_articles_topics_source  on articles_topics (source);
create index if not exists idx_articles_topics_status  on articles_topics (classification_status);
create index if not exists idx_articles_topics_country_dataset on articles_topics (country, dataset_type);

-- ----------------------------------------------------------------
-- scrape_runs  (monitoring; one row per source per run)
-- ----------------------------------------------------------------
create table if not exists scrape_runs (
    id              uuid        primary key default gen_random_uuid(),
    run_id          text        not null,         -- groups all sources from one orchestrator run
    source          text        not null,
    source_type     text        not null,
    since_date      date,
    until_date      date,
    started_at      timestamptz not null default now(),
    finished_at     timestamptz,
    rows_scraped    int,
    rows_upserted   int,
    status          text        not null,         -- 'ok' | 'partial' | 'failed'
    error           text
);

create index if not exists idx_scrape_runs_run_id  on scrape_runs (run_id);
create index if not exists idx_scrape_runs_source  on scrape_runs (source);
create index if not exists idx_scrape_runs_started on scrape_runs (started_at desc);
