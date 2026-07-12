# Datasheet — ESRC ERP Newsletter Training Dataset

Following "Datasheets for Datasets" (Gebru et al., 2021). Governance artefact for
the data behind the section classifier. Pairs with `docs/model_card.md`.

## Motivation
- **Why created:** to train a classifier that suggests a newsletter section for
  each candidate article, to assist curators triaging the weekly ESRC Education
  Research Programme (ERP) newsletter.
- **Created by / for:** Louise Yorke, for the ERP newsletter pipeline (UCL IOE).

## Composition
- **Instances:** published newsletter items, each = one article with the section
  it appeared under. The v1 modelling snapshot is **1,109 labelled items**
  (942 train / 167 validation, stratified 85/15). The dataset is a **split of a
  continuously-updated corpus** — the full labelled set grows as new newsletter
  issues publish, and v1 was trained on a snapshot.
- **Label (`target`):** the newsletter **section** the item was published in —
  the curators' own historical editorial decision. These are gold labels but
  **editorial, not objective**: an item can legitimately fit several sections,
  which is why the classes overlap.
- **Classes (6):** political_environment_key_organisations (203),
  what_matters_ed (167), teacher_rrd (165), edtech (149),
  policy_practice_research (136), four_nations (122) — counts from train.
  Mild imbalance (~1.7:1), handled with balanced class weights.
  (Two further newsletter sections, `update_from_pi` / `update_from_programme`,
  are human-only and not modelled.)
- **Features:** `text` (at training time this was title + the **full** newsletter
  description, up to ~815 words; inference truncates to a ~80-word snippet, so there is
  a **known train/serve skew** — the shapes do NOT match, which contributes to the
  production weighted-F1 of 0.630 vs val 0.750),
  plus metadata kept for analysis but **not used by the production model**
  (`organisation`, `org_broad_category`, `issue_date`, `link`).
- **Coverage:** issues 1–104, **Oct 2023 → May 2025**; ~173 distinct
  organisations.

## Collection process
- **How:** extracted programmatically from the published newsletters via
  `src/training_data/s00_extract_newsletters.py`.
- **Source type:** content already in the public domain (published newsletters /
  the organisations' own public outputs). No personal data collected.
- **Labels:** derived from where each item was actually published — no separate
  annotation exercise, so labels carry the curators' editorial framing (a known
  source of label bias / the permeable-category effect).

## Preprocessing / cleaning / labelling
- `s01_clean.py`: encoding repair (ftfy), Unicode normalisation, multi-pass
  deduplication, entity/whitespace cleanup.
- `s02_preprocess.py`: theme normalisation (collapsing ~68 historical labels to
  the 6 production classes), snippet construction.
- `s03_split.py`: stratified 85/15 train/val, seed 42; held-out test uses later,
  unseen issues (105–114) to prevent leakage.
- Known minor leakage (6 URLs train/val ↔ backfill) documented in project notes.

## Uses
- **Used for:** training + validating the section classifier; held-out and
  production evaluation.
- **Should NOT be used for:** treating the section labels as objective ground
  truth, or training a quality/importance judge — the labels encode editorial
  selection, not item quality.

## Distribution
- **Internal**, not publicly released. Derived from public-domain content. The
  anonymised case is described in the FAccT paper (`paper/`).

## Maintenance
- Versioned with the model run (`models/runs/<id>/`). Train/val CSVs under
  `data/modelling/`. Retraining will extend coverage to later issues.

## Known biases & limitations
- **Editorial label bias:** labels are curator placement decisions; categories
  are permeable (items shift between sections by editorial need) — confirmed by
  the Director's feedback (June 2026).
- **Representation skew:** some sources (e.g. Schools Week) dominate; Four
  Nations / Wales are under-represented.
- **Temporal:** Oct 2023 → May 2025; concept/representation may drift as the
  newsletter and source roster evolve (monitored via `s09_monitor` / NB12).
- **Class imbalance:** ~1.7:1 most-to-least frequent class.
