# Incident: weekly newsletter pipeline failure (2026-06-16)

Factual write-up for the AM2 report (Project 2 / live operation). Two independent faults, both traced to the same root change, recovered with no loss of curator work.

## Summary
The weekly newsletter pipeline failed to produce last week's issue. The scheduled scrape ran for over an hour and was cancelled; the curator dashboard showed "0 pending articles" for the newsletter week. Investigation found two separate faults, both downstream of a recent dependency change. Both were diagnosed and fixed the same day, and last week's issue was fully recovered (88/88 articles classified and summarised) with curator decisions untouched.

## Symptoms
- Scheduled scrape workflow (run #25) cancelled after 1h 5m (exit code 143). Every article's enrichment step (summary, tags, topic sentence) logged `APIConnectionError: Connection error`.
- Because the scrape ended as "cancelled" rather than "success", the chained `classify`, `drift` and `fairness` workflows (which gate on scrape success) were all skipped, so nothing was categorised.
- The dashboard showed **0 pending articles** for the newsletter week, even though the data was present.

## Root cause 1: GitHub runner could not reach the Claude API
- The enrichment step calls Anthropic Claude (summary, tags, topic sentence). Every call failed at the transport level (`APIConnectionError`), and with 5 retries per call the job ran to a 1-hour cancellation.
- **Isolation test:** from a separate environment (the dev container) a minimal Claude call **succeeded**, the API key was valid (108 chars, `sk-ant...`), the account had credit, and the SDK was fine. A raw HTTPS request to the API returned 401 (reachable). So the fault was specific to the **GitHub Actions runner** being unable to connect, not Claude, the key, or the account (a connection error, not an auth or credit error).
- The 404 links the curators noticed (e.g. Belfast Telegraph) were a **red herring**: a sample of the failing URLs returned HTTP 200; only a few anti-bot sources 403, and the log error was uniformly the Claude connection error, not a 404.

## Root cause 2: dashboard date-parsing regression
- After the data was recovered, the dashboard still showed 0 pending for the week. The data layer was correct (88 articles with `week_number = 24`, only 17 already decided, so 71 genuinely pending).
- The bug was in `dashboard/app.py`: it parsed the ISO `article_date` values (`2026-06-11`) with `dayfirst=True`. On the upgraded pandas, that **mangles ISO dates** (11 June becomes 6 November) and produced 564 invalid (NaT) dates out of 913, so the week filter matched nothing.
- Both faults trace to the same recent change: the `requirements.txt` dependency **pinning**, which bumped pandas (the date bug) and likely changed the runner's transitive HTTP stack (the connection bug).

## Diagnosis approach
- Read the actual workflow logs rather than guessing; identified the uniform `APIConnectionError`.
- Tested each layer in turn (network reachability, key validity, account credit, SDK) to localise the fault to the runner rather than Claude or the account.
- Queried Supabase directly to prove the data was present and correctly week-numbered, isolating the dashboard fault from the data.
- Replicated the dashboard's exact date pipeline against the real data to pinpoint the `dayfirst=True` mangling, and verified the corrected parse restored all 88 articles with 0 NaT before changing any code.

## Fixes and recovery
1. **Recovered this week's content off the broken runner.** Because Claude worked from the dev container and `sweep_summaries.py` is idempotent (fills only missing/`Summary unavailable` fields, writes only to `articles` enrichment columns, never touches `curator_decisions`), it was run from there to backfill all missing summaries, tags and topic sentences directly into Supabase, bypassing GitHub entirely. Result: 0 missing summaries; curator decisions unchanged (134).
2. **Ran classify manually.** classify does not call Claude, so it was dispatched manually (its `workflow_dispatch` trigger bypasses the scrape-success gate). All 913 articles classified.
3. **Fixed the dashboard date bug** with a one-line change in `dashboard/app.py` (removed `dayfirst=True` so ISO dates parse correctly), verified against real data.

## Outcome
Last week's issue fully recovered: 88/88 articles classified, summarised, with topic sentences and tags; dashboard displaying correctly; no curator work lost.

## Lessons and preventive actions
- **A single dependency change caused two separate production failures.** Pin and upgrade dependencies cautiously, and test the live path (runner + dashboard) after, not just the model.
- **Inline enrichment was a single point of failure:** a Claude outage blocked the whole pipeline because enrichment ran inside the scrape and the downstream steps gated on it. Preventive actions: decouple enrichment from scrape so scraping and classification proceed without Claude; add a fail-fast Claude preflight (so the job exits in seconds rather than retrying for an hour); add a fallback provider (GPT).
- **Idempotent, side-effect-scoped jobs enable safe recovery.** Because the enrichment job only fills missing fields and touches no curator data, it could be safely re-run from a healthy environment. This is a design property worth preserving.
- **Diagnosis discipline matters:** distinguishing a transport error from an auth/credit/code error, and proving the data was present before blaming the dashboard, avoided chasing the wrong cause (the 404 links).

## KSB mapping (for the appendix)
Monitoring and robustness (S24); analysis and problem-solving / evaluating from logs and test data (K19); change management (K14); data governance / not overwriting curator data (K24, B4); operating under technical complexity and uncertainty (B5); platform and reliability decisions (K11, S22).
