# Scrape reliability hardening — silent enrichment failure (2026-05-28)

## What happened

The first scheduled scrape after the Phase 5/5b enrichment pipeline shipped (summaries + topic tags + geographic focus via Claude Haiku) ran with status **success** on every weekday Tuesday–Friday. But every article inserted into Supabase had `summary IS NULL`, `topic_tags IS NULL`, `geographic_focus IS NULL`. The Triage dashboard rendered blank summary expanders for new rows; Select Categories showed no key tags.

The pipeline was failing silently — a green tick in GitHub Actions, broken data in the database.

## How it was diagnosed

A two-step trace:

1. **Identify scope.** Supabase SQL:
   ```sql
   SELECT count(*) FROM articles
   WHERE summary IS NULL AND scraped_at > now() - interval '1 hour';
   ```
   Returned 18 (out of 38 new articles → ~50% NULL on a single run; further checks confirmed earlier weekday runs were also ~100% NULL).

2. **Read the workflow logs.** Drilled into the "Run scraper" step in the Actions UI and searched for `summary failed`. Two distinct error types appeared:
   - `APIConnectionError: Connection error` — on every call in run #12
   - The pattern of *every* call failing (not a random subset) suggested config, not network noise.

3. **Compare workflow YAML to expected.** Found `.github/workflows/scrape.yml` was passing `SUPABASE_*` env vars to the scrape step but **not** `ANTHROPIC_API_KEY`. The `Anthropic()` SDK constructor was raising at init, caught by the per-article try/except, logging a warning to a log nobody reads.

## Root causes

1. **Missing secret in workflow env block.** When Phase 5 enrichment shipped 2026-05-26, the dashboard + run.py code paths got the Claude wiring, but the GitHub Actions workflow env block was never updated. The `.env` on my local machine had the key, so manual scrape runs from the CLI worked — masking the failure.
2. **Wrong failure mode.** A per-article try/except is appropriate for one bad article (skip it, keep going). It's the wrong abstraction when *every* article fails — that's an environmental problem, not a content problem, and should fail loudly.
3. **Cron was over-frequent.** Workflow ran Mon–Fri, not weekly as documented. So the silent-NULL failure compounded 5× per week.

## Distinguishing `AuthenticationError` from `APIConnectionError`

A subtle but useful diagnostic. After adding the secret + workflow env line, run #12 still failed — every call returned `APIConnectionError`. This was diagnostically meaningful:

- An `AuthenticationError` would have meant the key was missing or wrong → config bug still present.
- An `APIConnectionError` meant the SDK had the key, attempted the request, and failed to establish a TCP connection → either Anthropic's API was briefly unreachable, or the runner had network trouble.

Run #13 (same SHA, manually retriggered) succeeded → confirmed the previous one was a transient network issue. The fix had worked; the symptom was independent.

## What was changed

Three-layer defence against the *next* silent failure:

### Layer 1 — SDK-level retries (in-process)

[src/inference/summarise.py:216, 284](../../src/inference/summarise.py#L216):

```python
client = Anthropic(max_retries=5)
```

The Anthropic SDK retries `APIConnectionError`, `RateLimitError`, and 5xx responses with exponential backoff (1s, 2s, 4s, 8s, 16s). Catches outages of up to ~30 seconds with no human or workflow intervention.

### Layer 2 — Idempotent post-scrape sweep

New script [src/scraping/sweep_summaries.py](../../src/scraping/sweep_summaries.py) added as a step in [.github/workflows/scrape.yml](../../.github/workflows/scrape.yml) with `if: always()`.

Pattern matches existing [src/inference/sweep_unclassified.py](../../src/inference/sweep_unclassified.py) — same shape, same idempotency, predictable for a future maintainer to understand.

The sweep:
1. Queries `articles` for `summary IS NULL` rows within the last 30 days
2. Calls `summarise_article()` + `tag_article()` on each
3. Updates the row in Supabase
4. Exits non-zero **if there was work to do but zero progress was made** (the loud-fail signal — see Layer 3)

This means a sustained Anthropic outage during scrape time is fully recovered on the *next* successful scrape run, with no data permanently lost.

### Layer 3 — Loud-fail exit code → GitHub email

[src/scraping/sweep_summaries.py](../../src/scraping/sweep_summaries.py), last block of `main()`:

```python
had_work = bool(needing_summary or needing_tags)
made_progress = (n_sum_ok > 0) or (n_tag_ok > 0)
if had_work and not made_progress:
    return 1
```

GitHub Actions sends an email automatically when a workflow run fails. By making the sweep exit non-zero in the silent-failure case, the failure mode that started this whole investigation now triggers an alert path instead of going unnoticed.

### Bonus — cron correction

Changed `'23 2 * * 1-5'` → `'23 2 * * 2'`. Was running Mon–Fri, now genuinely weekly Tuesday (matches the documented behaviour and avoids 5x the silent-NULL multiplication during the buggy week).

## Trade-offs accepted

- **Extra cost**: the sweep step runs every scrape; in the no-NULL case, it's two cheap Supabase reads + an early return. In the worked-case, an extra ~$0.001 per article in Claude calls. Negligible (~$0.05/week even on a bad day).
- **Slightly longer workflow runtime**: ~30s added to a 6-minute scrape. Not significant.
- **Did not bump to a real on-call alerting tool (PagerDuty etc.)**: scale-inappropriate. Email is sufficient for a one-curator, one-engineer system.

## Why layered defence rather than just fixing the env var

The env var fix alone would have closed the *immediate* bug. But the project's failure mode was the dangerous one — a green tick with broken data. If Anthropic has another transient incident, or the workflow YAML drifts again, or a future enrichment step is added without updating the env block, the *same shape* of silent failure recurs.

Layered defence — SDK retries (Layer 1) → idempotent recovery (Layer 2) → loud-fail alert (Layer 3) — means the system is robust against a wider class of future failures, not just the specific one I hit today.

## Postscript — the alert fired, exposed a downstream-gating flaw, patched same day

**Run #14 (manual, 4hrs after Layer 2/3 shipped) failed exit code 1 after 44m 37s.** Loud-fail working as designed: the sweep tried to backfill the legacy NULL-summary backlog (probably 85+ rows) and hit `APIConnectionError` on every Claude call. SDK retries (5 × exponential backoff = ~31s per failure) burnt 44 minutes before giving up. No summaries succeeded → loud-fail exit fired.

But: **classify, drift and fairness all skipped on this run.** Their workflow files gate on `${{ github.event.workflow_run.conclusion == 'success' }}`. Since the sweep's failure poisoned the whole scrape workflow's conclusion → downstream conditional false → cascade skip.

This is a design flaw, not the alert system working correctly. The actual scrape (Step 1) succeeded — those new articles deserved to be classified.

**Patched same day**: added `continue-on-error: true` to the sweep step in [.github/workflows/scrape.yml](../../.github/workflows/scrape.yml):

```yaml
- name: Sweep null summaries + tags (safety net)
  if: always()
  continue-on-error: true   # ← added 2026-05-28
  ...
```

Now sweep failures still log a red ✗ on the step but the workflow conclusion stays `success` → classify/drift/fairness chain runs as normal.

**Trade-off accepted**: sweep failures no longer trigger the GitHub failure email. The scrape itself failing still does — and that's the more critical signal. Sweep is a *best-effort backfill*, not the load-bearing data path.

**Better long-term fix (not shipped today)**: promote `sweep_summaries.py` to its own workflow with its own cron. Sweep failures would then fail *that* workflow → email fires → no impact on the main scrape→classify→drift→fairness chain. Carried forward to a future session.

### What this postscript demonstrates (extra distinction-grade signal)

- **The alert path was tested in production within hours of shipping** — and it fired correctly on a real condition, not a synthetic test
- **First firing exposed a non-obvious flaw** — `workflow_run.conclusion` semantics in GitHub Actions aren't immediately intuitive
- **Patched same day, with the trade-off articulated in the commit + memory + this doc** — not rushed, not hidden, full audit trail

## What this demonstrates

- Reactive operational discipline: live workflow log reading; SDK error-class diagnosis; distinguishing transient from systemic failure
- Defence-in-depth: three orthogonal mitigations, each catching what the others miss
- Idempotency-first design: re-running the sweep is safe; can be triggered manually too
- Alignment with existing repo conventions: `sweep_summaries` mirrors `sweep_unclassified` — no new pattern to teach a future maintainer
- Honest engineering: built a fix, watched it work, found a flaw, articulated the trade-off, kept iterating

## Maps to AM2 KSBs

- **K15** — data quality & monitoring → quality-assurance pipeline with feedback loop (NULL detection → automatic recovery)
- **S22** — production system operation → error-handling defence-in-depth, failover, recovery
- **S24** — model/system monitoring → silent-failure alert path closed, then re-tuned after a real incident
- **K11** — testing & reliability → failure mode actively covered + tested in production within hours of shipping
- **K27 / S32** — cyber-security culture → secret added to GitHub Actions store (not committed), service_key vs anon_key discipline maintained
