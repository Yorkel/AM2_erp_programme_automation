# Dashboard Handoff — `newsletter_dashboard_demo`

> **⚠️ Important framing correction up front.** The brief described this repo
> as a *Next.js + React + FastAPI* dashboard with Supabase, and asked for an
> inventory in order to migrate **back from Streamlit to Next.js**.
>
> **This repo is the Streamlit dashboard.** There is no Next.js, React,
> Supabase, FastAPI client, `package.json`, `tsconfig.json`, `app/` router, or
> `.env.example` anywhere in the tree. The migration *direction* (Streamlit →
> Next.js) is correct, but **this repo is the source, not the destination.**
> The Next.js code presumably lives elsewhere (private main repo
> `AM2_erp_programme_automataion`, or not yet written).
>
> Below is an honest inventory of what is here. Sections that asked for things
> that don't exist (Supabase tables accessed, FastAPI URL, tailwind config,
> etc.) are answered with "not present" plus what the equivalent is in the
> Streamlit code.

---

## 1. Description

A Streamlit app supporting weekly curation of the **ESRC Education Research
Programme (ERP) newsletter**. Curators step through ML-classified articles,
accept/reject, manually add missed items, organise into newsletter sections,
write descriptions, and download a plain-text draft.

- **Users:** ERP newsletter curators (the prod version is described as
  private to programme curators; this repo is an explicit prototype/demo —
  the in-app banner says "This is a prototype dashboard").
- **Stack:** Python 3.12, Streamlit, pandas, numpy, openpyxl,
  python-dotenv. No JS toolchain.
- **Integration with the rest of the system:** *None at runtime.* The
  dashboard reads a single CSV (`data/modelling/classified_articles.csv`)
  that the upstream classification pipeline produces. No Supabase client.
  No HTTP calls to a classifier API. No FastAPI client. The pipeline is
  upstream and offline.

## 2. Current status

- **Deployment:** Designed for **Streamlit Community Cloud**.
  [app.py](app.py) header reads *"Entry point for Streamlit Cloud. Set main
  file path to: app.py"*. Commit `479a2ed` is "streamlit communitiy". URL
  not configured in this repo — if live, it's on `share.streamlit.io`.
- **Usage:** Prototype/demo only. The app shows a banner warning that
  selections are session-only and reset on page close; production is
  described as a future, private version.
- **Last meaningful commit:** `b1d8de9` *"update"* on **2026-04-13** (about
  5 weeks before today). Recent commits are cosmetic ("fix", "clean fork for
  demo", "warning add"). Active development on this fork looks paused.
- **Open issues / TODOs:** `grep -rniE 'TODO|FIXME|XXX|HACK'` over the
  source returns nothing. One known issue is acknowledged in the
  Instructions page copy: *"The model over-predicts 'Teacher recruitment,
  retention & development'."*
- **Auth:** None. No Supabase Auth, NextAuth, Clerk, or any login flow.
  The app is unauthenticated.

## 3. File tree

```
.
├── LICENSE                          MIT, © 2025 Louise Yorke
├── README.md                        User-facing description
├── app.py                           Streamlit Cloud entry point (calls dashboard.app.main)
├── requirements.txt                 streamlit, pandas, numpy, python-dotenv, openpyxl
├── dashboard/                       Main application package
│   ├── __init__.py
│   ├── app.py                       main(): page config, sidebar nav, page router
│   ├── config.py                    Category labels/order/colors, source labels, brand colors
│   ├── data.py                      CSV loader, session-state init, decisions persistence
│   ├── styles.py                    Custom CSS string (ESRC brand)
│   ├── erp_logo.png                 Sidebar logo
│   └── pages/
│       ├── __init__.py
│       ├── about.py                 Landing page describing the workflow
│       ├── instructions.py          Step-by-step weekly workflow guide
│       ├── add_article.py           Form to manually add an article the pipeline missed
│       ├── review.py                Per-week article review (accept top1/top2/manual/reject)
│       ├── organise.py              Group accepted articles by section, pick up to 3 each
│       ├── draft.py                 Newsletter preview + plain-text download
│       ├── sources.py               Static list of monitored / under-review sources
│       └── feedback.py              Form writing to data/modelling/curator_feedback.csv
├── data/
│   └── modelling/
│       └── classified_articles.csv  270 rows, the only data file the dashboard reads
├── .devcontainer/                   Codespaces config (Python 3.12, pip install reqs)
├── .vscode/                         Editor settings
├── .claude/                         Claude Code settings
├── .gitignore                       Standard Python + .env + .vscode etc.
└── .claudeignore
```

There is **no** `package.json`, `tsconfig.json`, `next.config.*`,
`tailwind.config.*`, `vercel.json`, `netlify.toml`, `Dockerfile`,
`.github/workflows/`, `.env.example`, `migrations/`, or `supabase/`.

## 4. Key files

| File | What it does |
|---|---|
| [app.py](app.py) | One-liner: `from dashboard.app import main; main()`. Streamlit Cloud entry. |
| [dashboard/app.py](dashboard/app.py) | Page config (wide layout, logo, sidebar `st.radio` nav), loads CSV once, renders the prototype banner, dispatches to each page module. |
| [dashboard/config.py](dashboard/config.py) | `CATEGORY_LABELS`, `CATEGORY_ORDER`, `CATEGORY_COLORS`, `SOURCE_LABELS`, ESRC brand colors (`NAVY=#0f1e3d`, `TEAL=#44b4a6`, `MID_BLUE=#1d3461`). **Copy these constants verbatim into the Next.js port.** |
| [dashboard/data.py](dashboard/data.py) | `load_classified_articles()` (cached 5min), `init_session_state()`, `save_decisions()` writing to local JSON, `get_accepted_articles()` merging decisions + curator-added rows + category overrides. |
| [dashboard/styles.py](dashboard/styles.py) | Returns a CSS `<style>` block; brand colors, button color coding per kind, sidebar styling. Behaviour to replicate, not code to port. |
| [dashboard/pages/review.py](dashboard/pages/review.py) | The core decision-capture screen — week filter, sort, progress bar, card-per-article with top1/top2/manual/reject buttons + status, decisions export. |
| [dashboard/pages/organise.py](dashboard/pages/organise.py) | Picks (max 3/section), category override via "Move to" dropdown, selections export. |
| [dashboard/pages/draft.py](dashboard/pages/draft.py) | Renders newsletter preview + builds the plain-text download. |
| [dashboard/pages/add_article.py](dashboard/pages/add_article.py) | Form for curator-added articles (stored in `st.session_state.curator_articles`, persisted across reruns but session-scoped). |
| [dashboard/pages/sources.py](dashboard/pages/sources.py) | Hardcoded list of 10 sources with Automated/Under-review status. |
| [dashboard/pages/feedback.py](dashboard/pages/feedback.py) | Submits to `data/modelling/curator_feedback.csv`. |
| [dashboard/pages/about.py](dashboard/pages/about.py), [instructions.py](dashboard/pages/instructions.py) | Static content — useful as copy reference for the Next.js port. |

There are **no** API routes, hooks, Supabase client, or FastAPI client to
list — those concepts don't apply.

## 5. Configuration files

### [requirements.txt](requirements.txt)
```
streamlit
pandas
numpy
python-dotenv
openpyxl
```

### [.devcontainer/devcontainer.json](.devcontainer/devcontainer.json)
```json
{
  "name": "AM2 ERP Newsletter Automation",
  "image": "mcr.microsoft.com/devcontainers/python:3.12",
  "postCreateCommand": "python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && echo 'Run: streamlit run dashboard/app.py'",
  "customizations": {
    "vscode": {
      "extensions": ["ms-python.python", "ms-toolsai.jupyter"],
      "settings": {
        "python.defaultInterpreterPath": "/workspaces/newsletter_dashboard_demo/.venv/bin/python",
        "python.terminal.activateEnvironment": true
      }
    }
  },
  "remoteEnv": { "VIRTUAL_ENV_DISABLE_PROMPT": "1" },
  "forwardPorts": [8888]
}
```

### [.gitignore](.gitignore) — relevant excerpts
```
.venv/
.env
data/
!data/modelling/
!data/modelling/classified_articles.csv
models/
CLAUDE.md
.claude/
```

**Not present in repo** (and therefore can't be pasted): `package.json`,
`tsconfig.json`, `next.config.*`, `tailwind.config.*`, `.env.example`,
`.eslintrc`, `.prettierrc`, `vercel.json`, `netlify.toml`, `Dockerfile`.

## 6. Environment variables

The dashboard **reads no environment variables at runtime.** `python-dotenv`
is in `requirements.txt` but isn't imported anywhere in the source tree
(`grep -r dotenv dashboard/` returns nothing). The data path is the
hard-coded relative `data/modelling/` in [dashboard/config.py:7](dashboard/config.py#L7).

For the Next.js destination, the env vars you'll need to introduce (none
of them exist here yet):

- `NEXT_PUBLIC_SUPABASE_URL` — Supabase project URL (client-side OK).
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` — anon key, used from the browser for
  RLS-gated reads/writes.
- `SUPABASE_SERVICE_ROLE_KEY` — server-only, for any privileged
  write paths (route handlers / server actions). **Never expose to client.**
- `CLASSIFIER_API_URL` — the FastAPI classifier endpoint;
  currently `https://yorkel-erp-classifier.hf.space` (was a Render URL).
  Server-side only unless you specifically want browser → HF calls.
- Auth: nothing wired up today — choose at port time (Supabase Auth is the
  natural fit given the data layer).
- Analytics: none wired up here.

## 7. Data contract

**Today (this repo):** no database. The dashboard reads exactly one file:

| Source | `data/modelling/classified_articles.csv` |
|---|---|
| Columns | `url, title, article_date, source, text_clean, week_number, top1, top1_confidence, top2, top2_confidence, confidence_gap` |
| Mode | Read-only, cached for 300s via `@st.cache_data` |
| Filters | By `week_number` in [review.py](dashboard/pages/review.py); by `url` keyed lookups in [data.py](dashboard/data.py) |
| Sorts | `article_date` (desc/asc) or `source` in review |

Side-effect writes that *do* happen (all to local filesystem, not a DB):

- `data/modelling/curator_decisions.json` — written by `save_decisions()`.
- `data/modelling/curator_feedback.csv` — appended by feedback form.
- `data/modelling/curator_added_articles.csv` — read on init if present;
  the running app keeps curator-added rows in `st.session_state` only.

**Compared to the destination shape you described:**

| Destination | Status in this repo |
|---|---|
| `articles` (renamed from `articles_topics`) | **Not used.** Equivalent fields (`url, title, article_date, source, text_clean, week_number`) live in the single CSV. |
| `classify_newsletter` | **Not used.** Equivalent fields (`top1, top1_confidence, top2, top2_confidence, confidence_gap`) live in the same CSV. |
| `curator_decisions` | **Not used.** Curator decisions are written to a local JSON file keyed by URL with shape `{url: {action, label}}` where action ∈ `accept_top1, accept_top2, manual, reject`. |
| `v_dashboard` (joined view) | **Not used,** but the CSV's column set is essentially this view pre-materialised. |

**Confirmation: the current code does not match the destination table names
or shape.** The Next.js port will need to translate every CSV access into
a Supabase query against `v_dashboard` (reads) and `curator_decisions`
(writes). The action vocabulary above must be preserved.

## 8. Deploy config

- **Streamlit Community Cloud** is the only target referenced. No
  `vercel.json`, `netlify.toml`, `Dockerfile`, or `.github/workflows/`
  exist.
- Build command: implicit (Streamlit Cloud runs
  `pip install -r requirements.txt` then `streamlit run app.py`).
- Python version: **3.12** (from `.devcontainer/devcontainer.json`). No
  Node version, as there's no JS.

## 9. Setup instructions

From a fresh clone:

```bash
git clone https://github.com/Yorkel/newsletter_dashboard_demo
cd newsletter_dashboard_demo
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run dashboard/app.py
```

Or open in the devcontainer / Codespaces — `postCreateCommand` builds the
venv and installs requirements automatically; then run
`streamlit run dashboard/app.py`.

- **Seed data:** `data/modelling/classified_articles.csv` is committed (270
  rows, weeks 1–N). No DB migrations exist.
- **Env file:** not needed. There is no `.env.example` and the code reads
  no environment variables.

## 10. Outstanding work / TODOs

- No `TODO/FIXME/XXX/HACK` markers in the source.
- README has no "Todo / Next steps" section.
- Acknowledged-in-copy issue (Instructions page): the model over-predicts
  `teacher_rrd`; curators should manually shift govt-announcement articles
  to `political_environment_key_organisations`.
- Acknowledged-in-banner limitation: decisions are session-only in the demo
  build. Persistence is the headline gap the Next.js port should close
  (via the `curator_decisions` table).
- Repo has been quiet since 2026-04-13, so any unfinished work is in the
  author's head, not in code comments.

## 11. What to bring back vs leave behind

Since the destination is a **different stack**, "copy verbatim" doesn't
apply. Treat this repo as a **product spec** that drives the Next.js
build:

**Port as data / constants** (copy values, change language):
- `CATEGORY_LABELS`, `CATEGORY_ORDER`, `CATEGORY_COLORS`,
  `SOURCE_LABELS` from [dashboard/config.py](dashboard/config.py) — these
  are the canonical vocabulary and must match the DB enums.
- Brand colors `NAVY / TEAL / MID_BLUE / LIGHT_BLUE` — feed into the
  tailwind theme.
- Decision action vocabulary (`accept_top1`, `accept_top2`, `manual`,
  `reject`) — preserve so historical decisions remain interpretable.
- Static source list in [pages/sources.py](dashboard/pages/sources.py).
- All user-facing copy from [about.py](dashboard/pages/about.py) and
  [instructions.py](dashboard/pages/instructions.py).

**Port as UX spec** (rebuild in React, don't translate code):
- The per-article card with top1 / top2 / manual / reject buttons and
  confidence colour bands (≥0.6 green, ≥0.4 orange, else red) — see
  [review.py:83-84](dashboard/pages/review.py#L83-L84).
- Max-3-per-section pick rule and "Move to..." override flow in
  [organise.py](dashboard/pages/organise.py).
- Plain-text newsletter assembly + footer in [draft.py](dashboard/pages/draft.py).

**Adapt (don't copy):**
- All CSV reads → Supabase `v_dashboard` queries filtered by
  `week_number`.
- `save_decisions()` JSON writes → Supabase upserts into
  `curator_decisions` keyed by article URL.
- Classifier API URL — does not exist in this codebase; introduce
  `CLASSIFIER_API_URL` env var pointing at
  `https://yorkel-erp-classifier.hf.space`.

**Leave behind:**
- `app.py`, `requirements.txt`, `.devcontainer/`, `dashboard/styles.py` —
  Streamlit-specific.
- `data/modelling/classified_articles.csv` — committed sample data; the
  destination should pull live from Supabase.
- Streamlit Community Cloud deploy choice.
