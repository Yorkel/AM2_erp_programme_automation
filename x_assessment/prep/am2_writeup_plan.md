# AM2 Portfolio — Section Status & Writeup Plan

Tracks every criterion in the L6 AI Engineer AM2 portfolio against current evidence in this repo. **Status column** says whether you can write the section now or whether it needs a notebook to run first.

Source: `L6_MLengineer_AM2_Portfolio_Guidance.docx`. Generated 2026-05-28.

Status legend:
- ✅ — write now; evidence already exists in code / notebooks / memory
- 🟡 — write narrative now; sharpen with output from listed notebook(s)
- ❌ — blocked; cannot write the analytical section until the notebook runs

---

## 1. Engineering Principles

| # | Criterion (KSB) | For pass | For distinction (extra) | Status |
|---|---|---|---|---|
| 1.1 | **K1** — Explain purpose, methodologies, applications of ML/AI | Newsletter automation context; supervised classification rationale; comparison of TF-IDF vs SBERT vs DistilBERT vs Claude as alternative ML paradigms | Trade-off discussion: when to use trained model vs LLM zero-shot; cost-accuracy framing | ✅ Write now — `docs/project_plan.md`, notebooks 01–08 |
| 1.2 | **K5** — Differences/applications of ML methods and models | 5-model comparison (TF-IDF, SBERT+LogReg, DistilBERT, Claude zero-shot, Claude few-shot); what each is best at | Why fine-tuning didn't beat frozen-encoder + classical head on this dataset size | ✅ Write now — `notebooks/08_model_comparison.ipynb` |
| 1.3 | **K18** — Mathematical principles in org context | Sentence embeddings as 384-d vectors; LogReg as linear classifier on those; cosine similarity for clustering (`scoring.py`); softmax → top1/top2 probabilities | Relationship between embedding-space geometry and classification decisions; why metadata one-hots dominated SHAP attribution | ✅ Write now — notebooks 03–09 contain the math |
| 1.4 | **K20** — Sources of error + algorithmic bias | SHAP analysis (`notebooks/09_shap_sst.ipynb`) — proxy concentration 27.6% on metadata features → decision to drop metadata | Per-class fairness slices (per-source / per-nation / temporal); calibration analysis showing where confidence is misleading | 🟡 Write SHAP narrative now; sharpen with **nb 13_bias_fairness** + **nb 12_calibration** |

---

## 2. Work-based Project 1 — Applying ML methods

| # | Criterion (KSB) | For pass | For distinction (extra) | Status |
|---|---|---|---|---|
| 2.1 | **K30/S33/S34** — Integrate AI into existing processes; identify automation potential | Curator workflow before (7hrs/week, ~55 sources manually scanned) → automated scrape + classifier + curator dashboard; one-click triage; one entry in the curator's week saved | Quantify time saved per curator; describe the unified workflow design (Triage/Select Categories/Draft) emerging from the 2026-05-26 redesign | ✅ Write now — code in `src/scraping/`, `src/inference/`, `dashboard/` |
| 2.2 | **K4/S1** — Vulnerabilities / security throughout dev | Curator password gating; HF Space Private + token; Supabase service_key vs anon_key split; `.env` excluded from git; no PII in source content (public sources only) | RLS plan; per-curator auth as future improvement; security-review process | ✅ Write now → **`docs/decisions/ml_security_risks.md`** (not yet created) |
| 2.3 | **S11/K25** — Regulatory / legal / ethical / governance / quality | GDPR Article 6(1)(f) legitimate interest basis for public-source articles; Supabase EU (Frankfurt) region; daily Supabase backups committed; data deletion policy for rejected articles | Concrete documented data-flow audit; how GDPR rights would be honoured if a request came in | ✅ Write now → **`docs/decisions/data_governance.md`** (not yet created) |
| 2.4 | **(Implicit)** — Operate under technical complexity to apply ML for business problems | 5-model comparison narrative; the val→real-world degradation finding (0.750 → 0.630); decision framework for which model to ship | Honest engineering — the no-test-set methodological gap acknowledged; the held-out test as the remediation | 🟡 Write narrative now; sharpen with **nb 14_held_out_test** |
| 2.5 | **K14/S9** — Refine / re-engineer model; version + change management | Model versioned at `models/runs/v1_2026-05-16/`; `active.txt` pointer; 13 SQL migrations; git history of `src/scraping/` evolution | Counterfactual on what would have happened with the metadata version in production | ✅ Write now — repo structure speaks for itself |
| 2.6 | **K27** — Cyber security culture | Personal practices: secrets in `.env` not git, dependency pinning via `requirements.txt`, HF token rotation discipline, no force-pushes | Position the practices as transferable to a larger organisation post-handover | ✅ Write now — frame as solo-engineer-imposed culture |
| 2.7 | **K25/S32** — ML principles / standards / assurance frameworks | Industry-standard tooling: HuggingFace sentence-transformers, sklearn, FastAPI auto-OpenAPI docs at `/docs`; reference NIST AI RMF, EU AI Act draft, OECD AI Principles | Map this project's decisions to specific framework clauses (e.g. NIST AI RMF Map-Measure-Manage-Govern) | ✅ Write now — could merge into ml_security_risks.md or sit alongside |
| 2.8 | **(B5)** — Own role supports org strategy; impartial decisions under change | AM2 portfolio context; ESRC ERP programme handover-readiness; curator-iteration cycle (4 meetings) showing adaptive decision-making | "Impartial decisions" angle: SHAP-driven model choice over higher F1 = principled rather than maxing-the-leaderboard | ✅ Write now — curator memories now logged |
| 2.9 | **Distinction S9/K14** — Critically evaluate why refining model | SHAP-driven decision narrative: 0.750 vs 0.765, the 27.6% proxy concentration finding, the principled choice to ship the lower-F1 content-faithful model | McNemar p-value showing the F1 difference is statistical noise (strengthens story: didn't trade real F1 for principle, traded noise for principle); bootstrap CIs on val F1 | 🟡 Narrative now (already exists in notebooks); sharpen with **nb 12_calibration** (McNemar cell needs filling) |
| 2.10 | **Distinction S27** — Justifies stakeholder strategies | ⭐ Curator iteration cycle: 4 meetings (20 Apr / 5 May / 26 May / 27 May) with concrete asks → shipped. Each meeting evolved the product. Now logged in memory. | The 26 May redesign as a stakeholder-driven pivot: "they said the v1 was wrong, here's what I did about it" | ✅ Write now — strongest narrative in the project |

---

## 3. Work-based Project 2 — Live ML model

| # | Criterion (KSB) | For pass | For distinction (extra) | Status |
|---|---|---|---|---|
| 3.1 | Platform architecture + hardware + ML methods + impact | FastAPI on HuggingFace Spaces (Render-style container); Supabase Postgres EU; Streamlit Cloud for dashboard; GitHub Actions cron for orchestration; rationale for each | Why not local Docker (codespaces resource discipline — see [[project-skipped-local-docker]]); why not full Prometheus+Grafana stack (scale-appropriate); the in-progress Next.js migration as future state | ✅ Write now — all decisions documented in `docs/decisions/` and memory |
| 3.2 | Data types security/scalability/cost (local/remote/distributed) | Render free-tier OOM at batch=50 → batch=10 fix (concrete trade-off); Supabase free-tier sizing; Claude Haiku ~$0.001/article (~$0.04/week); HF Space Private token cost | Calculations on what happens at 10× article volume; how the system would degrade gracefully | ✅ Write now → **`docs/decisions/data_security_scalability.md`** (not yet created) |
| 3.3 | **S24** — Model drift / data drift / performance monitoring | `drift_log` Supabase table; `src/inference/s09_monitor.py` runs every classify; 18-week backfill confirmed concept drift (confidence 0.53 → 0.45, <50%-confidence articles 41% → 74%); v2 trigger criteria in [docs/decisions/model_v1_state_and_retraining_plan.md](decisions/model_v1_state_and_retraining_plan.md) | Drift-in-fairness story (separate from drift-in-F1); per-class confidence heatmap showing which classes drift hardest | 🟡 Narrative now; sharpen with **nb 11_backfill_drift_eda** (the chart-producing notebook) |
| 3.4 | **S25** — Decommissioning / legacy management | `models/runs/active.txt` pointer; versioned model directories; retraining trigger criteria documented; how a v2 would be promoted | Rollback procedure; what happens to in-flight inference jobs at switchover | ✅ Write now → **`docs/MODEL_LIFECYCLE.md`** (not yet created) |
| 3.5 | Compliance / governance / industry regs / audit | `scrape_runs` Supabase audit table; daily backups in `backups/<date>/*.csv`; GH Actions run history; classifier predictions traceable to model version via `run_meta` | Audit replay capability (could you re-classify a specific week's articles against an old model?); compliance with ESRC research data policies | ✅ Write now — audit infrastructure already in code |
| 3.6 | **K26** — Ethics; integrity in ML use | SHAP-driven decision IS the ethics moment (refused source-proxy classification); curator-in-loop for every published item; transparency via FastAPI `/docs`; no PII in source data | Counterfactual: what would have happened to which curators if we'd shipped the metadata model? Show concrete bias risk avoided | ✅ Write now → **`docs/decisions/ml_ethics.md`** (not yet created) |
| 3.7 | Stakeholder engagement / multi-disciplinary teams | Curator iteration cycle (4 meetings); engagement with Render hosting team; HF Space community; Anthropic API community; sustainability conversation with user re: legacy tool | Conflict-management example: curator "total refresh" ask in 26 May meeting and how it was scoped to "restructure not rebuild" | ✅ Write now — curator memories logged |
| 3.8 | Inclusive collaboration tech/non-tech | Streamlit dashboard targets non-technical curators with plain-English labels; FastAPI `/docs` Swagger UI targets technical reviewers; documented decisions translate ML jargon into curator-language | Specific examples of language adaptation: "Top 1: Politics & key orgs (44%)" vs underlying `accept_top1` action | 🟡 Write now; brief personal reflection on tone shifts |
| 3.9 | **Distinction K15/S19** — Security/scalability decisions justified | Render OOM → batch=10 (memory vs throughput); HF Space Private + token auth (don't expose unfinished model); Supabase service_key in CI vs anon_key in dashboard (privilege separation); skipped local Docker (resource discipline) | ⭐ Lived incident 2026-05-28: silent NULL-summary failure → traced via workflow logs (distinguished `AuthenticationError` from `APIConnectionError`) → three-layer defence shipped (SDK retries / idempotent sweep / loud-fail exit). See `docs/decisions/scrape_reliability_hardening_2026_05_28.md` | ✅ Write now — concrete decisions in `docs/decisions/` |
| 3.10 | **Distinction S22/S24** — Systems robust through monitoring | `drift_log` + `fairness_log` + Prometheus `/metrics` endpoint + `sweep_unclassified` + **`sweep_summaries` safety-net (added 2026-05-28)** + loud-fail exit code → GitHub email + `scrape_runs` audit + daily backups | Per-issue F1 holding stable over time (held-out test); calibration in target range; statistically-significant model improvement (or not) via McNemar | ✅ Narrative now — self-healing pipeline + alert path closed; sharpen quant with **nb 11 + nb 12 + nb 13 + nb 14** combined |

---

## 4. CPD

| # | Criterion (KSB) | For pass | For distinction (extra) | Status |
|---|---|---|---|---|
| 4.1 | **K28/S31/B1** — Stay current with emerging tech + societal impact | Module 9 learnings; Claude API + prompt caching adoption; sustainability/legacy-platform analysis (Reflex / Next.js / Airtable etc. — done 2026-05-27); societal impact reflection on schools-newsletter content curation | Critical reflection: where AI in education is heading; ethics of LLM summarisation for editorial workflows; what you'd do differently with current tooling | ✅ Write now — sustainability memo already in memory ([project_sustainability_platform.md]) |

---

## Summary

| Status | Count | Action |
|---|---|---|
| ✅ Write now | 17 of 25 criteria | Start prose this week — ~12 hours |
| 🟡 Partial now, sharpen after notebooks | 7 criteria | Write the narrative; insert plots later |
| ❌ Fully blocked on notebook | 1 (held-out test results inside 2.4) | Build `test.csv` + run nb 14 |

## Notebooks needed for distinction-grade evidence

In run order:

1. **`11_backfill_drift_eda.ipynb`** — drift plots → upgrades 3.3, 3.10 partials
2. **`12_calibration.ipynb`** — bootstrap CIs + McNemar → upgrades 2.9, 1.4 partials
3. **`13_bias_fairness.ipynb`** — fairness slices → upgrades 1.4, 3.10 partials
4. **`14_held_out_test.ipynb`** (after extracting `test.csv` from issues 88+) — upgrades 2.4

## Missing decision docs (each criterion above flagged "not yet created")

1. `docs/decisions/ml_security_risks.md` (criterion 2.2) — 45 min
2. `docs/decisions/data_governance.md` (criterion 2.3) — 45 min
3. `docs/decisions/ml_ethics.md` (criterion 3.6) — 30 min
4. `docs/decisions/data_security_scalability.md` (criterion 3.2) — 45 min
5. `docs/MODEL_LIFECYCLE.md` (criterion 3.4) — 60 min

**Total decision-doc effort: ~4 hours**

## Decision docs already shipped

- ✅ `docs/decisions/scrape_reliability_hardening_2026_05_28.md` — lived incident write-up (criterion 3.9 / 3.10 / S22 / S24)

## Total budget

| Bucket | Hours |
|---|---|
| Write the ✅ sections (prose only) | ~12 |
| Write the 5 decision docs | ~4 |
| Run nb 11 + nb 12 + nb 13 | ~7 |
| Build test.csv + run nb 14 | ~3 |
| Insert plots into 🟡 sections + finalise | ~3 |
| CPD + screenshots + final polish | ~2 |
| **Total to distinction-ready** | **~31** |

Over 5 weeks to end-of-June: ~6 hrs/week. Comfortable.
