# AM2 Portfolio Tracker (L6 ML Engineer — Professional Discussion)

Every item required for the AM2 portfolio doc, mapped to KSBs, with status + what's
left. Deliverable = the guidance doc filled in with **first-person, past-tense
STAR notes** for a 90-min open-book professional discussion, across **2 projects**.

**Projects**
- **P1 — Applying ML methods** = building the ESRC newsletter classifier.
- **P2 — Working with a live ML model** = the production dashboard + drift monitoring + curator collaboration.

**Status key:** ✅ done · 🟢 evidence ready, needs writing up · 🟡 partial (some evidence/work to do) · 🔴 not started

---

## Section 1 — Engineering Principles (general knowledge notes)

| Requirement | Task | KSB | Status | Outstanding |
|---|---|---|---|---|
| Purpose, methodologies & applications of ML/AI | Write notes: why ML suits the newsletter-classification problem; supervised/unsupervised/deep; where applied in ESRC ERP | K1 | 🔴 | Write notes |
| Differences & applications of ML methods/models | Notes: supervised vs unsupervised vs deep; example models per method; how differences affect use | K5 | 🔴 | Write notes |
| Maths principles ↔ core techniques | Notes: theory of linear regression, logistic regression, tree-based models (tie to your classifier) | K18 | 🟡 | Write notes (you use these) |
| Sources of error & algorithmic bias | Notes + **run a bias/fairness analysis** (per-source / per-region performance) | K20 | 🔴 | Bias/fairness analysis NOT yet done — build NB + write up |

---

## Section 2 — Project 1: Applying ML methods (the classifier)

| Requirement | Task | KSB | Status | Outstanding |
|---|---|---|---|---|
| Project brief (200–500 words) | Write STAR brief: problem, ML solution, outcome | — | 🔴 | Write brief |
| Integrate AI into processes / identify automation | Write up bringing scraping in-house + classifier automating curation | K30, S33, S34 | 🟢 | Write up |
| Assess vulnerabilities / security across lifecycle | Write up: Supabase service keys, API auth, secret handling, where data lives/who has access | K4, S1 | 🟡 | Name org policies; write up |
| Evaluate data-process choices (regulatory/legal/ethical/governance/quality) | Write up: scope decision (schools/pre-HE/FE), GDPR, data quality controls | S11, K25 | 🟡 | Write up |
| Evaluate performance / metrics align with business | **Run proper evaluation** (held-out, per-class, confusion matrix) + write up vs curator needs | K19, S12, B5 | 🟡 | Rigorous evaluation NOT yet done — run NB14/NB11 |
| Refine/re-engineer + version control + documentation | Write up: tuning, git/GitHub, `models/runs/active.txt`, model-state doc | K14, S9 | 🟢 | Write up |
| Cyber security culture | Notes: org security/data policies; how the model could breach them | K27 | 🟡 | Name policies; write up |
| ML principles/assurance frameworks for safe data use | Notes: NCSC ML security principles; how applied; preventing data exposure | K25, S32 | 🟡 | Write up |
| Role ↔ org strategy; impartial decisions under change | Write up: how the newsletter pipeline serves ESRC ERP; handling scope/deadline changes | K29, S26 | 🟢 | Write up |
| **Distinction:** critically evaluate model refinement | Write up: what worked/didn't in optimisation; what you'd do differently | S9, K14 | 🟡 | Needs held-out/optimisation evaluation (NB11) |
| **Distinction:** justify stakeholder strategies | Write up: curator collaboration, comms methods, adapting to needs | S27 | 🟢 | Write up |

---

## Section 3 — Project 2: Working with a live ML model (dashboard + monitoring)

| Requirement | Task | KSB | Status | Outstanding |
|---|---|---|---|---|
| Project brief (≤500 words) | Write STAR brief: live model, monitoring, collaboration | — | 🔴 | Write brief |
| Platform architecture & hardware | Write up: Render → HF Spaces, Docker remote build, FastAPI `/docs` (Swagger), free-tier choices | K11, S22 | 🟢 | Write up |
| Data types → security & scalability, supply-chain risk | Write up: Render OOM → batch size; HF Space visibility; sensitive-data handling | K15, S18, S19 | 🟢 | Write up |
| Monitor model/data drift & performance | **Run drift analysis** (data/concept drift, confidence over time) + describe tools/metrics | S24 | 🟡 | Drift analysis NOT yet report-ready — build NB12 |
| Decommission assets / manage legacy models | Notes/write up: `active.txt` pointer, v1→v2 retraining plan, any policy | S25 | 🟡 | Write up (+ note process) |
| Compliance, governance, audit, lifecycle docs | Write up: GDPR, decision docs, change log (`deployment_challenges.md`) | S6, S17 | 🟡 | Write up |
| Act with integrity / ethics (legal/regulatory) | Write up: ethical scope, fairness audit, data ethics | K26, B4, K24 | 🟡 | Write up |
| Engage diverse stakeholders; manage expectations/timescales | Write up: Gemma/Rachel/Nina, trial feedback loop, deadline management. **Strong evidence (2026-06-09 thread, in `deployment_challenges.md`): explicit Tue→Thurs production cadence; dashboard items used as late PEKO replacements in issue #115 ("picking up stuff Emma W doesn't see"); stakeholder-driven shift to Monday-night delivery.** | K21, S27 | 🟢 | Write up |
| Act inclusively (technical & non-technical); EDI | Write up: adapting comms for curators vs technical; org EDI policies | S30, B3 | 🟡 | Name EDI policy; write up |
| **Distinction:** justify risk/security/scalability decisions | Write up: a specific scaling/security decision (e.g. batch=10 for OOM; HF private), monitoring/maintenance | K15, S19 | 🟢 | Write up |
| **Distinction:** robustness via monitoring & data-quality control | Write up: how monitoring keeps performance reliable; data-quality checks; what works/improves | S22, S24 | 🟡 | Needs NB12/13 + write up |

---

## Section 4 — Continuous Professional Development

| Requirement | Task | KSB | Status | Outstanding |
|---|---|---|---|---|
| Identify emerging trends; stay current | Notes: recent AI/ML trends (genAI ubiquity), one +ve & one −ve societal impact, tools/resources used (lunch & learn, etc.) | K28, S31, B1 | 🔴 | Write notes |

---

## Supporting technical artefacts (evidence — esp. for Distinction)

**All four analysis notebooks already EXIST and are fully written** (code + markdown,
sophisticated) — they have **never been executed** (zero outputs). So these are
**run + write-up**, not build. Deps all present except **`statsmodels`** (NB12
McNemar only; pip install). Data paths all present.

| Notebook (in `notebooks/`) | Purpose / KSB it strengthens | Status | Outstanding |
|---|---|---|---|
| `14_held_out_test.ipynb` | Held-out (unseen issues **105–114**) macro-F1 vs val → K19/S12, Distinction S9 | 🟡 written, not run | In cell 3 set `HELD_OUT_ISSUES = range(105, 115)` (include issue 114), then Restart & Run All |
| `11_backfill_drift_eda.ipynb` | Confidence over time, % <50% conf/week, class-mix shift → S24 | 🟡 written, not run | Restart & Run All |
| `12_calibration.ipynb` | Reliability diagram, Brier/ECE, **bootstrap CIs on F1**, McNemar → S24 + Dist S22/S24 | 🟡 written, not run | `pip install statsmodels`, then run |
| `13_bias_fairness.ipynb` | Per-class / per-source / **per-nation (Four Nations)** / over-time / curator-override fairness → K20, S11, K26 | 🟡 written, not run | Restart & Run All |
| Decision docs / model card | Documentation evidence → K14, S6, S17 | 🟡 partial | Finish (+ `docs/decisions/model_lifecycle.md` now drafted for S25) |
| `deployment_challenges.md` | Change log / monitoring / stakeholder evidence → P2 (S6/S17/S24/K21) | ✅ | — (keep updated) |
| **(future)** pipeline coverage / curator-acceptance NB | % of published items dashboard-scraped (rising 0→25%) + keep/accept rate → K19/S12, P2 | 🔴 post-handover | Build once curators have ~2 weeks of live use (needs real `curator_decisions` data) |

---

## Suggested order (deadline: end of June 2026)
1. Run/finish notebooks **14 → 11 → 12 → 13** (the evidence artefacts).
2. Write **Project 2** first (freshest; `deployment_challenges.md` is the raw material).
3. Write **Project 1** (classifier build + evaluation).
4. Write **Engineering Principles + CPD** notes (general knowledge — quick).

## Headline status (corrected 2026-06-09)
- **Built & deployed:** classifier + live dashboard + pipeline — strong on the
  *engineering/deployment* criteria (K11, S22, K15, stakeholder, automation).
- **Analysis: already WRITTEN, not yet RUN.** Notebooks 11 (drift), 12
  (calibration + bootstrap CIs + McNemar), 13 (bias/fairness incl. Four Nations),
  14 (held-out) exist as complete, sophisticated analyses — they just need
  **Restart & Run All** (+ `pip install statsmodels`) to produce the figures/
  numbers, then interpreting. This covers K19/S12, S24, K20 and the Distinctions.
- **Then:** write the portfolio notes in first-person STAR for every criterion.

So the gap is **run the 4 notebooks → interpret → write up.** Much less than
"build" — the hard design/coding is done.
