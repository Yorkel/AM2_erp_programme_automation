# Model lifecycle, versioning & decommissioning (S25, S6, S17, K14)

Record of how models and data assets are versioned, managed and retired in the
ESRC ERP newsletter-classification project. Written for AM2 (criterion S25 —
decommission assets and manage current/legacy models in line with policy).

## Position on policy
There is **no formal organisational model-decommissioning policy** — appropriate
to the project's scale (a single classifier serving an internal curator tool).
Rather than claim one, I follow a lightweight, auditable process, described below.

## Model versioning
- Each trained model is saved as an **immutable, dated run folder** under
  `models/runs/` (e.g. `v1_2026-05-16/`) containing the model artefacts and a
  metadata file (embedding model, hyperparameters, training data, metrics).
- `models/runs/active.txt` is a **git-tracked pointer** to the run currently in
  production. Because it's in version control, **every change of live model is
  captured in the commit history** — a complete audit trail of which model was
  live, when, and by whom.

## Retiring a model (v1 → v2)
- A new model is trained and **validated on the held-out test set (issues
  105–114, unseen during training)** before any switch (see `notebooks/14_held_out_test.ipynb`).
- v1 is retired by **repointing `active.txt`** to v2 — a one-line, reversible
  change. The v1 run folder is **kept archived** (never deleted) so:
  - past predictions remain **reproducible** (you can re-run the exact model),
  - **rollback** is immediate if v2 underperforms,
  - the change is auditable.
- Retraining triggers and the v1→v2 criteria are documented in
  `docs/decisions/model_v1_state_and_retraining_plan.md`.

## Data-asset management / decommissioning
- **Superseded data** (e.g. out-of-scope source articles, stale prediction
  backfills) is removed from Supabase via **documented cleanup scripts**
  (`src/scraping/cleanup_existing_articles.py`, targeted delete scripts), not
  ad-hoc edits — so changes are repeatable and logged.
- **Curator decisions** are archived (not deleted) on the weekly reset into
  `curator_decisions_archive`, preserving the record while clearing the working
  view.
- Daily Supabase backups (`backup.yml`) provide a recovery point for the data
  assets.

## Compliance / audit (S6, S17)
- The data is **public web content (no PII)**, classified for an internal
  newsletter — low regulatory exposure, but GDPR principles are respected
  (minimal data, no personal data, EU-region storage).
- Change/operation/monitoring history is documented in
  `docs/deployment/deployment_challenges.md` (the running ops log) and the
  `docs/decisions/` folder.

## Summary for the discussion
*"We don't have a formal decommissioning policy at this scale, so I run a
lightweight, version-controlled process: immutable dated model runs, a
git-tracked `active.txt` pointer (full audit trail), retire-by-repointing with
the old run archived for rollback/reproducibility, and documented cleanup scripts
for stale data assets. Nothing is hard-deleted, so past predictions stay
reproducible and auditable."*
