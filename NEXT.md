# Pick up here next session

Snapshot saved 2026-05-17 end of day. AM2 deadline: **2026-05-31** (14 days).

## Tomorrow's first 5 steps (in order)

1. **Verify Streamlit Cloud deploy** — open the URL, click through Overview → Review → Generate Summary. Check Supabase populates. (15 min)
2. **Rename GitHub repo** — fix `automataion` → `automation` typo + `git remote set-url origin https://github.com/Yorkel/AM2_erp_programme_automation.git`. (5 min)
3. **Trigger scrape workflow** — Actions → "Scrape sources → articles" → Run workflow. First clean run with 115+ sources + relevance filter + week_number fix. (~15 min run)
4. **Write 5 AM2 docs** — pure write-up, no code. (~4 hours)
   - `docs/decisions/ml_security_risks.md` (K4/S1)
   - `docs/decisions/data_governance.md` (S11/K25)
   - `docs/decisions/ml_ethics.md` (K26/B4/K24)
   - `docs/decisions/data_security_scalability.md` (K15/S19)
   - `docs/MODEL_LIFECYCLE.md` (S25/S6/S17)
5. **Build `src/inference/scoring.py`** — populates cluster_id + composite_score + 5 other columns already in DB (migration 006). (~2 hours)

## Plus everything else for the fortnight

- `src/inference/fairness_audit.py` — populates `fairness_log` table; K20 evidence (~2 hours)
- **Notebook 11** — classification metrics on the 225 clean labels (~30 min)
- **Notebook 12** — backfill EDA after fresh scrape (~1 hour)
- **Tests** — pick from option (a) honest docs / (b) min-viable / (c) broader coverage / (d) +CI
- **AM2 evidence screenshots** — HF Swagger UI `/docs`, `/metrics`, the dashboard (Overview / Review / Draft pages), Supabase schema panel
- **AM2 portfolio prose** — assemble all the above into the Word template (~6 hours)
- **Operational follow-ups** — `week_number` backfill if too many older rows still NULL after the scrape; flip HF Space to Public (lower stakeholder friction); archive `newsletter_dashboard_demo` repo on GitHub; split `requirements.txt` into full + dashboard for faster Streamlit Cloud rebuilds.

## To resume

Open Claude in this directory, paste:

> Pick up from yesterday — read `project_state_2026_05_17_eod` memory + `NEXT.md` and let's go.

The agent will load the full end-of-day snapshot and we'll start with step 1.

## Where the full context lives

- `project_state_2026_05_17_eod` (auto-memory) — comprehensive EOD snapshot
- `project_deferred_todos` (auto-memory) — full prioritised to-do list with effort estimates
- `docs/decisions/` — design records (data layer, Render OOM, model v1 plan, source-roster gaps, disabled sources, etc.)
- `docs/dashboard_bundle_2026_05_17.md` — bundle from the demo repo, refactor notes
