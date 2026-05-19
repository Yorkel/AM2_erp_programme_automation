# Newsletter pipeline template

This folder is a **ready-to-fork starting point** for a new newsletter topic
(e.g. AI governance, climate policy, anything else). It's the ERP newsletter
pipeline with the classifier stripped out — what's left is generic newsletter
infrastructure: scraping, dashboard, curator decisions, daily backup.

For the full step-by-step on how to spin up a new topic, see
[`../docs/new_topic_template.md`](../docs/new_topic_template.md).

## Quick start

```bash
# 1. Copy this folder's contents into a fresh GitHub repo
cp -r repoexport/. /path/to/new-repo/
cd /path/to/new-repo
git init && git add -A && git commit -m "initial commit from newsletter template"

# 2. Push to GitHub (you've created the empty repo already)
git remote add origin git@github.com:<you>/<new-repo>.git
git push -u origin main

# 3. Configure the per-topic files (see "Per-topic configuration" below)
# 4. Provision Supabase + apply migrations
# 5. Configure GitHub Actions secrets (SUPABASE_URL, SUPABASE_SERVICE_KEY)
# 6. Deploy dashboard to Streamlit Cloud
```

## What's included

```
.
├── .github/workflows/
│   ├── scrape.yml       # daily Mon-Fri 02:23 UTC; manual trigger available
│   └── backup.yml       # daily DB backup → CSVs committed to /backups
├── dashboard/           # Streamlit app
│   ├── app.py
│   ├── config.py        # ← edit: replace CATEGORY_* with your buckets
│   ├── data.py
│   └── pages/
│       ├── about.py     # ← edit: replace placeholder copy
│       ├── add_article.py
│       ├── draft.py
│       ├── feedback.py
│       ├── organise.py
│       ├── overview.py
│       └── review.py
├── migrations/          # apply to Supabase in numeric order
│   ├── 001_articles_topics.sql
│   ├── 003_curator_decisions.sql
│   ├── 004_dashboard_view.sql           # template variant — no classifier JOIN
│   ├── 007_curator_decisions_summary.sql
│   ├── 008_curator_feedback_and_source_suggestions.sql
│   ├── 010_curator_decisions_newsletter_picks.sql
│   └── 011_curator_feedback_name.sql
├── src/scraping/        # scraping pipeline (mostly topic-agnostic)
│   ├── sources.yml      # ← edit: replace example entries with your sources
│   └── ...
└── requirements.txt
```

## Per-topic configuration

Files you'll always edit for a new topic:

| File | What to change |
|---|---|
| `src/scraping/sources.yml` | Replace example sources with real RSS feeds and Google Alerts |
| `dashboard/config.py` | Set `CATEGORY_LABELS`, `CATEGORY_ORDER`, `SOURCE_LABELS` |
| `dashboard/pages/about.py` | Replace `[YOUR TOPIC HERE]` placeholders |
| `dashboard/erp_logo.png` | Replace with your project logo (or delete + remove the reference in `app.py`) |
| `README.md` | Topic-specific README at the new repo root |

## What's NOT included (and why)

Everything classifier-related from the original ERP repo:
- `src/training/`, `src/inference/` (model training + inference code)
- `models/runs/` (trained model artifacts)
- `experiments/` (R&D notebooks)
- `.github/workflows/classify.yml`, `drift.yml`, `fairness.yml`
- `migrations/002`, `005`, `006`, `009` (classify/drift/fairness tables)

If you decide later that you do want a classifier for the new topic,
copy those pieces back from the ERP repo. The dashboard already has hooks
for `top1`, `top2`, `confidence` fields — they're just NULL in the template
variant of `v_dashboard`.

## Known things you'll need to do after copying

1. `dashboard/pages/organise.py` and `draft.py` still reference category
   bucketing. If you keep categories (i.e. set `CATEGORY_LABELS`), they work
   as-is. If you skip categories, both pages need simplifying — likely a
   single "selected for newsletter" flag instead of per-category grouping.
2. `dashboard/pages/review.py` has "Category 1 / Category 2" accept buttons.
   With NULL top1/top2 from the template's `v_dashboard`, those buttons will
   show empty labels. Either:
   - Configure a classifier (advanced) and populate `classify_newsletter`
   - Strip the top1/top2 buttons and leave just a single "Accept" button
3. `dashboard/data.py:91-95` references an `authenticated` session-state flag.
   If you don't want password-gated curator auth, simplify `is_authenticated`
   to `return True` and remove the login widget from `app.py`.
