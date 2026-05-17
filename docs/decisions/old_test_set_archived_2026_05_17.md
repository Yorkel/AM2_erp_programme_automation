# Old test set archived — 2026-05-17

## What it was

- `data/modelling/manual_labelling.csv` (231 rows) — articles from the OLD atlas-ed-data inference pipeline (pre-cutover, Jan–Apr 2026), hand-labelled by the user as ground truth.
- `data/modelling/weekly/week_1_classified.csv` … `week_14_classified.csv` (~284 rows total) — predictions from a 2026-04-13 inference run, covering only the original 5 in-house scrapers (schoolsweek, gov, fft, fed, epi).
- `data/modelling/weekly/classified_20260517.csv` (66 rows) — duplicate of `classified_articles.csv` (week 18 only).

## Where it lives now

Moved to `data/modelling/_archive/old_test_set/` on 2026-05-17. Not deleted — kept in case useful for reference.

## Why it was archived

- The atlas-ed pipeline has been replaced by the in-house scraping pipeline (cutover 2026-05-16). The test set is no longer representative of the data the model sees in production.
- The April-13 outputs reflect only 5 sources; the current production set has 17+ sources contributing.
- A new test set will be built from curator accept/reject decisions in the live dashboard, accumulating from late May 2026 onwards.

## Metrics recorded against this dataset (training-time evaluation)

| Metric | Value | Source |
|---|---|---|
| Validation macro-F1 | 0.750 | `models/runs/v1_2026-05-16/run_metadata.json` |
| Real-world weighted F1 | 0.630 | same, on 264 manually-labelled atlas-ed articles |
| Real-world top-2 accuracy | 0.874 | same |

These are training-time numbers, recorded when the active model was trained. They are NOT a current production evaluation — they describe how the model performed on the (now archived) atlas-ed-data eval set.

## Caveat — leakage

Within the 231 archived hand-labels, 6 articles overlap with `train.csv` / `val.csv` (URLs published in newsletters #98–104, January–March 2026). The headline metrics above are slightly inflated by these 6 leaked items. Of the 231, 225 are evaluation-clean. See [`project-data-leakage-2026-05-17` memory] for the named URLs.

## Replacement

Rolling test set sourced from curator accept/reject decisions in the dashboard. File: `data/modelling/curator_decisions.json`. Will accumulate from late May 2026 onwards.
