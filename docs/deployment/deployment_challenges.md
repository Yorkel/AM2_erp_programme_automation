# Deployment challenges log

A running record of production incidents on the curator dashboard (Streamlit
Cloud) and the scrape pipeline, with root cause and fix. Newest first.

---

## 2026-06-09 — Dashboard stabilisation day (crashes, summaries, body extraction, weekly reset, source filtering)

A long firefighting + hardening session. Multiple issues surfaced together on
the live dashboard, several with **separate** root causes. Captured here in the
order they were diagnosed (A–C in the morning; D–H through the day).

**Changes shipped (summary for write-up):**
- Fixed two dashboard crashes (empty-week `KeyError`; missing-table `APIError`).
- Killed literal "nan" rendering across the UI (shared `clean_text` helper).
- Diagnosed missing summaries as a **body-extraction** problem, not a summariser
  one; replaced the body extractor with **trafilatura** (UCL 61→5,595 chars;
  Schools Week 0→4,146 chars).
- Hardened the summary sweep: retries `"Summary unavailable"` placeholders +
  falls back to `text_clean`.
- Built a **weekly reset** (manual dashboard button *and* a Monday GitHub
  Action) using a non-destructive "week boundary" model.
- Added DfE regulatory-notice **title filtering** ("notice to improve",
  "warning notice") and removed 15 existing such articles from the corpus.
- Added an all-weeks **search box** to Triage (find/coverage-check any article).
- Fixed the **"Other didn't stick"** category bug (Categorise dropdown snapped
  back to the placeholder after a manual pick — the choice was saved but looked
  lost).
- Ingested **newsletter issue #114** (19 items) into the dataset.
- Added an **extractive "topic sentence"** (verbatim lead sentence) alongside the
  abstractive summary — Triage shows the topic sentence (fast to verify), Draft
  shows the editable summary (newsletter copy); both stored (`articles.summary`
  + `articles.topic_sentence`, migration 016). Direct response to Gemma's
  "find a topic sentence ... not write its own" feedback.
- Identified the **leftover Render service** as the source of recurring deploy-
  failure emails (see Issue I).
- **Excel export = EXACT MS-Form format** (14 columns, same order as
  `ERPNewsletterSubmissions.xlsx`) so the download cut-and-pastes straight into
  the form sheet; empty auto-fields are fine. **Submitter column defaults to
  "Dashboard"** so dashboard-found rows are distinguishable from real form
  submissions (Gemma, 2026-06-09).
- **Topic-sentence reliability pass** — verbatim guard (must appear in the body)
  + **title fallback** when there's no clean sentence / no body, so it never
  fabricates or shows "Summary unavailable"; neutral on preambles. Regenerated
  all 821 (verified verbatim-or-title).
- **Status badge** (Pending / Kept / Rejected / Categorised) on Triage cards +
  an all-weeks **search box** with a **Clear** button.
- **URL de-duplication** — normalise at ingest (strip `?_locale=`, `utm_*`,
  trailing slash) so the same article isn't stored twice; cleaned the 1 existing
  duplicate (NEU).
- New **Sources tab** — every source feeding the dashboard with overall +
  last-week counts and a Google-Alert-aware Link column (see Issue K).
- **Removed the manual "Start a new week" button** — resets now run only via the
  Monday GitHub Action, removing an accidental-reset trap (see Issue L).
- **Reset the dashboard clean** for the curators' new week (archive + boundary).

### Issue A — Triage page white-screens with `KeyError: '_article_date'`

**Symptom.** Selecting certain weeks crashed the whole page:

```
File ".../dashboard/pages/triage.py", line 182, in render
    filtered = filtered.sort_values("_article_date", ascending=False, na_position="last")
...
raise KeyError(key)
```

**Root cause.** A pandas indexing footgun, triggered whenever the selected
week had **zero pending articles**. The status filter

```python
filtered = filtered[filtered["url"].apply(lambda u: _status_for(u, decisions) == "Pending")]
```

returns an **empty, non-boolean (str/object) Series** when `filtered` is empty.
pandas interprets a non-boolean indexer as a list of **column labels** to
select, not a row mask. With zero labels it returned a frame with **zero
columns**, dropping the `_article_date` helper column, so the following
`sort_values("_article_date")` raised `KeyError`. Reproduced on pandas 3.0.3
(the Streamlit Cloud runtime).

**Fix.** Force the mask boolean so it stays a row mask even when empty:

```python
filtered = filtered[filtered["url"].apply(
    lambda u: _status_for(u, decisions) == "Pending"
).astype(bool)].copy()
```

Also added (earlier the same day) a defensive `_article_date` creation (handles
a missing `article_date` column from `classify_newsletter` schema drift) and an
empty-`_week_options` guard.

**Lesson.** Never index a DataFrame with the raw result of `.apply()` /
`.map()` when the frame can be empty. Always `.astype(bool)` (or guard
`if df.empty`). An empty object-Series indexer silently means "select zero
columns", not "select zero rows".

### Issue B — UI shows the literal string "nan"

**Symptom.** "Key tags: nan" and summary panes showing "nan".

**Root cause.** pandas null is a **float `NaN`, which is truthy**. The guards
were `value or ""`, and `NaN or ""` evaluates to `NaN` (truthy), so the null
slipped through and `str(NaN)` rendered as "nan".

**Fix.** Added a `_clean()` helper that coerces `None` / float `NaN` /
the string `"nan"` to `""` (and passes lists through), applied to title,
source, date, tags, and summary. Null summaries now render "Summary
unavailable" with a Generate button.

**Lesson.** `x or ""` does **not** catch pandas `NaN`. Use an explicit
`pd.isna()` check for any DB-sourced scalar before display.

### Issue C — Many articles had no summary last week

**Symptom.** Most Belfast Telegraph articles (and some others) had blank
summaries for the week of 26 May - 1 June 2026.

**Root cause.** Upstream enrichment, NOT the dashboard. Body extraction fails
on certain sources (Belfast Telegraph returns 403; plus the other known broken
extractors: UCL IOE News, edtech.oii.ox.ac.uk, Schools Week partial). With no
body text, `summarise_article` correctly stores `NULL` / "Summary unavailable".
Possibly compounded by an unreliable GitHub Actions cron run.

**Status / remediation.**
- Display is fixed (Issue B) so nulls read honestly.
- Recoverable rows backfill via `python -m src.scraping.sweep_summaries`
  (idempotent, last 30 days, needs SUPABASE + ANTHROPIC env).
- Rows that failed body extraction will **not** recover from a re-run; they
  need the source-specific extraction fix first. Tracked separately.

**Concurrency note.** These fixes were authored while another agent (Codex) was
editing the same file. Codex's edits never landed (they stayed in its review
panel); the working tree stayed coherent. Worth flagging that two agents on one
file is a footgun in its own right.

### Issue D — "Fixed" crash still live: stale Streamlit process + repo-rename red herring

**Symptom.** After committing/pushing the Issue A fix, the live app *still*
crashed at the old line. The traceback showed `sort_values` failing at a line
number that, in the fixed code, was the selectbox `help=` text — i.e. the
running process was executing **older bytecode** than the deployed source.

**Root cause.** Streamlit Cloud had not redeployed — it was serving a stale
process from a previous commit. A separate scare: the Streamlit path was
`am2_erp_programme_automation` while local `origin` was
`AM2_erp_programme_automataion` (a typo). This looked like a two-repo split, but
the repo had simply been **renamed** (the Codespace predated the rename) and
GitHub redirects the old URL — it is one repo.

**Fix / lesson.** A **manual reboot** (Manage app → Reboot) forces Streamlit to
pull the latest commit. Lesson: a committed-and-pushed fix is not a *deployed*
fix; confirm the running process actually restarted. Don't infer "wrong repo"
from a path-name mismatch — check for a rename/redirect first.

### Issue E — Missing summaries: the API key was a false lead; body extraction was the real cause

**Symptom.** "All summaries missing" on recent articles.

**Investigation.** The old note blamed a missing `ANTHROPIC_API_KEY` Actions
secret. Verified the key is **valid** (live test call) and **is** wired into the
workflow — that note was stale. Counts: of 836 articles (last 30 days), only ~62
were NULL and ~40 were the `"Summary unavailable"` placeholder; the bulk were
fine. The sweep recovered the NULLs, but ~52 stayed as placeholders.

**Root cause.** For those, there was **nothing summarisable**: Belfast Telegraph
(`text=0`, 403-blocked), UCL IOE (extractor grabbed the **nav menu**), Schools
Week (extractor grabbed a single-paragraph **fragment** / Google-Alert snippet),
DfE gov.uk (body is page **metadata**; real content in a linked PDF). A
`text_clean` fallback in the sweep recovered only ~3 — confirming the problem
was upstream **body extraction**, not the summariser.

**Lesson.** "Summaries missing" is usually a *scraping* symptom. Diagnose by
inspecting the stored `text`, not by re-running the LLM. Stale ops notes (the
key) cost time — verify before trusting.

### Issue F — Body extraction rewritten on trafilatura

**Root cause.** `common.extract_body_text` used a BeautifulSoup heuristic
(`<article>`/`<main>`/`<body>` → `<p>` tags). When the article wasn't in those
containers it fell back to the whole body and scooped up nav/boilerplate (UCL),
or found no usable `<p>` (Schools Week).

**Fix.** Made `trafilatura.extract(str(soup), ...)` the primary path, keeping the
old heuristic as a fallback (no regression for sources that already worked).
Verified end-to-end via the real `soup_of → extract_body_text` path: UCL
61→**5,595** chars, Schools Week 0→**4,146** chars. Forward-looking only —
existing rows need a body-backfill (`backfill_bodies.py`) then a re-sweep.

**Backfill scope (dry-run, 2026-06-09).** Of 83 headline-short articles
(text < 200 chars): **15 are now recoverable** via trafilatura (Schools Week ×6,
UCL ×2, Teacher Tapp, ADES ×4, gov.scot, education-ni) and **68 are unreachable**
— almost entirely **Belfast Telegraph (HTTP 403 at scale)** plus a couple of
`parliament.uk` 403s. This quantifies the hard limit: Belfast Telegraph blocks
automated fetches outright, so those items will keep showing "Summary
unavailable" until a different acquisition route is found (or the source is
dropped). The 15 recoverable rows are fixed by running `backfill_bodies` for
real (it re-summarises in the same pass).

**Lesson.** A purpose-built extractor beats hand-rolled container heuristics for
the long tail of site layouts; gate it behind a length check + heuristic
fallback so a bad parse can't regress a working source.

### Issue G — Weekly reset feature + a self-inflicted crash

**Goal.** Curator asked for last week's kept/categorised items to clear each
Monday. Implemented as a **non-destructive "week boundary"**: a `curator_resets`
row marks "new week started"; Categorise/Draft only show decisions at/after it.
Kept/rejected articles keep their status (don't reappear in Review); pending are
untouched. A snapshot is archived to `curator_decisions_archive` first.
Delivered as both a manual dashboard button and a Monday GitHub Action
(`weekly_reset.py` + `weekly_reset.yml`).

**Self-inflicted crash.** Shipping `get_week_boundary()` before its
`curator_resets` table existed (migration committed but **not run** in Supabase)
took down Categorise + Draft with a PostgREST `APIError`, because the function
runs on every page load. Fixed by wrapping it in try/except → returns "no
boundary" if the table is absent.

**Lessons.** (1) Committing a migration `.sql` file does **not** create the
table — it must be run in Supabase; ship code that degrades gracefully until it
is. (2) The reset button was also hidden by an early `return` when the draft was
empty — reset controls should render regardless of page state.

### Issue H — DfE regulatory-notice noise

**Symptom.** Routine DfE "Notice to improve:" / "warning notice" items cluttered
the corpus and are not newsletter content.

**Fix.** Added both phrases to the title-keyword blocklist (`relevance.py`,
word-boundary match) so they're dropped at scrape time, and removed the 15
existing matches from the corpus (all DfE).

### Issue I — Recurring Render deploy-failure emails after migrating off Render

**Symptom.** Repeated "Render deploy failed" notices, despite the classifier
having been moved to **HuggingFace Spaces** (`CLASSIFIER_API_URL=…hf.space`).

**Root cause.** A **leftover Render service** is still linked to the GitHub repo.
`render.yaml` has `autoDeploy: true` + `branch: main`, so every push to main
triggers a Render redeploy of the old `am2-classifier` service, which fails on
the free tier (the 512 MB OOM previously logged). The pipeline doesn't use it —
it's an orphaned deploy target firing on every push.

**Fix.** Suspend/delete the `am2-classifier` service in the Render dashboard
(definitive). Keep `render.yaml` + `Dockerfile` in the repo as AM2 portfolio
evidence (Docker / IaC story); optionally set `autoDeploy: false` as belt-and-
braces. **Lesson:** when migrating off a platform, retire the connected service,
not just the code path — an orphaned auto-deploy keeps firing (and emailing).

### Issue J — Topic-sentence reliability (verbatim guard + title fallback)

**Symptom.** The first cut of the extractive topic sentence produced sentences
the curator **couldn't find in the article** ("that sentence doesn't exist"),
often pulled the **first/preamble sentence** (e.g. "I have been thinking…"),
and showed bare "Summary unavailable" for blocked sources.

**Root causes.** (1) It summarised from `text_clean` (scraped metadata), which
isn't the article body, so the "quote" wasn't in the article. (2) A prompt rule
to "skip the opening sentence" over-corrected — the curator pointed out
**preambles are sometimes the best line**. (3) No fallback when there was no
real body.

**Fix (iterated with the curator).**
- Extract from the **real body only**, and add a **verbatim guard** — the
  returned sentence must actually appear in the body (normalised match), else
  it's rejected.
- **Fall back to the article title** when there's no body / no clean sentence —
  so it never fabricates and never shows "Summary unavailable" on Triage.
- Prompt made **neutral on preambles** (pick the most representative sentence,
  opening or not).
- Regenerated all **821** topic sentences (cleared the column + re-swept) so the
  fix applied to existing rows, not just new scrapes.

**Lesson.** "Extractive" only means *trustworthy* if you (a) extract from the
real text and (b) verify the output is verbatim. An LLM told to "pick a
sentence" will paraphrase and favour the lead unless constrained + checked.

### Issue K — Sources coverage page (+ a gitignored-roster deploy bug)

**Goal (curator ask).** A page listing every source feeding the dashboard with
article counts — overall and for the last completed week — so coverage gaps are
visible at a glance.

**Design decisions.**
- Counts are **empirical** (grouped from the `articles` table) joined to the
  **live roster** (`data/sources_master.csv`), so approved-but-silent sources
  still appear with 0.
- **Newsletter sources excluded** — they arrive by email (Power Automate), not
  the web scraper, so they're not in `articles` (this is *why* only ~44 of 121
  "live" sources had data; the rest are newsletters, low-volume, or alerts
  stored under publisher domains).
- **Google-Alert entries de-duplicated** — an alert is an ingestion mechanism,
  not a publisher; its content is stored under the real domain, so the alert
  row (e.g. "Rebecca Eynon (Google Alert)") otherwise duplicated the publisher
  with 0 counts. De-duped by base name, keeping the row with articles.
- Week = the **Tue→Mon scrape week** (matches Triage), labelled with dates.

**Deploy bug found + fixed.** On Streamlit Cloud the page first showed only the
~44 producing sources, not the full roster. Cause: `data/` is **gitignored**, so
`sources_master.csv` was never pushed — the runtime read failed and silently
fell back. Fix: a `.gitignore` exception (`data/*` + `!data/sources_master.csv`)
so the roster file deploys. **Lesson:** any data file a deployed app reads at
runtime must be tracked, or the app must degrade visibly (not silently).

### Issue L — Manual "Start a new week" button removed (now fully automated)

Originally shipped both a manual reset button *and* a Monday GitHub Action
(`weekly_reset.py` / `weekly_reset.yml`). Removed the **button** before handover:
it was redundant with the Action and, worse, a curator could click it
**mid-week and reset their own work**. Resets now happen only via the scheduled
Action (Mon 06:17 UTC). **Lesson:** don't leave a destructive manual control in
the UI when the same action is automated — it's an accidental-data-loss trap.

### Curator feedback captured (Gemma, 2026-06-01, from `curator_feedback`)
- "The summary just says **nan**" → **fixed** (Issue B).
- Picked up **press commentary** on the Milburn review, not the review itself;
  curator's own list was longer → recall/coverage gap. Root cause found: the
  Milburn report is a **DWP** publication, outside the monitored education
  sources (noted in open risks; source not yet added).
- Could **not change category** beyond the two AI suggestions; **"Other" didn't
  stick** → **fixed** (Issue, 2026-06-09: dropdown no longer resets after a
  manual pick).
- "Checking the summary is what takes time. Can the AI **find a topic sentence**
  rather than write its own?" → **built** (extractive topic sentence on Triage;
  migration 016).

### Curator feedback captured (Gemma, 2026-06-09, by email — last week's trial)
- **Summary on the include/exclude (Triage) page** was clutter for quick
  keep/reject → **addressed**: Triage now shows the short topic sentence; the
  full summary lives on the Draft page.
- **Excel download didn't match the submission form** → **fixed**: export now
  mirrors `ERPNewsletterSubmissions.xlsx` headings/order exactly. Gemma's reason:
  *"so it's easier to cut and paste — doesn't matter if some cells aren't
  filled."*
- **"Could we use the Submitter column to put Dashboard in?"** → **done**:
  dashboard rows are tagged "Dashboard" in Submitter (distinguishes them from
  real form submissions).
- Topic sentences that **"didn't exist in the article"** / first-sentence /
  preamble issues → **fixed** with a verbatim guard + title fallback + neutral
  prompt; all regenerated.
- Correction logged: Gemma did **not** ask to remove the Submitter/Question
  columns (see [[project-gemma-feedback-2026-05-27]]) — the real ask was the
  exact-format match above.

### Newsletter production workflow + dashboard impact (email thread, 2026-06-09)

Captured from the "Newsletter deadlines" thread (Rachel, Gemma, Nina, Louise)
the evening issue #115 was being laid up. Strong **Project 2 stakeholder
evidence (K21 / S27)** — keep for the write-up.

**Production cadence (now explicit).** Tue evening: Nina lays out the issue.
Weds: Gemma edits/directs; Nina edits Weds evening and sends to Rachel. Thurs:
Rachel proofs; Nina edits and schedules Thurs evening (issue publishes the
following Thurs/Fri). The dashboard feeds the **front** of this pipeline (it
supplies candidate items into the XLS that Nina lays up from). Multi-disciplinary
team: Nina (layout), Gemma (director/editorial), Rachel (proof + gap-filling),
Louise (dashboard + automation + scheduling), SK (LinkedIn promo).

**Concrete impact in the published newsletter.** For issue #115, Gemma judged the
draft gave "too much space to DfE self-promotion" and **used two items from the
dashboard list as late replacements in the Political-environment (PEKO) section**
(visible in the #115 draft as "new entry from dashboard in XLS" and an added
Scottish Government item). Gemma's words: *"She is picking up stuff that Emma W
doesn't see!"* This is the dashboard's output landing in the real published
newsletter, in a stakeholder's own voice — the "impact on the organisation"
evidence the distinction criteria (S27) ask for.

**Stakeholder-driven workflow change.** Rachel and Gemma both found Tuesday-evening
delivery too late ("dealing with it on Tues eve leads to too many amendments for
Nina on Weds"). Agreed fix: **Louise runs the dashboard search and delivers on
Monday night**, so Gemma can update the XLS Monday before Tuesday layout. This is
adapting the process to fit the curators' cadence rather than the pipeline's
convenience (S27), and managing conflicting timescales across the team (K21).
*Implication for a future (post-freeze) update:* the weekly reset (Mon 06:17 UTC)
and scrape (weekdays 02:23 UTC) may need re-timing so fresh results are ready for
a Monday-evening hand-off.

**Recall gap recurred (logged).** The Milburn review was again missed in #115
because it is a **DWP** publication, not DfE, so it is outside the monitored
education sources (see the cross-department source gap in Open risks below). A
real instance of the documented limitation, useful for the honest-evaluation /
ethics notes.

---

## Open / recurring deployment risks

- **Body extraction** — UCL IOE + Schools Week now **fixed** (trafilatura,
  Issue F). Still hard: **Belfast Telegraph** (HTTP 403 at scale — ~68 articles
  unreachable in the 2026-06-09 backfill dry-run, headline only) and **DfE
  gov.uk** (content in linked PDFs). edtech.oii.ox.ac.uk unverified. The 15
  recoverable rows are fixed by running `backfill_bodies`; the Belfast Telegraph
  block needs a different acquisition route or the source dropped.
- **GitHub Actions free-tier cron is unreliable** at peak; overnight/off-peak
  slots fire more reliably. (Scrape now runs weekdays 02:23 UTC; reset Mondays
  06:17 UTC.)
- **`classify_newsletter` schema instability** — the dashboard now guards a
  missing `article_date`, but the underlying schema should be pinned.
- **Migrations are applied by hand in Supabase** — committing the `.sql` does
  not run it. New tables must be created before the code that reads them ships,
  or the code must degrade gracefully (see Issue G).
- **Deploy ≠ push** — Streamlit Cloud can serve a stale process after a push;
  reboot to force a redeploy (Issue D). The repo-rename "two repos" worry is
  **resolved** (one repo, GitHub redirects the old name).
- **Summariser quality (curator feedback)** — generated summaries are slow to
  verify; consider an extractive "topic sentence" option. Recall gap: press
  commentary surfaced instead of the primary source (e.g. Milburn review).
- **Cross-department source gap (noted, not yet actioned)** — the Milburn
  "Young people and work" report was missed because it's published by **DWP**,
  not an education source on the monitored list. Education-relevant reports from
  non-education departments (DWP, HM Treasury, etc.) currently slip through.
  Possible fix later: a targeted DWP/Treasury alert filtered to NEET / young
  people / education so we don't pull in unrelated benefits/pensions content.
- **Weekly drift monitoring is compute-only (design agreed, not built)** — the
  monitor (`s09_monitor.py`) computes drift but does not route, score, diff
  week-over-week, or detect new sources. EDA in `notebooks/11_drift_monitoring.ipynb`
  surfaced junk sources, scraping-quality confounds, a new-source-detection gap, and
  the Four Nations/Wales yield gap. Agreed redesign (data quality shifts left to the
  ingestion gate; monitor observes and routes) is in
  `docs/decisions/monitoring_redesign_2026_06_11.md`. Implementation deferred until
  after the AM2 write-up.
