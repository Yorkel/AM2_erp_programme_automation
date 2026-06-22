# Incident: classifier cold-start failure + blank-summary crash (2026-06-22)

Factual write-up for the AM2 report (Project 2 / live operation). A curator (Rachel) hit a hard error on the Draft tab on Monday morning. Investigation found the weekly pipeline had partially failed overnight: today's articles were unclassified, and many recent articles had no summary. Recovered the same day with no loss of curator work. Sits alongside [incident_2026_06_16_pipeline_failure.md](incident_2026_06_16_pipeline_failure.md) — a second live-operation incident, different root cause.

## Summary
The dashboard Draft tab crashed for a curator, and the current week showed no usable articles. Investigation found two independent faults:
1. The classifier workflow failed overnight because the HuggingFace model Space was asleep and did not respond to the health probe within the timeout, so today's 11 articles were never categorised and did not surface in the dashboard.
2. Many recent articles had blank summaries/tags (an enrichment gap); a missed null-guard let a pandas `NaN` reach a Streamlit text widget, which is the actual crash the curator saw.
Both were diagnosed and recovered the same day. No curator decisions were touched (174 decisions this week, including 65 made that morning, all intact).

## Symptoms (as reported by the curator)
- Draft tab threw a `TypeError` (`text_area_proto.value = widget_state.value`) at [dashboard/pages/draft.py:259](../../dashboard/pages/draft.py#L259).
- Triage showed "0 pending articles" for the current week.
- Categorise page showed articles with no category ("awaiting category") and tags rendering as the literal string `nan`.
- Curator's read: "things keep failing in front of curators."

## Root cause 1: HuggingFace classifier Space cold-start timeout
- The classify step (`src/pipeline.py --inference`) pulled 970 articles successfully, then called the model API at `yorkel-erp-classifier.hf.space` and failed:
  `Health probe attempt 1/3 failed: ... Read timed out (timeout=60)` → `RuntimeError: Could not reach .../health after 3 attempts`. Workflow run #39 failed in 5m40s at 04:54.
- **Isolation test:** the same Space answered a `/health` request in **0.6s (HTTP 200)** later the same day. So it was not down, not an auth fault, not a code fault — it was a **free-tier cold-start** that exceeded the probe budget (`COLD_START_TIMEOUT = 60`, `MAX_RETRIES = 3` in [classify_via_api.py:55-57](../../src/inference/classify_via_api.py#L55-L57)). The overnight cron slot is exactly when the Space is coldest.
- **Cascade:** because classify ended as "failed", the chained `drift` and `fairness` workflows (which gate on classify success) were skipped, and today's 11 articles stayed unclassified. The dashboard only surfaces classified articles, hence "0 pending / no articles from today".

## Root cause 2: blank summaries + missed null-guard → widget crash
- 57 of 78 recent articles had `NULL`/blank `summary` and `topic_tags` (the enrichment gap; the in-scrape summary sweep is `continue-on-error`, so when it does not run/complete it fails silently).
- The Draft page seeded its summary text box with `decisions...summary or art.get("summary") or ""`. Because pandas `NaN` is a **truthy float**, the `or` chain let `NaN` through and Streamlit rejected it as a widget value — the crash. The shared `clean_text()` guard ([dashboard/data.py:24](../../dashboard/data.py#L24)) existed and had been applied to the Excel export and display fields in a prior fix, but **this one widget-seeding line was missed**.

## Recovery actions (same day)
- Ran `src.scraping.sweep_summaries` from the dev container (Claude reachable there): **summaries 84 ok / 0 fail; tags 57 ok / 0 fail; topic sentences 57 ok / 0 fail.** Result: 0 blank summaries/tags for the week (13 legitimate "Summary unavailable" placeholders remain for body-extraction-blocked sources).
- Applied the missed `clean_text()` guard to the Draft text-box seeding so a future blank batch cannot crash the page.
- Confirmed the HF Space is warm, so re-running classify recovers today's 11 articles.

## Fixes / prevention (proposed)
- **HF Space reachability:** raise `MAX_RETRIES`/`COLD_START_TIMEOUT` with longer backoff; pre-warm the Space (`/health` ping) at the start of the scrape so it is awake by classify time; optionally auto-retry the classify workflow once on failure.
- **Make failures loud:** the in-scrape summary sweep is `continue-on-error`, so enrichment failure is silent — surface it.
- **Health check + self-heal:** a daily check that verifies today's articles are classified and summarised, alerts if not, and can re-run the failed step before a curator sees it.
- **Dashboard status banner:** show "today's articles still processing" instead of a raw stack trace.

## Reflection angle (for Louise to write up)
- Two live incidents in a week, both transient infrastructure faults (runner→Claude on 06-16; runner→HF Space cold-start on 06-22), both surfacing to curators rather than to me first. The recurring theme is **fragile free-tier dependencies + silent failure modes + no proactive monitoring**, not application logic.
- The honest gap: I fixed the *symptom* class (`clean_text`) on 06-16 but missed one call site, and I did not add monitoring after the first incident — so the second incident was found by a curator, not by me. The durable lesson is operational: alerting and self-healing matter as much as the model.
