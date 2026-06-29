# Problem: GitHub runner cannot reach the Claude API (recurring enrichment failure)

Factual write-up for the AM2 report (Project 2 / live operation + risk decisions).
A systemic infrastructure constraint that broke the weekly enrichment repeatedly,
how it was diagnosed, the options weighed, and the fix. Sits with
[incident_2026_06_16_pipeline_failure.md](incident_2026_06_16_pipeline_failure.md)
and [incident_2026_06_22_classifier_cold_start.md](incident_2026_06_22_classifier_cold_start.md).

## Summary
For several consecutive weeks the scheduled pipeline produced articles with **blank
summaries, tags and topic sentences**. Scraping and classification worked; only the
**Claude (Anthropic) enrichment** failed. The confirmed cause is that the **GitHub
Actions runner cannot establish a connection to `api.anthropic.com`**, while it
reaches every other service (HF classifier Space, Supabase, the web) fine. This
could not be fixed on the runner — including the self-heal we had added, because it
runs on the same runner — so it recurred weekly and was rescued manually each time.

## Timeline
- **16 June:** first occurrence. Enrichment failed with `APIConnectionError`; the
  scheduled job retried for ~1 hour and still failed. Recovered by running the
  enrichment manually from the dev container (which *can* reach Claude).
- **22 June:** blank summaries again (alongside a separate, since-fixed HF Space
  cold-start). Added monitoring: a health check + self-heal + dashboard banner.
- **29 June:** recurred — 51 of 52 articles blank. The health check correctly
  caught it and failed loudly, but the self-heal could not recover it.

## Symptoms
- This week: 51/52 articles with NULL `summary`, `topic_sentence`, `topic_tags`;
  0 unclassified (classification fine); they show in Triage but unenriched.
- Health check workflow concluded **failure**; scrape + classify concluded success.

## Root cause (confirmed from run logs)
Pulled from the failed health-check run (GitHub Actions API, run 28357314531):
```
ERROR: Claude unreachable before sweep: APIConnectionError: Connection error.
  needing summary: 84
UNHEALTHY: 0 unclassified, 51 blank summaries this week — self-heal did not fully recover.
```
- It is a **connection** failure, **not** authentication — the API key is present
  (`ANTHROPIC_API_KEY: ***`).
- The same runner reaches the HF Space and Supabase, so general egress works.
  **Only `api.anthropic.com` is unreachable from GitHub's runners** — the classic
  signature of a broken IPv6 route (the runner resolves Anthropic to an IPv6
  address it cannot reach) and/or Anthropic refusing GitHub's shared CI IP ranges.
- The dev container and Streamlit Cloud both reach Claude fine, which localises the
  fault to the GitHub runner environment, not the key, account, or Anthropic itself.

## Why it was hard to fix
- The obvious safety nets don't help: **retries** (it failed for an hour on 16
  June), and the **self-heal sweep runs on the same runner**, so it hits the same
  wall. Monitoring could *detect* it but not *cure* it.
- The fix therefore has to change *where* or *how* Claude is reached — not add more
  resilience on the runner.

## Options considered
| Option | Approach | Effort | Cost / dependency |
|---|---|---|---|
| A4. Force IPv4 on the Anthropic client | Bind the HTTP client to `0.0.0.0` so it can't take the broken IPv6 route | Tiny | none — try first |
| A1. Claude via AWS Bedrock | Runner reaches AWS, bypassing api.anthropic.com | Low-med | AWS account + per-token cost |
| A2. Claude via Google Vertex | Same via GCP | Low-med | GCP account |
| A3. Self-hosted runner | Run the workflow on a Claude-reachable machine | Med | a host |
| B1. Render Cron Job | Run enrichment off-runner on Render (reaches Claude) | Med | Render account |
| B2. Supabase Edge Function + pg_cron | Enrichment next to the data, scheduled by Supabase | Med-high | rewrite in TS |
| C1. Enrichment endpoint on the HF Space | Runner calls the Space (reachable); Space calls Claude | Med | verify Space→Claude |

## Decision
Try the **cheapest, no-infra fix first (A4 — force IPv4)**, since the symptom
matches a runner IPv6-routing problem and it costs nothing to try. A single shared
client factory (`src/inference/anthropic_client.py`) binds the HTTP client to IPv4
and is used at every Claude call site. If A4 fails, fall back to **A1 (Bedrock)** or
**B1 (Render cron)** as the durable off-runner fix.

## Verification
Because a `GITHUB_TOKEN` is available, the run logs are read directly via the GitHub
Actions API rather than waiting for the weekly cycle: push → manually run the health
check → inspect the log for `APIConnectionError` (gone = fixed; present = escalate).

## Outcome
- ❌ **A4 (force IPv4) did NOT work.** The verification scrape on the A4 commit
  still logged `APIConnectionError: Connection error` on every Claude call
  (tag_article, summary, and the sweep probe); the new articles came in blank.
  So the cause is **not** IPv6 routing — it is a harder network block between
  GitHub runners and `api.anthropic.com` (Anthropic refusing GitHub's shared CI
  IP ranges, or a runner egress firewall). A4 is ruled out.
- ✅ **Resolution — a variant of C1 (route Claude via the HF Space).** The Space
  was the natural host: the runner *already* calls it for classification every
  week (so runner→Space is proven), and `/claude_probe` confirmed Space→Claude
  works (`{"reachable":true,"status":401}` — 401 = reached Anthropic, only the
  deliberately-omitted key rejected). Rather than duplicate the enrichment logic
  in a new endpoint, the Space hosts a **transparent proxy** at `/v1/messages`
  that forwards Claude requests upstream. The runner then sets
  `ANTHROPIC_BASE_URL=https://yorkel-erp-classifier.hf.space`, which the Anthropic
  SDK reads automatically, so **every** Claude call (summary, tags, topic
  sentence) routes runner→Space→Claude with **no change to the enrichment code**.
  - **Why a proxy, not a stored-key endpoint:** the caller's API key is forwarded
    in the `x-api-key` header over TLS and is **never stored or logged** on the
    Space. The Space cannot spend the key's budget (it holds no key); a public
    stored-key endpoint could. Optional `PROXY_TOKEN` header gate locks the proxy
    to our runner (open-relay hardening; not required for key safety).
  - **Zero new infrastructure / zero cost:** reuses the existing classifier Space.
    No AWS/GCP account, no Render service, no rewrite — A1/B1 kept as fallback.
- Verified end-to-end on **29 June**: a real Haiku call through the proxy returned
  the expected sentinel (`CLAUDE VIA PROXY → PROXY_OK`). Production confirmation =
  the next scheduled/manual run's "Sweep null summaries + tags" step reporting
  `summaries N ok / 0 fail` instead of `APIConnectionError`.
- Interim recovery (still works): `python -m src.scraping.sweep_summaries` from a
  Claude-reachable host (dev container / Streamlit Cloud).

## Reflection (for the AM2 write-up)
- **K11 / S22 (platform & operation):** a real lesson that free, shared CI
  infrastructure carries hidden network constraints — a dependency can be reachable
  from one environment and not another, and "it works on my machine" is literally
  the failure mode here.
- **S24 / robustness:** monitoring that only *detects* isn't enough when the
  self-heal shares the failing component; resilience has to be designed at the right
  layer (where Claude is actually reachable).
- **K15 / S19 (risk & scalability decisions, Distinction):** the fix was chosen by
  cost/effort, escalating only as evidence required. The free IPv4 change was tried
  first and **disproven by the logs** (ruling out IPv6 routing). Rather than then
  jump to paid infrastructure (Bedrock/Vertex) or a new service (Render cron), the
  resolution **reused infrastructure that already existed and was already trusted**
  — the classifier Space the runner talks to every week — adding only a thin proxy.
  A defensible, scale-appropriate decision: the cheapest durable option that reused
  proven components, with paid routes kept as a documented fallback rather than
  over-engineered in pre-emptively.
- **Security in the design (K11/S22):** the proxy forwards the key over TLS and
  never persists it, a deliberate choice over a stored-key endpoint so the public
  Space can never be made to spend the key's budget.
- **Diagnosis discipline:** the cause was confirmed from the actual run logs
  (connection vs auth), not guessed — the same isolation approach as the earlier
  incidents.
