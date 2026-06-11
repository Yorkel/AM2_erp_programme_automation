# Monitoring redesign: quality gate at ingestion, weekly drift, monthly source review

**Date:** 2026-06-11
**Status:** Process agreed. Parts already exist; the rest is deferred until after the AM2 write-up.
**Trigger:** Building the inference-data EDA in `notebooks/11_drift_monitoring.ipynb`.

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
them; "never" is just hoping. The notebook (`11_drift_monitoring.ipynb`) is the human review
surface for both loops — it pulls the raw data (`v_dashboard`) plus the pipeline's computed
logs (`drift_log`, `fairness_log`, rejected archive) and displays them.

## Notebook structure (consolidated 2026-06-11)

Analysis notebooks reduced to two, split by the label rule (*does it use ground-truth labels?*):

- **`11_drift_monitoring.ipynb` — Monitoring** (live stream, no labels): data quality, drift,
  confidence, per-source fairness disparity, retrain-trigger check, relevance-filter analysis
  (folded in from old nb15).
- **`evaluation.ipynb` — Evaluation** (labelled test/val set): held-out performance, calibration,
  bootstrap CIs, McNemar, bias & fairness by accuracy. Merged from old nb12 + nb13 + nb14.

`notebooks/01-10` remain as the model-build history. Superseded notebooks are in
`notebooks/_archive/`.

## AM2 framing (S24)

The robust-monitoring story: quality work sits at ingestion (the gate acts), monitoring
observes and routes (weekly), and a monthly human review evolves the allow/block lists. It
demonstrates the full loop (detect, score, route, review, retrain trigger) rather than just
computing a drift number. The week-20 Google-Alerts leak is a concrete worked example of why
the review loop matters.

## Related

- `notebooks/11_drift_monitoring.ipynb` (the EDA that surfaced these issues)
- `src/scraping/run.py`, `src/scraping/relevance.py`, `src/scraping/rss_adapter.py` (the gate and the alert adapter)
- `src/inference/s09_monitor.py`, `.github/workflows/drift.yml` (the current monitor)
- `docs/decisions/model_v1_state_and_retraining_plan.md` (retraining stays human-gated)
- `docs/decisions/source_roster_gaps_2026_05_17.md` (coverage gaps, including Four Nations)
