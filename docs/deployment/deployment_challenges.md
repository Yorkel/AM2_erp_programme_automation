# Deployment challenges log

A running record of production incidents on the curator dashboard (Streamlit
Cloud) and the scrape pipeline, with root cause and fix. Newest first.

---

## 2026-06-09 — Triage page crash + "nan" everywhere + missing summaries

Three issues surfaced together on the live dashboard. They had **separate**
root causes.

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

---

## Open / recurring deployment risks

- **Body extraction broken** for Belfast Telegraph (403), UCL IOE News,
  edtech.oii.ox.ac.uk, Schools Week (partial). Produces blank summaries.
- **GitHub Actions free-tier cron is unreliable** at peak; overnight off-peak
  slots fire more reliably.
- **`classify_newsletter` schema instability** — the dashboard now guards a
  missing `article_date`, but the underlying schema should be pinned.
- **Deployed repo name** in the Streamlit path is `am2_erp_programme_automation`
  while the local/origin repo is `AM2_erp_programme_automataion` (typo
  spelling). Confirm which repo Streamlit Cloud actually deploys from before
  assuming a pushed fix is live.
