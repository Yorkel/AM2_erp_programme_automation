# Monitoring redesign: quality gate at ingestion, weekly drift, monthly source review

**Date:** 2026-06-11
**Status:** Process agreed. Parts already exist; the rest is deferred until after the AM2 write-up.
**Trigger:** Building the inference-data EDA in `notebooks/12_drift_monitoring.ipynb`.

## Context

Notebook 11 consolidates the production model's weekly inference output (the
`data/modelling/weekly/classified_week_*.csv` files, ~900 articles over 20 weeks) into a
single ordered EDA covering AM2 criterion S24 (model drift, data drift, performance
monitoring). Working through it surfaced data-quality and coverage issues, and clarified
where quality work should sit relative to inference.

## The agreed process

```
1. Scrape articles
2. Quality gate: blocklist (always) + approved-list / UK-domain check (broad/alert sources)
3. Not approved  -> dropped + logged (url, title, source, reason) to data/archive/rejected/
   Approved      -> written to Supabase
4. Inference (classify + score) runs weekly on the approved set
5. Drift monitoring runs weekly on the approved set, with integrated alerts on anomalies
6. Monthly source-roster review of the rejected log:
      (a) genuinely relevant -> add to APPROVED_DOMAINS  (grows recall)
      (b) junk                -> add to BLOCKED_DOMAINS   (grows precision)
      (c) one-off             -> leave as-is (no action)
```

Two cadences, two purposes: a **fast weekly loop** (drift anomalies) and a **slow monthly
loop** (source-roster grooming). A weekly drift alert about a volume or coverage anomaly can
escalate to an earlier ad-hoc roster review.

### What already exists vs what is to build

| Step | Status |
|------|--------|
| 1 Scrape | Exists (`src/scraping/run.py`) |
| 2 Quality gate (blocklist + approved/keyword) | Exists, **except** the UK-domain rule for alert sources (to build) |
| 3 Drop + log rejected | Exists (`log_rejection` -> `data/archive/rejected/<date>_<source>.csv`) |
| 4 Weekly inference | Exists (`pipeline.py --inference`, `classify.yml`) |
| 5 Weekly drift | Compute exists (`s09_monitor.py`, `drift.yml`); **alert routing to build** |
| 6 Monthly source review | Rejected log exists; **review surface to build** |

## Issues identified through the drift-monitoring work

1. **Junk leaks via Google Alerts (corrected understanding).** The week-20 junk
   (`tvguide.co.uk`, `msn.com`, `e.vnexpress.net`, `smh.com.au`, `news.abplive.com`,
   `instagram.com`, `pressreader.com`, `uk.news.yahoo.com`) was **not** historical pre-gate
   data. It was the most recent week (17-18 May 2026), and it arrived through **Google
   Alerts**: the RSS adapter sets an alert article's `source` to its real domain
   (`_domain_as_source`), which is why the source column shows raw domains. The domains were
   added to `BLOCKED_DOMAINS` the next day (18 May, commits `bffb4e4`, `916b146`) after being
   spotted by hand on the dashboard.

2. **The blocklist is reactive, so alerts are a permanent leak vector.** A Google Alert
   returns articles from arbitrary publishers, so it cannot be allowlisted. It relies on the
   blocklist plus keyword filter, and the blocklist can only stop a domain after it has been
   seen once. The keyword filter does not help here because the junk is on-topic-ish but
   wrong (wrong country or wrong format: "education spending per student", a TV listing).
   The fix is a **domain** rule, not more keywords.

3. **No new-source review surface.** Rejected items are logged to disk but nobody looks at
   them, so the allow/block lists only change when someone happens to notice junk on the
   dashboard. The list is effectively frozen, which is how genuinely relevant new outlets get
   missed (for example the Milburn/DWP report and the Welsh feeds).

4. **The monitor computes but does not route.** `s09_monitor.py` computes distribution shift,
   confidence stats, and embedding drift, and writes a `drift_log` row plus a GitHub Actions
   step summary, but sends no alert. In practice you have to open the Actions tab to see it.

5. **Coverage bias (Four Nations gap).** Wales is roughly 1% of articles. The registry
   configures ~12 Welsh feeds but almost all yield zero; only `wales_centre_for_public_policy`
   produces anything. A yield problem, not a coverage-design gap.

## The fix for the alert leak (step 2)

Add a **UK-domain rule for alert sources**: after extracting the real domain (already done via
`_domain_as_source`), require it to be a UK domain (`.uk`, `.gov.uk`, `.ac.uk`, `.scot`,
`.wales`) or already on `APPROVED_DOMAINS`. Otherwise reject and log to the same rejected file.
This turns the non-UK long tail from per-domain whack-a-mole into one standing rule (it would
have caught all 10 week-20 rows proactively), while genuinely new UK domains land in the
rejected log for the monthly review to promote or block. About 10 lines, reusing what exists.

Stronger alternative if dashboard junk keeps reaching curators: a full **default-deny review
queue** for alert results (unknown domain held, not published, until reviewed). More plumbing;
hold unless the UK-domain rule proves insufficient.

## Drift is computed on the approved set

Because non-approved sources are dropped at step 2, inference and drift only ever see the
approved set. So "drift is on the approved sources only" is already structurally true; the
redesign just makes it explicit and adds alert routing.

## Alert routing (step 5)

Route by severity to avoid alert fatigue: green log-only, amber weekly digest, red active
notification plus a human action. Scale-appropriate delivery (consistent with the decision to
add monitoring signals but skip a heavy Prometheus/Grafana stack): a weekly email digest plus
a GitHub Issue auto-opened on red. Sustained red prompts a retraining decision, which stays
human-gated per `model_v1_state_and_retraining_plan.md`.

## Review cadence (manual review)

Manual review is **scheduled + alert-triggered, never alert-only** — each catches what the
other misses:

- **Weekly (fast loop):** light glance at drift / confidence. Runs *regardless of alerts*, so
  it catches slow drift that never trips a threshold and protects against mis-tuned thresholds.
- **Monthly (slow loop):** deeper review of the rejected-source log (promote / blacklist /
  leave) + fairness + the retrain-trigger checklist.
- **Alert-triggered (event-driven):** when a threshold breaks (drift spike, confidence floor,
  performance drop), investigate immediately.

"Only on alert" trusts the thresholds are perfectly tuned and lets slow degradation slip under
them; "never" is just hoping. The notebook (`12_drift_monitoring.ipynb`) is the human review
surface for both loops — it pulls the raw data (`v_dashboard`) plus the pipeline's computed
logs (`drift_log`, `fairness_log`, rejected archive) and displays them.

## Notebook structure (consolidated 2026-06-11)

Analysis notebooks reduced to two, split by the label rule (*does it use ground-truth labels?*):

- **`12_drift_monitoring.ipynb` — Monitoring** (live stream, no labels): data quality, drift,
  confidence, per-source fairness disparity, retrain-trigger check, relevance-filter analysis
  (folded in from old nb15).
- **`11_evaluation.ipynb` — Evaluation** (labelled test/val set): held-out performance, calibration,
  bootstrap CIs, McNemar, bias & fairness by accuracy. Merged from old nb12 + nb13 + nb14.

`notebooks/01-10` remain as the model-build history. Superseded notebooks are in
`notebooks/_archive/`.

## AM2 framing (S24)

The robust-monitoring story: quality work sits at ingestion (the gate acts), monitoring
observes and routes (weekly), and a monthly human review evolves the allow/block lists. It
demonstrates the full loop (detect, score, route, review, retrain trigger) rather than just
computing a drift number. The week-20 Google-Alerts leak is a concrete worked example of why
the review loop matters.

## Update 2026-06-11 (end of session) — items resolved

- **UK-domain rule for alert sources: NOT built (obsolete).** `src/scraping/run.py::_filter_items`
  already runs a **universal approved-domain allowlist** (`is_approved_domain` — drops anything
  not on `APPROVED_DOMAINS`) plus a **non-UK content veto** (`is_non_uk_content`), both *before*
  any opt-in gate. That is stricter than a UK-domain rule (which would have *loosened* the gate by
  allowing any `.uk`). The week-20 leak predated the allowlist (added 2026-05-18). No change needed.
- **Alert routing: implemented.** `s09_monitor` now prints `MONITOR STATUS: GREEN/AMBER/RED`
  (RED if mean conf <0.40, class-mix shift >15%, or OOD >15%; AMBER on class-mix alerts / >70%
  below-0.5 / OOD >5%). `drift.yml` gained `permissions: issues: write` + an "Open issue on RED"
  step (built-in `GITHUB_TOKEN`, no new secret). **Email digest = remaining choice** (needs an
  SMTP/Resend secret) — left to the user to pick a service.
- **Canonical nation field = `country`.** `country` (deterministic, source-derived via
  `src/scraping/nations.py`; drives the inference filter + fairness + Four Nations coverage) is
  canonical. `geographic_focus` stays a *secondary* article-level descriptor (LLM-derived
  England/Scotland/…/International) — NOT used for filtering or grouping. Do not conflate them.

## NB12 inference-stream EDA findings (2026-06-13)

**Scope:** the live, **unlabelled** production stream (~849 articles, weeks 1-24 of 2026). No accuracy
or F1 here (no ground truth) — this is distribution, confidence and drift signals. Confidence is a
proxy for *certainty*, not correctness.

**Source distribution — heavy concentration.** `schoolsweek` = **338 of ~849 (~40%)**. One source
dominates the stream, so the model's real-world behaviour largely reflects Schools Week content. Long
tail of ~45 sources (gov_scot 71, belfast_telegraph 68 [body-extraction issues], ascl 51, dfe 33…).
Representativeness risk: the newsletter inherits this skew unless balanced at curation.

**Nation distribution — extreme Four Nations imbalance (input side).** England 440, UK-wide/other 241,
Scotland 122, N. Ireland 68, **Wales 3**. By month, N. Ireland grew (0→30→19) while Scotland tailed off.
This is an **input coverage/yield gap** (feeds producing nothing), compounding the model-side four_nations
point and consistent with §5 above.

**Class distribution (top1 over the stream).** political_environment **229**, what_matters 215,
four_nations 135, teacher_rrd 135, edtech 90, **policy_practice_research 45**. `political_environment` is
over-predicted (the diffuse catch-all); `policy_practice_research` is under-predicted.

**Confidence levels — the model hedges.**
- Mean top1 confidence **0.494** (std 0.17). top1 0.494 + top2 0.206 = **0.70**, leaving **0.30 "rest
  mass"** spread across the other four classes.
- Regimes: **40% decisive** (top1 ≥ 0.5), 35% two-horse race, 25% scattered — so 60% of predictions are a
  *plurality*, not a majority.
- Per class: edtech 0.65, four_nations 0.56, teacher 0.51, what_matters 0.47, policy 0.42, political 0.42
  (same ordering as the held-out F1). Per-class regimes: edtech 70% decisive, four_nations 58%; but
  policy 20% / political 23% decisive (51% / 45% two-horse) — the editorial classes are rarely decisive.

**Confidence over time — no trend (flat).** Pearson **r ≈ 0.01** between week and confidence → no
relationship. Week 1 (0.471, n=4, unreliable) vs week 24 (0.547) is **noise, not a trend** — no
confidence drift across the 24 weeks. (Supersedes the older 0.53→0.45 backfill note, a different window.)
The within-class week-to-week wobble is **article mix + small-n noise**, not the model (frozen). The
stable thing is the per-class *ranking*, not the individual weekly numbers.

**top2 / rest-mass — mechanical and meaningful.** top2 is by definition ≤ top1, so "lower confidence on
top2" is structural. The meaningful part is the **0.30 rest mass** = genuine hedging across overlapping
classes.

**"Confusion is general overlap, not error" (top1↔top2 co-occurrence).** `political_environment` is the
model's **universal second guess**: what_matters→political **139**, four_nations→political 62,
teacher→political 60, edtech→political 48. As the broadest/most-diffuse class it is the default fallback.
The heavy top1/top2 pairs (what_matters↔political, four_nations↔political) trace **genuine semantic
adjacency**, not random error — the label-taxonomy-ceiling story seen from the probability side.

**Confidence × class × week heatmap** (`outputs/drift_confidence_heatmap.png`). A grid — rows = class,
columns = week, green = confident, red = unsure — showing *where* uncertainty concentrates. Read across a
row (a class over time: steady colour = stable, green→red = drift) and down a column (one week). Expect
edtech/four_nations green, policy/political red; a row drifting green→red would be a confidence-drift signal.

**Caveats.** Unlabelled (confidence ≠ accuracy); small n per week-cell = noisy; schoolsweek dominance
skews every distribution above.

### Drift synthesis (§9): model vs data vs concept drift

**Three drifts, and only one is directly visible without labels:**
- **Data / covariate drift** (the *input* distribution changes) — **measurable here**: volume 4→~100/wk,
  schoolsweek 40%, nation mix shifting, class-mix. Present, but system-driven (see below).
- **Concept drift** (the *X→label* relationship changes) — **not measurable without labels**; only
  *proxied* by confidence / OOD. Proxies are flat (confidence r≈0.01) → no signal.
- **Model / performance drift** (accuracy degrades) — **not measurable on the live stream**; the only
  true read is the NB11 held-out snapshot (0.725 ≈ val 0.75 → still generalising).

Principle for the write-up: on an unlabelled stream you can only directly see **data** drift; concept and
performance drift you must **proxy** (confidence, OOD) or catch with **periodic re-labelling**.

**How they interact + the cohort trick.** Data drift is the *cause*; concept/performance drift the *effect
you can't see*, so visible data drift + confidence/OOD act as **early warnings**. Crucially, volume grew
because **new sources switched on** (by weeks 21-24 the "added later" cohort outnumbers "original"). So an
apparent confidence change could be **composition drift** (different sources), not model decay. §7 splits
`original` vs `added later` cohorts precisely to test this: if the *original* cohort's confidence stays
flat, the change is composition, not concept.

**The crux — "Start 75.0% → End 26.8% decisive" vs a flat mean.** These look contradictory; resolving it
*is* the synthesis. Mean confidence sits ~0.45–0.55, right on the 0.5 majority threshold, so the "% decisive"
metric is **hypersensitive** (a tiny mean wobble flips many articles across the 0.5 line). With week 1 at
n=4 and the population **recomposing**, the 75%→27% swing — and the older "0.53→0.45" claim — are artefacts
of **threshold-sensitivity + small-n + composition change**, not genuine decay. The robust trend test says
**flat (r≈0.01)**, and the original-cohort line confirms composition over concept.

**Verdict (the §9 finding):**
- **Data / composition drift: YES** — but benign and system-driven (ingestion maturing, new sources
  switching on), not the world shifting under a fixed model.
- **Concept drift: no evidence** (confidence flat; unconfirmable without labels).
- **Performance drift: not observed** (held-out 0.725 ≈ val).
- **RETRAIN: NO.** The real risks are **input-side representativeness** (schoolsweek 40%, Wales 3) — a
  coverage/curation issue, not model degradation.

AM2 (S24): separating *composition* drift from *concept* drift via the cohort trick, and concluding
honestly, is the distinction-level monitoring story — not just computing a drift number.

### §12 — Production monitoring log & retrain decision

The `fairness_log` / monitor history (one row per scheduled run, 25 May → 11 Jun) is the *operational*
view, and it agrees with the EDA:
- mean confidence **0.479 → 0.494**, pct_below_50 **0.63 → 0.59**, source disparity **0.61 → 0.47** —
  all **stable-to-improving**. Nothing degrading → confirms RETRAIN: NO on the live log too.
- **n_articles drops 991 → 776 around 27 May** (with a simultaneous disparity step-down). That is the
  **data-quality cleanup taking effect** (junk purge around the 26–27 May rework); removing noisy
  sources *improved* the fairness disparity. A concrete worked example of the gate doing its job.
- **political = most-predicted, policy = least-predicted in every single run** — persistent, stable
  class imbalance (catch-all / under-served), not drift.

**Retrain-trigger check** (all three gates must be met; none are):
1. curator decisions **98 / 500** → not met (note: 98, *not* zero — feedback is accruing, just below threshold),
2. **3.7 / 4 weeks** since deploy → not met (model still fresh),
3. confidence < 0.40 for 2 weeks → not met (floor is 0.445, healthy).
→ **RETRAIN: NO**, well-justified (fresh model, little feedback yet, confidence fine). Rule-based and
human-gated — the loop *decides*, it doesn't just compute.

### Bias & fairness — three distinct kinds (K20)

The important move is separating bias the **model introduces** from bias **inherited from the data** from
the **label-design ceiling** — they need different responses:

1. **Algorithmic bias (model-introduced) — ADDRESSED.** SHAP (NB09) showed the with-meta model classified
   by *source-type proxy* (27.6% concentration). Shipping the **no-meta** model makes it classify by
   *content*, robust to new sources; the McNemar tie means this cost no real accuracy. This is the one
   bias actually *in the model*, and it was designed out.
2. **Representation bias (inherited from the data) — PRESENT, upstream.** schoolsweek is **40%** of the
   stream; **England 440 vs Wales 3**. The `source_confidence_disparity` (~0.47) shows the model is more
   confident on well-represented sources than rare ones. The model is faithfully mirroring an imbalanced
   input. **Mitigation is curation + the monthly source-roster review, not a model fix.**
3. **Label-design ceiling — PRESENT, structural.** political over-predicted / policy under-predicted, plus
   the ~0.30 per-class F1 gap (NB11): the editorial triangle. A *taxonomy* overlap problem, not fixable by
   the model (see `embeddings_and_llm_post_model.md`).

**Honest framing:** most of the "bias" here is **not introduced by the model** — it is inherited from an
imbalanced corpus and an overlapping label scheme; the model itself is content-faithful. The
human-in-the-loop curator is the live mitigation (reviews everything). **Subtle risk:** if curators
over-trust high-confidence suggestions, the source-confidence bias could propagate (dominant sources get
more airtime). So: algorithmic bias designed out; representation + label biases flagged and managed by
curation/review, and honestly beyond the model's reach. That tri-partite split is the distinction-level K20 line.

## Related

- `notebooks/12_drift_monitoring.ipynb` (the EDA that surfaced these issues)
- `src/scraping/run.py`, `src/scraping/relevance.py`, `src/scraping/rss_adapter.py` (the gate and the alert adapter)
- `src/inference/s09_monitor.py`, `.github/workflows/drift.yml` (the current monitor)
- `docs/decisions/model_v1_state_and_retraining_plan.md` (retraining stays human-gated)
- `docs/decisions/source_roster_gaps_2026_05_17.md` (coverage gaps, including Four Nations)
