# Model v1 state, drift findings, and retraining plan — 2026-05-17

The deployed classifier (`v1_2026-05-16`), what it does well, what's drifting, why we are **deliberately not retraining before the AM2 write-up**, and the roadmap for v2.

## Current state — v1_2026-05-16

| Metric | Value | Source |
|---|---|---|
| Validation macro-F1 | 0.750 | `models/runs/v1_2026-05-16/run_metadata.json` |
| Real-world weighted F1 | 0.630 | 264 hand-labelled articles from atlas-ed-data eval set |
| **Real-world top-2 accuracy** | **0.874** | same eval set |
| Mean top-1 confidence (production) | 0.484 | 854 articles classified 2026-05-17 |
| % below 50% confidence | 62.9% | same run |

**Architecture:** sentence-transformer `all-MiniLM-L6-v2` embeddings + sklearn LogisticRegression (`sbert_no_meta` variant — chosen after SHAP showed the `with_meta` variant classified by source-type instead of content). 6-class single-label.

**Why "good enough":** top-2 accuracy at 87% means for ~87 of 100 articles the correct category is in the model's top 2 picks. Curators are the safety net — they review every prediction in the dashboard, accepting top-1 or top-2 in one click. The design pattern is "model assists, curator decides".

## Confidence is not accuracy — common misconception

Mean confidence of 0.484 does NOT mean the model is wrong 52% of the time.

- Random guess across 6 classes = 16.7% (1/6). 0.484 is nearly 3x baseline.
- "62.9% below 50%" means for 62.9% of articles, the model's top pick has under 50% probability mass. That just describes how the model splits its uncertainty — not how often it's right.
- The model's *accuracy* (top-2 = 87%) is the only number that says "the prediction is correct or not".
- The two metrics measure different things. Both worth tracking; don't conflate.

## Concept drift detected (backfill 2026-05-17)

Three orthogonal signals trend the same direction over the 18-week window Jan 7 → May 12 2026:

| Signal | Jan | May | Change |
|---|---|---|---|
| Mean top-1 confidence | 0.534 | 0.454 | −0.08 |
| % articles with top-1 confidence < 50% | 40.6% | 74.2% | +33.6 pp |
| Mean embedding similarity to training centroids | 0.555 | 0.475 | −0.08 |
| Out-of-distribution flagged per week | 0–1 | 4–6 | +5pp |

Class distribution patterns (vs val baseline):
- `political_environment_key_organisations` consistently **over-predicted** (val 17.4%, prod 31.6%, **+14.3pp**)
- `policy_practice_research` **under-predicted** (val 14.4% → prod 7.5%)
- `teacher_rrd` **under-predicted** (val 21.6% → prod 13.3%)

These match historical news salience (King's Speech, election coverage etc.) so the drift might reflect real news rather than model degradation — caveat applied.

## Decision: do NOT retrain before AM2

Reasons:

1. **No new labelled data yet.** Training on the same data wouldn't help. The curator dashboard (going live this week) is what generates fresh labels — wait for it to accumulate decisions.
2. **Current performance is sufficient for the workflow.** 87% top-2 means curator-side review is one-click for ~87% of articles. Retraining for marginal improvement displaces higher-priority work.
3. **Time-budget against the AM2 deadline (2026-05-31).** Retrain + evaluate + redeploy is days of work; better spent on dashboard, fairness audit, and write-up.
4. **A worse v2 reads badly.** With limited new label data, retraining could *worsen* metrics. Then the portfolio narrative becomes "tried to improve, made it worse". Risk not worth the reward.

## AM2 narrative this enables

> "v1 reached 87% top-2 real-world accuracy. I deployed it via Render (then migrated to Hugging Face Spaces after diagnosing memory constraints), instrumented drift monitoring on three orthogonal signals (confidence, embedding similarity, OOD rate), and confirmed concept drift across the production window. I designed the dashboard to capture curator accept/reject decisions as fresh labels — closing the active-learning loop. The v2 retrain will trigger when N curator decisions have accumulated (proposed: N = 500), allowing me to compare v1 vs v2 fairly on labels neither model has seen at training time."

That single paragraph evidences:

- **K14 / S9** — refinement strategy
- **S9 / K14 distinction** — critical evaluation (admitting drift is real, framing retraining as a data problem not a model problem)
- **S24** — model drift / data drift / performance monitoring
- **S22 / S24 distinction** — robustness via monitoring
- **S25** — decommissioning + lifecycle (defined v2 trigger criteria)

## v2 trigger — when to retrain

Retrain when ALL of:

1. **Label volume:** ≥500 curator decisions accumulated in `curator_decisions` table (mix of accept_top1 / accept_top2 / reject / custom_label)
2. **Time elapsed:** at least 4 weeks since v1 deployed (avoid retraining on noise)
3. **Confidence floor breached:** weekly mean top-1 confidence falls below 0.40 for 2 consecutive weeks (currently 0.45 — close but not over)
4. **Accuracy floor breached** (if labels available): rolling top-2 accuracy from curator decisions falls below 80%

Retrain procedure:

1. Snapshot `articles` + `classify_newsletter` + `curator_decisions` from Supabase
2. Build a fresh training split: existing newsletter items (train.csv/val.csv) + new curator-labelled articles, stratified by source and class
3. Train candidate v2 with same `sbert_no_meta` architecture
4. Compare v1 vs v2 on a held-out slice of curator decisions (which neither model has seen at training time)
5. If v2 wins on top-2 accuracy AND weighted-F1: deploy. Update `models/runs/active.txt` to `v2_<date>`. Redeploy Hugging Face Space.
6. If v2 loses or ties: investigate before deploying. Document.

## Possible improvement options for v2 (or later)

Listed without recommending — to choose from when retrain time arrives.

| Option | Effort | Expected gain on top-2 | Operational cost |
|---|---|---|---|
| Retrain on curator decisions | 1–2 days | Most direct fix for the current drift | Free (uses labels from the dashboard loop) |
| Bigger embedding model (`all-mpnet-base-v2` or `bge-small`) | Half a day | +2–3% accuracy | Slower inference, more RAM, may push HF Space cold-start time |
| Add summary or first-paragraph snippet to `text_clean` (lengthen the input) | Half a day | +2–3% accuracy | None |
| Ensemble with Claude zero-shot for low-confidence cases | 1–2 days | Strong on ambiguous edges | ~$0.01/article via Anthropic API |
| Hard-negative mining + targeted retraining | Days | Specifically helps the top-1 vs top-2 confusion pairs | Needs the confusion data |
| Multi-label rather than single-label | 1–2 weeks | Better fit to articles that span categories | Bigger schema change; need to relabel training data |
| More classes / finer-grained taxonomy | 1–2 weeks | More useful category granularity for newsletter sections | Requires curator-led taxonomy redesign |

## What stays the same when v2 ships

- Data layer (3 tables + view) — unchanged
- Inference pipeline shape (s07 → classify_via_api → fairness_audit → s10) — unchanged
- `active.txt` pointer pattern — same swap mechanism
- Dashboard — unchanged (reads `v_dashboard`, writes `curator_decisions`)

Versioning via `active.txt` means v2 deployment is a 1-line config change + redeploy. The whole pipeline picks it up on the next run.

## Related

- `docs/decisions/data_layer_design.md` — data layer
- `docs/decisions/render_free_tier_memory_limit.md` — deployment platform decision
- `docs/decisions/old_test_set_archived_2026_05_17.md` — what the v1 metrics were measured against
- `models/runs/v1_2026-05-16/run_metadata.json` — model artefact metadata
