# Publication Checklist

Run through this before making the repository public (or publishing a clean
mirror). It's a one-page gate to avoid leaking secrets or personal material.

## Secrets & credentials
- [ ] No real secrets in tracked files (`.env`, configs, notebooks, docs).
- [ ] `.env`, `.env.*`, `.streamlit/secrets.toml`, `secrets.toml` are gitignored
      (only `.env.example` is tracked).
- [ ] `detect-secrets` baseline is current and the pre-commit hook runs
      (`.pre-commit-config.yaml`, `.secrets.baseline`).
- [ ] **Git history scanned** for secrets, not just the working tree
      (e.g. `detect-secrets scan $(git rev-list --all | head)` or `gitleaks`).
- [ ] Any key that was ever committed is treated as compromised and **rotated**.

## Personal / assessment material kept out
- [ ] `AM2 now/`, `AM2 evidence prep/`, `x_assessment/`, and any other personal or
      EPA-assessment folders are gitignored and **not** in the published tree.
- [ ] No internal handover/review notes left at the top level.

## Data hygiene
- [ ] No raw scraped corpora, operational DB dumps, or generated artefacts tracked
      (`backups/`, `outputs/`, `data/modelling/classified_articles.csv` are ignored).
- [ ] Historic data snapshots in git history don't expose private emails, internal
      links, or tracking parameters (decide: sanitise history or publish a clean
      snapshot mirror).

## Documentation & licence
- [ ] `README.md` reflects the real system (architecture, results, how to run).
- [ ] `LICENSE` present and correct.
- [ ] `SECURITY.md` and `DATA.md` present and accurate.
- [ ] Deployment docs name the current target (Hugging Face Space; Render is legacy).

## Final pass
- [ ] Tests pass and CI is green (`.github/workflows/tests.yml`).
- [ ] Commit history is presentable, or a clean public mirror is published instead.
- [ ] A fresh `git clone` + `pip install -r requirements.txt` works for a stranger.
