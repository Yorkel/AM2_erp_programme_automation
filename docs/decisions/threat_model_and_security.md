# Threat Model & Security Frameworks

Security governance artefact. STRIDE over the system's trust boundaries, mapped to
the NCSC ML security principles and OWASP ML/LLM risks, with current controls and
honest gaps. Supports K4, K25, K27, S1, S32.

## Trust boundaries
1. **Scraper** — ingests external, untrusted web/RSS/Google-Alert content.
2. **Classifier API** — the HuggingFace Space (`/predict`, `/health`).
3. **Inference service** — FastAPI model server (Pydantic-validated).
4. **Data store** — Supabase (articles, predictions, curator decisions).
5. **LLM enrichment** — Claude API (summaries, tags, topic sentences).
6. **Dashboard** — Streamlit curator UI (password-gated writes).

## STRIDE
| Threat | Where | Risk | Control / status |
|---|---|---|---|
| **Spoofing** | API, dashboard | Unauthorised caller / curator | Opt-in Bearer token on `/predict` + `/metrics` (enforced when `CLASSIFIER_API_KEY` is set on the Space; off by default); password gate on dashboard writes (read-only until login). ⚠️ No per-user identity (shared password); API auth must be turned on by setting the key. |
| **Tampering** | Scraper, store | Malicious feed content; row tampering | Approved/blocked-domain filters + UK-content rule; Supabase service key server-side only; no client-side writes to source data. |
| **Repudiation** | Store | "Who changed this?" | Timestamps (`*_at`) on all tables; curator decisions archived weekly; git audit trail for model/version changes. |
| **Information disclosure** | Store, API, secrets | Data/secret leak | No PII (public content only, snippet-only); secrets in GitHub Actions / env, never committed; `detect-secrets` pre-commit hook. |
| **Denial of service** | API, scraper | Cold-start / flood; runaway scrape | Free-tier cold-start handled (pre-warm + retry + longer timeout); incremental `--since-last-run` scrape. ⚠️ No rate-limiting on `/predict`. |
| **Elevation of privilege** | Service, store | Service key misuse | Inference service is read-only over the model; Supabase service key isolated to backend jobs; dashboard uses a scoped path. ⚠️ No row-level security (acceptable for an internal tool). |

## NCSC "Principles for the security of machine learning" — mapping
- **Secure design / aware of ML-specific threats:** model classifies by content not
  source (no-meta variant) — reduces a data-poisoning/proxy attack surface.
- **Secure the supply chain:** pinned dependencies (`requirements.txt`); models
  loaded from versioned `models/runs/<id>/` artefacts. ⚠️ Adopt SafeTensors over
  pickle for any future shared artefacts.
- **Secure the data:** public-domain content only, no personal data; entity/URL
  stripping; minimal data retained (snippet + metadata).
- **Secure deployment & monitoring:** drift + data-quality monitoring; health
  endpoint; incident write-ups (16/22 June) with root-cause and prevention.

## OWASP ML / LLM risks
- **ML01 Input manipulation / data poisoning:** untrusted feed text reaches the
  model. Mitigated by content-based (no-meta) classification + curator-in-the-loop
  (no autonomous action). Residual risk accepted (assistive tool).
- **LLM01 Prompt injection** (Claude enrichment): scraped text is sent to Claude
  for summaries. ⚠️ No input/output filtering yet — a known next step; impact is
  low (output is curator-reviewed copy, not executed).
- **LLM06 Sensitive-information disclosure:** no secrets/PII in prompts (public
  article text only).

## Institutional context
Operates within **UCL's information-security governance** (institutional policies
for data handling and access). This is not an independently ISO 27001-certified
system; the framing is alignment with institutional controls, not certification.

## Honest gaps / next steps
- Rate-limiting + input-length bounds on `/predict`.
- Prompt-injection input/output filtering for the Claude enrichment step.
- SafeTensors for model serialisation; per-user dashboard identity if it scales.
- These are documented as deliberate, scale-appropriate deferrals for an internal,
  human-in-the-loop tool — not oversights.
