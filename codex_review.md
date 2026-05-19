# Codex Review

Date: 2026-05-19

## Overall Rating

Current rating: **6/10**

This is a strong AM2/portfolio prototype with a real end-to-end ML workflow, but it is not yet production-grade. The core architecture is promising: scraping, Supabase, classifier API, scoring, Streamlit dashboard, drift monitoring, fairness audit, and backups are all represented. The main weaknesses are repo maturity, reproducibility, tests, documentation drift, security hygiene, and a few runtime bugs.

## Maximum Realistic Rating

Realistic ceiling: **9.5/10**

Suggested rating ladder:

| Rating | What must be true |
|---|---|
| 7/10 | README fixed, broken tests removed/replaced, pipeline failures handled, migration mismatch fixed. |
| 8/10 | CI added, core unit/integration tests passing, dashboard bugs fixed, secrets/auth cleaned up, legacy folders archived. |
| 8.5/10 | Fresh clone setup is reproducible, docs are clean, GitHub Actions are reliable, Supabase/RLS is credible, monitoring evidence is usable. |
| 9/10 | Production-grade packaging, dependency pinning, migration tooling, stronger dashboard persistence, model evaluation automation. |
| 9.5/10 | Disciplined operational system: per-user auth/audit trail, rollback/retraining process, observability, robust CI/CD, clean repo boundaries, low notebook/data clutter. |

I would not call 10/10 realistic for this project unless it becomes a long-lived commercial-grade system with dedicated maintenance. But **9 to 9.5 is achievable**.

## What Is Working Well

- The repo contains a genuine end-to-end workflow: scrape sources, store articles in Supabase, classify through an API, score/deduplicate, review in a dashboard, generate drafts, and monitor drift/fairness.
- The FastAPI serving layer is well-shaped. `src/serving/api.py` exposes `/health`, `/predict`, and `/metrics`, loads the model once, and returns top-1/top-2 predictions with confidence scores.
- The model is versioned under `models/runs/`, with `active.txt`, metadata, baselines, centroids, and a classifier artifact.
- The dashboard has moved beyond a demo: it reads from Supabase, records curator decisions, supports review/organise/draft flows, and gates mutating actions behind a curator password.
- The scraper architecture is thoughtful: `sources.yml`, source adapters, central relevance filtering, source-specific scrapers, run logging, and Supabase upserts.
- There are useful operational pieces: GitHub Actions for scrape/classify/drift/fairness/backup, Prometheus metrics, fairness logging, drift logging, and backup snapshots.
- The ML decision to use the no-metadata SBERT classifier is defensible because it reduces source-proxy classification risk.

## What Is Not Working Or Risky

- The migration chain is not reproducible from scratch. `migrations/001_articles_topics.sql` creates `articles_topics`, but later code and migrations use `public.articles`.
- `src/pipeline.py` ignores return codes from step modules, so a failed classify/scoring step can still end with "Pipeline complete."
- Tests are currently not usable. `pytest` is not installed, and the only test file imports old/missing `deploy_download_v2` modules.
- `src/inference/summarise.py --dry-run` currently fails with `KeyError: 'text'` because `estimate_cost()` expects few-shot examples to have a `text` key, while the bundled examples use `summary`.
- Manual article addition is only session-scoped, but review actions write decisions to Supabase. Because `curator_decisions.url` has a foreign key to `articles.url`, accepting a manual article that is not in Supabase is likely to fail.
- The README is stale and describes an earlier "to build" state. It also references `docs/next_steps.md`, which is not present.
- `.gitignore` ignores `docs/*.md`, so many important docs exist locally but are not part of the tracked repo.
- There is a security issue: a curator password appears in an ignored local doc. Rotate it if it has ever been used.
- The dashboard falls back to `SUPABASE_SERVICE_KEY`; production dashboard writes should use anon key plus RLS where possible.
- `dashboard/app.py` formats `article_date` as `DD-MM-YYYY` strings before review sorting, which can produce wrong chronological ordering.
- `deploy_download_v2/` is legacy code and creates confusion about the true project architecture.

## Priority Roadmap To Reach 9.5/10

### Priority 0: Stop The Bleeding

Goal: make the repo safe, honest, and non-misleading.

1. **Rotate leaked/known curator password**
   - Remove any password from docs.
   - Rotate the Streamlit `CURATOR_PASSWORD` secret.
   - Acceptance check: no hardcoded password appears in `rg -n "ERP2026|CURATOR_PASSWORD|password" docs dashboard .github README.md`.

2. **Update `README.md` to match reality**
   - Describe the current stack: Python, Streamlit, Supabase, FastAPI, GitHub Actions, HF/Render-style classifier deployment.
   - Remove stale "to build" claims.
   - Add fresh setup commands for dashboard, API, scraper, and pipeline.
   - Acceptance check: a new user can understand what the repo does in five minutes.

3. **Fix `.gitignore` documentation policy**
   - Remove or narrow `docs/*.md`.
   - Decide which docs are portfolio evidence, which are local scratch notes, and which should be archived.
   - Acceptance check: important docs are tracked; scratch docs are deliberately ignored by name.

4. **Archive or remove `deploy_download_v2/`**
   - If it is useful history, move it under `experiments/legacy/` and clearly mark it as non-runtime.
   - If not needed, delete it.
   - Acceptance check: no active test, workflow, or setup doc points to stale `deploy_download_v2` modules.

### Priority 1: Make The System Reproducible

Goal: a fresh clone plus secrets can run the expected workflow.

5. **Fix the Supabase migration chain**
   - Update migration 001 to create `articles`, or add a migration that renames `articles_topics` to `articles`.
   - Ensure later migrations apply cleanly in order.
   - Acceptance check: empty Supabase project can apply migrations 001-011 without manual table renames.

6. **Create `.env.example`**
   - Include placeholders for `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `CLASSIFIER_API_URL`, `CLASSIFIER_API_KEY`, `ANTHROPIC_API_KEY`, and `CURATOR_PASSWORD` where relevant.
   - Label which vars are local-only, CI-only, dashboard-only, and server-only.
   - Acceptance check: setup docs never require guessing env var names.

7. **Add a project config file**
   - Add `pyproject.toml` for package metadata, pytest config, ruff config, and import path settings.
   - Consider separate dependency groups: `api`, `dashboard`, `pipeline`, `dev`.
   - Acceptance check: `python -m pytest`, `ruff check`, and import paths work predictably from repo root.

8. **Pin or lock dependencies**
   - Keep lightweight `requirements-*.txt` if needed for deployment, but add a lock strategy.
   - At minimum, separate runtime and dev dependencies.
   - Acceptance check: installs are repeatable and CI does not break from surprise package upgrades.

### Priority 2: Make Failures Loud

Goal: a broken pipeline cannot look successful.

9. **Fix `src/pipeline.py` return-code handling**
   - Make `run_step()` capture the module `main()` return value.
   - If a step returns non-zero, stop the pipeline and exit non-zero.
   - Standardise all step modules to return `0` on success and `1` on failure.
   - Acceptance check: missing `CLASSIFIER_API_URL` or missing input CSV fails the pipeline and GitHub Action.

10. **Make all CLI modules consistently exit**
    - Add `raise SystemExit(main())` where appropriate.
    - Avoid silent `return` after errors.
    - Acceptance check: every script used by Actions exits non-zero on required config/data failure.

11. **Add smoke tests for pipeline wiring**
    - Test `src/pipeline.py --help`.
    - Test step registry imports.
    - Test missing env/input failure paths.
    - Acceptance check: CI catches wiring breakages before deployment.

### Priority 3: Replace Broken Tests With Useful Tests

Goal: tests reflect the current repo, not old AtlasED/NMF code.

12. **Delete or quarantine obsolete tests**
    - Remove tests importing `model_pipeline.training.s02_cleaning`, `s03_spacy_processing`, and `s06_topic_allocation`.
    - Acceptance check: test suite contains no references to missing modules.

13. **Add unit tests for pure functions**
    - `src.scraping.common.scrape_week`
    - `src.scraping.common.build_text_clean`
    - `src.scraping.config.load_sources`
    - `src.inference.scoring.recency_score`
    - `src.inference.scoring.substance_score`
    - `src.inference.scoring.cluster_articles`
    - `src.inference.fairness_audit` summary functions
    - Acceptance check: these tests run without Supabase, network, or model downloads.

14. **Add dashboard data-layer tests with mocks**
    - Mock Supabase client responses for `load_classified_articles`, `load_decisions`, `record_decision`, `set_newsletter_pick`, and `record_summary`.
    - Acceptance check: dashboard persistence logic is covered without real Supabase.

15. **Add API tests**
    - Test `/health` and `/predict` with a mocked model bundle.
    - Avoid loading sentence-transformer in unit tests.
    - Acceptance check: API contract is tested fast in CI.

16. **Add integration tests behind env gates**
    - Supabase connectivity.
    - Applying migrations to a throwaway database if possible.
    - Optional deployed classifier health check.
    - Acceptance check: integration tests skip clearly when secrets are absent.

### Priority 4: Fix Known Runtime Bugs

Goal: curator workflow works reliably.

17. **Fix summariser cost estimation**
   - Change `estimate_cost()` to use `ex["summary"]`, not `ex["text"]`, or normalise few-shot examples to a single shape.
   - Acceptance check: `python -m src.inference.summarise --input data/modelling/classified_articles.csv --dry-run --limit 1` succeeds.

18. **Persist manual articles properly**
   - When a curator manually adds an article, insert it into `articles` first.
   - Then allow classification suggestion/decision rows to reference it.
   - Acceptance check: manually added articles survive refresh and can be accepted, organised, drafted, and exported.

19. **Fix category override persistence**
   - Use `set_category_override()` instead of overwriting the whole decision with `record_decision(..., "manual", move_to)` where appropriate.
   - Ensure `get_accepted_articles()` reads `newsletter_category_override` from Supabase, not only session state.
   - Acceptance check: moving an article category survives reload/logout.

20. **Persist edited draft descriptions**
   - Generated summaries are saved, but manually edited text areas are session-local.
   - Save edited descriptions explicitly to Supabase, either on button click or debounced form submit.
   - Acceptance check: a curator edit survives reload.

21. **Fix review date sorting**
   - Keep a real datetime/date column for sorting and only format for display.
   - Acceptance check: oldest/newest sorting works across month boundaries.

22. **Improve dashboard error handling**
   - Friendly messages for missing Supabase env vars, auth failures, summariser failures, and write failures.
   - Acceptance check: user sees actionable error text, not stack traces.

### Priority 5: Security And Data Governance

Goal: the dashboard is suitable for real curator use.

23. **Use anon key + RLS for dashboard**
   - Avoid `SUPABASE_SERVICE_KEY` in Streamlit where possible.
   - Define Row Level Security policies for read/write tables.
   - Keep service role only in GitHub Actions/server-only contexts.
   - Acceptance check: dashboard can run without service role key.

24. **Replace shared password with per-user auth**
   - Best option: Supabase Auth.
   - Record `curator_id` or `submitted_by` on curator decisions, feedback, and summaries.
   - Acceptance check: audit trail can show who made which decision.

25. **Add a real audit trail**
   - Current `curator_decisions` upserts latest decision only.
   - Add an append-only decision history table for changes over time.
   - Acceptance check: corrections, rejects, category moves, and summaries are traceable.

26. **Classify sensitive artifacts**
   - Decide what belongs in git, Supabase, backups, local-only data, and portfolio evidence.
   - Acceptance check: no secrets, raw private data, or unnecessary backups are committed.

### Priority 6: CI/CD And Deployment Quality

Goal: every push proves the repo still works.

27. **Add CI workflow**
   - Run install, lint, compile, tests, and import smoke tests.
   - Keep heavy model/API/network tests optional.
   - Acceptance check: pull requests get a clear pass/fail signal.

28. **Add workflow concurrency and artifact discipline**
   - Prevent overlapping scrape/classify runs from racing.
   - Save useful summaries/logs as artifacts where appropriate.
   - Acceptance check: two scheduled runs cannot corrupt the same output path.

29. **Make backups safer**
   - Committing daily Supabase backups to `main` is useful for AM2 evidence but risky long term.
   - Consider private object storage, encrypted artifacts, or limited backup tables.
   - Acceptance check: backup strategy matches data governance decision.

30. **Document deployment targets**
   - Dashboard: Streamlit Cloud.
   - Classifier API: Hugging Face Spaces or Render, choose one as canonical.
   - Workflows: GitHub Actions.
   - Supabase: schema and secrets.
   - Acceptance check: deployment docs do not contradict each other.

### Priority 7: Model Quality And MLOps

Goal: model behaviour is measured, explainable, and maintainable.

31. **Automate model evaluation**
   - Track validation macro-F1, weighted-F1, top-2 accuracy, confusion matrix, confidence calibration, and real-world curator accuracy.
   - Acceptance check: a model candidate cannot become active without an evaluation report.

32. **Add retraining protocol**
   - Define when curator corrections become training data.
   - Define minimum sample size, train/validation split, and sign-off criteria.
   - Acceptance check: `docs/MODEL_LIFECYCLE.md` or equivalent explains retrain, promote, rollback.

33. **Store model run IDs in predictions**
   - `pull_predictions.py` notes that `model_run_id` is not stored in `classify_newsletter`.
   - Add it to the table so drift/fairness can audit historical predictions accurately.
   - Acceptance check: every prediction row records the model that produced it.

34. **Improve calibration and thresholds**
   - Use curator feedback to decide when confidence is trustworthy.
   - Add confidence bands to dashboard sorting/filtering.
   - Acceptance check: low-confidence and close top-1/top-2 predictions are easy to review first.

35. **Strengthen deduplication/scoring**
   - Validate clustering threshold with examples.
   - Let curators override cluster lead if needed.
   - Acceptance check: duplicate stories are grouped without hiding genuinely distinct stories.

### Priority 8: Repo Hygiene And Portfolio Polish

Goal: the repo is easy to read, assess, and maintain.

36. **Clean tracked artifacts**
   - Decide whether notebooks, BERA outputs, backup CSVs, and generated images belong in the repo.
   - Move portfolio evidence into a deliberate `docs/evidence/` area if needed.
   - Acceptance check: `git ls-files` contains intentional artifacts only.

37. **Create an architecture document**
   - One diagram or text doc showing data flow:
     scrape -> articles -> classifier -> classify_newsletter -> v_dashboard -> curator_decisions -> draft/feedback -> monitoring.
   - Acceptance check: an assessor can understand the system without reading code.

38. **Create an operations runbook**
   - How to run weekly scrape/classify.
   - How to recover from failed scrape.
   - How to rotate secrets.
   - How to rollback model.
   - How to restore from backup.
   - Acceptance check: future-you can operate the system under deadline pressure.

39. **Standardise naming**
   - Fix repo typo `automataion` -> `automation` if not already done.
   - Use one canonical name for the project, classifier, dashboard, and tables.
   - Acceptance check: docs, workflows, deployment configs, and README agree.

40. **Add screenshots/evidence intentionally**
   - Dashboard review/draft pages.
   - API Swagger or `/docs`.
   - `/metrics`.
   - Supabase schema.
   - GitHub Actions runs.
   - Acceptance check: AM2 evidence is easy to find and not mixed with scratch outputs.

## Suggested Work Order

The fastest path to visible improvement:

1. Rotate password and clean secrets/docs exposure.
2. Fix README and `.gitignore` documentation policy.
3. Fix migration 001/table naming.
4. Fix pipeline return-code handling.
5. Delete/quarantine old tests and add basic current tests.
6. Fix summariser dry-run bug.
7. Fix manual article persistence and category override persistence.
8. Add CI.
9. Add RLS/anon-key dashboard security.
10. Add model lifecycle and operations docs.

After those ten, the repo should be around **8 to 8.5/10**. The final push to **9.5/10** comes from per-user auth, audit trails, strong MLOps, reliable deployment runbooks, and disciplined artifact management.

## Verification Notes From Audit

- `python -m compileall -q src dashboard deploy_download_v2` passed.
- Import smoke test passed for `dashboard.data`, `src.serving.api`, `src.pipeline`, and `src.scraping.run`.
- Existing tests could not run because `pytest` is missing.
- `src.inference.summarise --dry-run` currently fails with `KeyError: 'text'`.
- Local `data/modelling/classified_articles.csv` contained 873 rows and 20 columns at audit time.

