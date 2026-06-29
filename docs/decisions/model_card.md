# Model Card — ESRC ERP Newsletter Section Classifier

Governance artefact for the production model. Factual record assembled from
`models/runs/v1_2026-05-16/run_metadata.json`, the evaluation notebooks (NB11,
NB14), and the decision records in `docs/decisions/`.

## Model details
- **Name / version:** ESRC ERP newsletter section classifier, `v1_2026-05-16`
  (the live version is pinned in `models/runs/active.txt`).
- **Type:** Sentence-BERT embeddings (`sentence-transformers/all-MiniLM-L6-v2`,
  frozen) + scikit-learn `LogisticRegression` (`class_weight="balanced"`).
- **Variant:** `sbert_no_meta` — **no metadata features**. The with-metadata
  variant was rejected after SHAP analysis (NB09) showed it classified by
  source-type rather than content (proxy concentration 27.6%); the no-meta model
  is slightly lower on validation (0.765 → 0.750 macro F1) but robust to new
  sources.
- **Alternatives considered:** sbert_with_meta, TF-IDF + LogReg, fine-tuned
  DistilBERT, Claude zero/few-shot (see NB03–09, `model_redesign_and_retraining.md`).
- **Owner:** Louise Yorke (UCL IOE / ESRC ERP).

## Intended use
- **Primary:** suggest a newsletter section for each scraped article to help
  curators triage a weekly list. Outputs the **top-2** sections with confidence.
- **Users:** the ERP newsletter curators (Gemma, Rachel, Nina), via the dashboard.
- **Human-in-the-loop by design:** the model *proposes*; curators *decide*. It is
  an assistive triage tool, not an autonomous classifier.

## Out of scope
- **Not** for autonomous publishing decisions or final section placement —
  placement is an editorial judgement (categories are permeable; see datasheet).
- **Not** a quality/relevance/importance assessor — it finds and labels, it does
  not judge whether an item is worth publishing.
- **Not** validated outside UK schools/pre-HE/FE education content.

## Training data
- Source: **ESRC ERP newsletters, issues 1–104** (Oct 2023 → May 2025).
- Labels: the **section each item was actually published under** — i.e. the
  curators' own historical editorial decisions (gold labels, but editorial not
  objective — this is why some classes overlap).
- Size (v1 modelling snapshot): **1,109 labelled items**, split **942 train / 167
  validation**. The overall labelled corpus is **continuously updated** as new
  newsletter issues publish; v1 was trained on a snapshot of it.
- See the **datasheet** (`docs/decisions/datasheet.md`) for full composition.

## Classes
The **model predicts 6 sections**: edtech, four_nations, policy_practice_research,
political_environment_key_organisations, teacher_rrd, what_matters_ed.
The **newsletter has 8 sections** in total: the 6 above plus two that are
**human-only and not modelled** — "Updates from projects & PIs" and updates from
the programme. This is by design: those two are populated by the curators, so the
classifier is deliberately scoped to the 6 it can learn from the published data.

## Metrics
- **Validation macro F1: 0.750** (stratified 85/15 split).
- **Held-out macro F1: 0.725**, bootstrap 95% CI **[0.644, 0.796]** (unseen
  issues 105–113, leakage-free; NB11/NB14). This is the headline, most rigorous
  number.
- **Top-2 accuracy: 0.879** (the model is used as a top-2 suggester).
- **Real-world weighted F1: 0.630** on 264 manually-labelled production articles
  (England, weeks 1–13 2026) — lower than validation, reflecting production
  snippet-vs-description skew.
- **Calibration: ECE 0.168** — under-confident (reliability sits above the
  diagonal). Acceptable because confidence is advisory, not a routing gate.
- Per-class F1 ranges ~0.50 (overlapping editorial classes) to ~0.90 (concrete
  classes). Confusion concentrates in the policy ↔ political ↔ what_matters
  "triangle".

## Limitations
- **Editorial-triangle overlap:** the weakest classes share conceptual ground;
  NB13 suggests this is a label-design ceiling, not model capacity.
- **Representation skew:** Schools Week is over-represented in inputs; Four
  Nations / Wales under-represented.
- **No quality judgement:** strong on discovery/recall, weak on selection/quality
  (curator feedback, June 2026).
- **Production skew:** trained on newsletter descriptions, served on scraped
  snippets.

## Ethical considerations
- **Data:** public web content, no personal data / PII; low GDPR exposure.
- **No protected attributes** in the data (articles, not people); standard
  demographic fairness metrics do not apply — geographic/source fairness is
  audited instead (`fairness_audit.py`, weekly `fairness_log`).
- **Bias mitigation:** no-meta variant removes source-proxy classification;
  human-in-the-loop curation; monthly source-roster review.

## Maintenance & versioning
- Immutable dated run folders under `models/runs/<id>/`; live version pinned in
  `models/runs/active.txt` (git-tracked for audit trail).
- **Rollback:** repoint `active.txt` to a previous run (one line).
- Retrain triggers (≥500 curator decisions, ≥4 weeks, mean confidence <0.40) in
  `model_v1_state_and_retraining_plan.md`.
