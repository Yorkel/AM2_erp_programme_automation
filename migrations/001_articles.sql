-- 001_articles.sql
-- Schema for the in-house scraping pipeline.
--
-- Two tables:
--   articles     -- scraped articles awaiting classification (read by the inference pipeline)
--   scrape_runs  -- one row per source per run, for monitoring/eval
--
-- NOTE: this table was originally created as `articles_topics` and renamed to
-- `articles` in production (2026-05-17). All later migrations (002+) and the
-- application code reference `articles`, so this migration now creates it under
-- the canonical name directly. A fresh apply of migrations 001 -> 016 in order
-- reproduces the production schema with no separate rename step.

create extension if not exists "pgcrypto";

-- ----------------------------------------------------------------
-- articles
-- ----------------------------------------------------------------
create table if not exists articles (
    id              uuid        primary key default gen_random_uuid(),
    url             text        not null unique,
    title           text,
    article_date    date,
    source          text        not null,         -- short code, e.g. 'gov_uk_education'
    source_type     text        not null,         -- 'web' | 'newsletter' | 'rss'
    text            text,                         -- full article body
    text_clean      text,                         -- title + first ~80 words (model input)
    country         text        default 'eng',    -- kept for backwards compat with the inference pull
    dataset_type    text        default 'inference',
    week_number     int,
    scraped_at      timestamptz not null default now(),
    classification_status text  default 'pending' -- 'pending' | 'classified' | 'failed'
);

create index if not exists idx_articles_date    on articles (article_date);
create index if not exists idx_articles_source  on articles (source);
create index if not exists idx_articles_status  on articles (classification_status);
create index if not exists idx_articles_country_dataset on articles (country, dataset_type);

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
