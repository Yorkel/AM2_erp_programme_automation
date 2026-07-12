# Security Policy

This repository contains the ERP newsletter automation pipeline (scraping,
classification, enrichment, dashboard, monitoring). This document describes how
the project handles security and how to report a problem.

## Reporting a vulnerability

If you find a security issue (an exposed credential, an injection vector, an
access-control gap), please **do not open a public issue**. Instead, email the
maintainer (see the repository owner's profile) with:

- a description of the issue and where it is,
- steps to reproduce, and
- the potential impact.

You'll get an acknowledgement, and the issue will be triaged and fixed before any
public disclosure.

## How secrets are handled

- **No secrets in code or git.** All credentials are supplied at runtime via
  environment variables: a git-ignored `.env` locally (see `.env.example` for the
  variable names) and **GitHub Actions secrets** for CI.
- **Secret scanning.** `detect-secrets` runs via `.pre-commit-config.yaml` against
  `.secrets.baseline` so an accidental credential commit is caught before it lands.
- **`.gitignore` / `.dockerignore`** keep `.env`, Streamlit/Supabase secret files,
  and personal material out of the repository and the Docker image.
- **Separate stores per environment** — local dev, CI, and the deployed Space each
  hold their own credentials; none are shared through the repo.

## Access & deployment

- **Database access.** The dashboard and backend jobs currently authenticate with
  the Supabase service key (Row-Level Security is not yet enabled), so the shared
  dashboard password is the effective write gate. Moving the dashboard to a
  restricted/anon key with RLS write policies is a tracked hardening step (below).
- **Private model serving.** The classifier API runs on a Hugging Face Space; model
  access is mediated through the API/dashboard, not by sharing raw data or weights.
- **Input validation.** The serving API validates every request against typed
  Pydantic schemas (malformed input is rejected with `422`).
- **Pinned dependencies.** `requirements*.txt` pin exact, tested versions to reduce
  supply-chain drift; the deployed API uses a slim, separate dependency set.
- **Claude via proxy.** When the CI runner routes Claude calls through the Space
  proxy, the API key is forwarded over TLS in the request header and is **never
  stored or logged** on the Space; an optional `PROXY_TOKEN` header locks the proxy
  to the pipeline.
- **Polite scraping.** Scrapers send a descriptive User-Agent and throttle requests.

## Known hardening steps (not yet done)

These are tracked, not silently ignored:

- App-level authentication and rate limiting on the FastAPI service (currently
  relies on platform-level private hosting).
- Exporting/version-controlling Supabase Row-Level-Security policies.
- Automated dependency vulnerability scanning (e.g. `pip-audit` / Dependabot).
