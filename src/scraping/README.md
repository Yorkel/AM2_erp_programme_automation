# src/scraping/

In-house scraping pipeline. Replaces the external `atlas-ed-data` feed that
used to populate Supabase `articles_topics`. Output flows straight into the
existing inference pipeline ([src/inference/s07_pull_supabase.py](../inference/s07_pull_supabase.py))
unchanged.

## Layout

```
src/scraping/
├── config.py              loads sources.yml
├── sources.yml            registry of every source (web + newsletter + rss)
├── supabase_client.py     get_client + upsert_articles + log_run
├── common.py              Article shape, _http with retries, date helpers, text_clean builder
├── try_source.py          test ONE source, never writes to Supabase
├── run.py                 orchestrator — iterates sources.yml, upserts, logs
├── web/
│   ├── _base.py           scrape_listing() pattern for listing-page-then-articles sites
│   └── <per-site>.py      one module per site (you write these)
└── newsletters/
    ├── parse_html.py      generic inbound-newsletter HTML parser
    ├── from_disk.py       reads data/inbound_newsletters/<source>/*.html
    └── gmail.py           Gmail API ingestion (stub, not implemented)
```

## Data directories

- `data/inbound_newsletters/<source>/YYYY-MM-DD.html` — save inbound newsletters here for the disk path
- `data/scratch/` — `try_source.py --save` writes JSON dumps here
- `data/newsletters_html/` — **NOT** used by this module. That directory contains past ESRC ERP newsletters used as training data ([src/training_data/s00_extract_newsletters.py](../training_data/s00_extract_newsletters.py))

## Adding a new source

### A. Web source

1. Create `src/scraping/web/<name>.py` exposing:
   ```python
   def scrape(source, since_date=None, until_date=None, **kwargs) -> list[Article]:
       ...
   ```
   For listing-then-article sites, build on `web._base.scrape_listing`. For odd ones, write it from scratch.

2. Add an entry to `sources.yml`:
   ```yaml
   - name: my_source
     type: web
     scraper: src.scraping.web.my_source
     params: {}
   ```

3. Iterate with `try_source.py` until the rows look clean:
   ```
   python -m src.scraping.try_source --source my_source --since 2026-05-01 --save
   ```

4. Once happy, leave the entry enabled. The next `run.py` will pick it up.

### B. Newsletter source (disk path)

1. Add to `sources.yml`:
   ```yaml
   - name: wonkhe_newsletter
     type: newsletter
     ingestion: disk
     params: {}
   ```

2. Save an example newsletter as `data/inbound_newsletters/wonkhe_newsletter/2026-05-12.html`.

3. Test:
   ```
   python -m src.scraping.try_source --source wonkhe_newsletter --save
   python -m src.scraping.try_source --html data/inbound_newsletters/wonkhe_newsletter/2026-05-12.html
   ```

4. If `parse_html.parse_newsletter_html` produces too much junk (footers, social links, "click here") for that sender, write a small override module under `src/scraping/newsletters/<name>.py` and point the source at it. Most senders will be fine with the generic parser.

### C. Newsletter source (Gmail path)

Not implemented yet. Use the disk path for now.

## Running

```
# Twice-weekly incremental run (cron path)
python -m src.scraping.run --since 2026-05-12 --until 2026-05-15

# Backfill — same code path, longer --since
python -m src.scraping.run --since 2023-01-01

# Dry run — scrape, print counts, no DB writes
python -m src.scraping.run --since 2026-05-12 --dry-run

# Single source for debugging
python -m src.scraping.run --source wonkhe_newsletter --since 2026-05-12
```

After `run.py`, the existing inference pipeline runs unchanged:

```
python src/pipeline.py --inference
```

## Schema

Apply `migrations/001_articles_topics.sql` to a Supabase project. Sets up:

- `articles_topics` — column names match what `s07_pull_supabase.py` already SELECTs (`url, title, article_date, source, text_clean, week_number`), plus `text` (full body) and `source_type` (`web`/`newsletter`/`rss`).
- `scrape_runs` — one row per source per orchestrator run for monitoring.

## Environment

Needs in `.env`:

```
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_KEY=<service role key>
```

## Build order (where we are)

- [x] Phase 1: foundation (this scaffolding)
- [ ] Phase 2: add sources to `sources.yml`, build/test each with `try_source.py`
- [ ] Phase 3: backfill via `run.py --since <start>`
- [ ] Phase 4: GitHub Actions twice-weekly cron + Gmail API ingestion
- [ ] Phase 5: monitoring/eval dashboards on `scrape_runs`
