# Evaluation findings (NB11)

What `11_evaluation.ipynb` shows about the production model's accuracy, calibration and fairness,
after the 2026-06-12 train/serve skew fix. Project 1 evidence. Companion to
`embeddings_and_llm_post_model.md` (why the ceiling exists) and `model_redesign_and_retraining.md`
(what to change). Numbers below are from the corrected re-run (input = title + description, matching
training).

## Headline (held-out test, issues 105-113, n=116, post-cutoff, leakage-free)

| Metric | Value | Reference |
|---|---|---|
| **Macro F1** | **0.725** (bootstrap mean 0.722) | val baseline 0.750 |
| 95% bootstrap CI on macro F1 | **[0.644, 0.796]** | wide because n=116 |
| Weighted F1 | 0.705 | real-world 264-label baseline 0.630 |
| Top-1 accuracy | 0.71 | |
| Top-2 accuracy | 0.879 | val baseline top-2 0.874 |

## The headline story: minimal overfitting, generalisation confirmed
The corrected held-out macro F1 (**0.725**) sits just below the validation score (0.750) and well inside
the bootstrap CI. So the validation number was **not badly overfit** and the model **generalises** to
newsletters published after the training cutoff. The earlier apparent 0.08 "overfitting gap" was an
artefact of the skew bug, not the model.

The real gap to explain is **held-out 0.705 weighted vs real-world 0.630 weighted**. That is the
**production skew** (training on clean curator descriptions, inferring on crude scraped snippets), not
overfitting. See `model_redesign_and_retraining.md` §6.2.

## The train/serve skew bug (caught and fixed 2026-06-12)
- **Bug:** NB11 originally encoded **title-only** while the model trains on **title + description**.
- **Impact:** depressed every metric. Held-out macro F1 read **0.670**; after the fix it is **0.725**
  (+0.055). The classes that gained most were exactly those that need description context:
  `teacher_rrd` 0.74 → 0.89, `policy_practice_research` 0.46 → 0.59. `four_nations` was unchanged
  (0.90), consistent with it being learned from a lexical signal (nation names), not body context.
- **Interpretation (the pattern):** the *more ambiguous* a category, the more it benefits from extra
  text. Classes where the title alone is enough (four_nations = a country name, edtech = "AI") barely
  move; the fuzzy editorial classes that need context to disambiguate gain the most. Title-only starved
  exactly the classes that most needed the description.
- **Scope:** the same bug was in all three parts (held-out, calibration, fairness); all fixed.
- **Lesson:** EDA the model *inputs* before trusting the metric. A surprising score is a prompt to
  inspect the pipeline, not just the model. (Distinction-grade S9/K14 critical evaluation.)

## Per-class (corrected)

| class | precision | recall | F1 | n | group |
|---|---|---|---|---|---|
| four_nations | 1.00 | 0.81 | **0.90** | 16 | concrete |
| teacher_rrd | 0.85 | 0.94 | **0.89** | 18 | concrete |
| edtech | 0.74 | 0.93 | **0.82** | 15 | concrete |
| what_matters_ed | 0.71 | 0.60 | 0.65 | 25 | editorial |
| policy_practice_research | 0.57 | 0.60 | 0.59 | 20 | editorial |
| political_environment_key_organisations | 0.50 | 0.50 | **0.50** | 22 | editorial |
| **macro avg** | 0.73 | 0.73 | **0.73** | 116 | |
| **weighted avg** | 0.71 | 0.71 | 0.71 | 116 | |

Pattern (robust, corroborated by NB13): the **concrete** classes are strong (0.82-0.90); the
**editorial triangle** is the ceiling (0.50-0.65), with `political_environment_key_organisations`
weakest. This is a label-taxonomy ceiling, not a model weakness (see `embeddings_and_llm_post_model.md`).

## Worked errors — content vs source/frame
The model classifies by what the article is *about* (its content/topic), while the curator's label
often encodes *who published it* or the editorial *frame*. The "errors" cluster exactly where those
two axes disagree. That's not the model being dumb; it's the content genuinely sitting on more than
one axis, and the single label being an editorial choice rather than a content-determined fact.

Evidence (held-out, ≥3-error pairs):
- `House of Commons Library - The pupil premium` → true `political`, predicted `what_matters` — a
  disadvantage *topic* labelled by its Parliament *source*.
- `UK Parliament - Dyscalculia: scientific evidence` → true `political`, predicted `what_matters` —
  SEND topic vs source.
- `Social Mobility Commission - level 2 English and maths` → true `what_matters`, predicted
  `political` — topic vs organisation (the axis flips the other way).
- `Nature - Could agentic AI topple grant-funding systems?` → true `policy`, predicted `edtech` — a
  research-funding piece pulled into edtech by its AI content (a content overlap, distinct from the triangle).

Many of these are *defensible* misclassifications a human would hesitate on. This also ties back to the
no-meta SHAP decision: the model was deliberately stopped from classifying by source-type, so it now
classifies purely by content — and these are exactly the cases where content and source disagree.

## Calibration
- **Overall ECE = 0.168** (10 bins) — not well calibrated by the 0.05 standard. Acceptable for this
  tool because confidence is advisory (curator-in-loop), not used to auto-route.
- **Brier score per class** (lower = better; combines confident + correct): edtech **0.030**,
  four_nations **0.035**, teacher_rrd 0.057, policy 0.077, what_matters 0.086,
  political_environment **0.116** (worst). Same ordering as the F1 story: concrete classes
  well-behaved, the editorial triangle weakest.
- **The model is generally *underconfident*** — on the reliability diagrams most classes sit *above*
  the diagonal (right more often than its probability claims; e.g. what_matters is right ~0.7 when it
  says 0.5). Two reasons: (1) **category overlap** — when an article plausibly fits 2-3 editorial
  classes, the model spreads probability across them, so its top-1 probability is modest even when the
  top-1 is correct; the underconfidence is concentrated in the overlapping classes, not the clean ones;
  (2) **`class_weight="balanced"`** flattens the probability outputs. Underconfident is the *safe*
  direction for a curator tool (it under-claims rather than misleads).
- Production SBERT model is better calibrated than the fine-tuned DistilBERT (which was overconfident).
- *Caveat:* per-class reliability curves are noisy at this n (few samples per bin) — read the ECE/Brier
  summary, not the jagged points.

## Statistical rigour
- **Bootstrap CI** reported, not just the point estimate (n=116 makes the interval wide; quote the
  interval).
- **McNemar's test** (no-meta 0.750 vs with-meta 0.765 on val): **p = 0.79**, not significant. So the
  SHAP-driven choice to ship the interpretable no-meta model cost no real F1 — it traded noise for
  interpretability. Strong S9/K14 evidence.
- **Val recompute (Part B) = 0.750** after the fix, matching the training baseline, confirming the
  skew correction is consistent across the notebook.

## Fairness (NB11 Part C + `src/inference/fairness_audit.py`)
"Groups" here are not people — they are **classes, sources, nations and time**. Six lenses run:

- **Algorithmic bias (SHAP recap):** the no-meta model classifies by *content*, not source-type proxy
  (the with-meta model had 27.6% proxy concentration). The deliberate fix for the main bias risk.
- **Per-class disparity:** F1 ranges from **0.50 (political) to 0.90 (four_nations)** — a **~0.30 gap**.
  Honest limitation: the editorial classes are systematically served worse. Not demographic bias, but a
  real per-category performance disparity. Per-class 95% CIs are **wide and overlap** for the editorial
  trio (policy [0.47, 0.77], political [0.44, 0.75], what_matters [0.55, 0.81]) — at this n we can't even
  cleanly rank them, consistent with them being a muddle rather than three distinct things.
- **Per-source / per-nation:** audits implemented (four_nations only ~0.4% of pulled articles; flagged).
- **Fairness over time (Part 5):** two things to separate here.
  - **The ranking is stable:** every week the high-confidence classes (edtech, four_nations) stay high
    and the low ones (political, policy) stay low — that's structural class separability, not drift.
  - **The within-class numbers *wobble*** (e.g. teacher_rrd 0.32 → 0.56 → 0.41 → 0.42). The **model is
    frozen**, so this is not the model shifting — it reflects **which articles landed in that class that
    week**. Three drivers: (1) **article mix** — some weeks a class catches clear-cut, prototypical
    items (high confidence), other weeks borderline ones (low); (2) **small n per week** — each
    week-class cell is only a handful of articles, so the mean swings on noise (probably the biggest
    factor at this sample size); (3) **topic shift** — genuine changes in the news make articles less
    prototypical, real but folded into (1) and impossible to isolate from only 4 noisy weeks.
  - To actually attribute it to topic shift you'd need more weeks, the per-week counts, and a sustained
    trend (not random up-down). That is what **NB12 drift monitoring** is built to test.
  - Caveat: this is a **confidence proxy, not accuracy** (curator labels weren't available) — so "stable
    behaviour", not "stable accuracy".
- **Curator-override rate (Part 6):** framework in place to flag which classes/sources curators correct
  most. Currently **data-light** (decisions accumulate over time; the table is sparse, not wiped — the
  weekly reset is non-destructive and archives to `curator_decisions_archive`). Signal grows with use.

## What can / cannot be claimed
- **Can:** first leakage-free macro F1 with its CI; that the model generalises (held-out ≈ val);
  per-issue temporal stability across 9 weeks; that no-meta vs with-meta is statistically a tie.
- **Cannot:** quote a bare point estimate (use the CI); make strong per-class claims at small n;
  treat held-out as identical conditions to real-world (production snippet skew lowers real-world).

## AM2 criteria
K19 / S12 (evaluation methods), K20 (fairness/bias), S24 (drift/monitoring inputs), S9 / K14
(critical evaluation: the skew bug, the McNemar tie, the honest CI).

---
Related: `embeddings_and_llm_post_model.md`, `model_redesign_and_retraining.md`,
`monitoring_redesign_2026_06_11.md`; NB11 (this), NB13 (separability), NB14 (LLM comparison).
