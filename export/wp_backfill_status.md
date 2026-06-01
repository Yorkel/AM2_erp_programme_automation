# WP Backfill Status — Hard-sources Re-test Backlog & Section 8 Gap Review

Companion document to `docs/pipeline_decisions.md`. Read that first.

This is a **planning / feasibility document only**. No code has been run, no
scrapes have been re-attempted, no Supabase rows written, and no schema has
been altered. Every item below that requires a new dependency, a paid
service, or a schema change is flagged for explicit user approval.

---

## PART 1 — Hard-sources feasibility re-test backlog

For each source previously dropped or contributing zero, the table below
records: the original blocker (from `pipeline_decisions.md` §4, §5, §11
and §13), the rescue method recommended by the scraping knowledge guide
(§6), an effort estimate, any dependency / cost flag, and a judgement on
whether the methodological gain is worth the cost.

### Ireland

| Source | Original blocker | Rescue method | Effort | Dependency / cost flag | Worth doing? |
|---|---|---|---|---|---|
| Irish Times | Paywalled — 0 usable articles (§4) | UCL Library institutional access, then authenticated Playwright session | High — requires librarian liaison, credential handling, session cookie management, plus Playwright build-out | FLAG: UCL Library access negotiation + Playwright dependency + secrets-in-CI policy review. User approval required. | **MAYBE.** Only worthwhile if Irish Times is methodologically essential to the cross-country comparison. Given that the empty `ed_media` slot in Ireland is itself a documented structural finding (§7), the analytical cost of "fixing" it is non-trivial — it would partially erase the finding. Defer unless reviewers specifically request it. |
| TASC | Low yield — only 8 articles matched education (§4) | Low-effort re-test: re-run existing scraper, broaden keyword filter, recount | Low — existing scraper, no new dependency | None | **NO.** 8 articles after a generous filter is genuinely too thin to constitute a "source" at the same granularity as ESRI (134). Re-testing will not change the underlying signal. Park unless TASC publishes a dedicated education stream. |
| NCSE | Low yield — only 26 articles (§4) | Low-effort re-test: re-run existing scraper, confirm count, optionally include under a narrower remit | Low — existing scraper | None | **MAYBE.** 26 is borderline. If NCSE were placed under a new `advocacy` or specialist category (rather than competing with ESRI/ERC in `think_tank`/`research_org`), 26 articles becomes defensible. Tied to the §14 advocacy-category decision, not a pure scraping question. |
| Children's Rights Alliance | Deferred — no matching category at the time (§4, §14) | Low-effort re-test once `advocacy` / `civil_society` category is formally added | Low — taxonomy decision is the blocker, not scraping | None for scraping itself. FLAG: depends on §14 category-expansion decision which would require NMF retrain. | **YES (conditional).** This is the cheapest "rescue" on the list — the blocker was never technical. If the advocacy category is approved (parallel to Children in Scotland for Scotland), CRA should be added in the same change. No standalone approval needed beyond the category decision. |
| NCCA | Cloudflare 403 blocks all automated access (§4) | Playwright with realistic browser fingerprint first; if that fails, paid scraper (ScrapingBee / Bright Data ~£30-50/mo) | Medium for Playwright attempt; High if paid fallback is required | FLAG: Playwright dependency (user approval). FLAG: paid scraper subscription and recurring cost (user approval). | **NO** for now. NCCA is curriculum-focused (similar reasoning to Education Scotland being de-prioritised in §5). Curriculum updates are not the policy-discourse signal the NMF model is built to surface. The cost/benefit does not justify a paid service. Revisit only if a curriculum-specific analysis is commissioned. |

### Scotland

| Source | Original blocker | Rescue method | Effort | Dependency / cost flag | Worth doing? |
|---|---|---|---|---|---|
| TES Scotland | Fully paywalled (§5) | UCL Library institutional access, then authenticated Playwright | High — same constraints as Irish Times | FLAG: UCL Library access + Playwright dependency + credentialled CI. User approval required. | **MAYBE.** Same trade-off as Irish Times: rescuing TES Scotland partially undoes the finding (§7) that Scotland has no free education journalism. Pursue only if a reviewer flags the empty `ed_media` slot as a fatal weakness rather than a finding. |
| Education Scotland | JS-rendered — `requests` returns empty shell (§5) | Playwright (~1 day setup + ongoing CI compute cost) | Medium — single scraper rewrite once Playwright is available | FLAG: Playwright dependency, runtime cost in GH Actions, user approval required. | **NO.** Already explicitly judged in §5: content is "primarily curriculum updates, not policy discourse" and the infrastructure cost is "not justified for this source". Re-confirming that judgement here. |
| Audit Scotland | Not education-focused — out of scope (§5) | N/A — not a scraping problem | N/A | None | **NO — out of scope.** Audit Scotland audits public spending generally, not education policy. It should not have been on the backlog in the first place; recording it here explicitly to close it out. |
| COSLA | Cloudflare 403 (§5) | Playwright with realistic browser fingerprint first; if that fails, paid scraper (ScrapingBee / Bright Data ~£30-50/mo) | Medium for Playwright attempt; High if paid fallback is required | FLAG: Playwright dependency (user approval). FLAG: paid scraper subscription (user approval). | **MAYBE.** Strongest case among the Cloudflare-blocked Scottish sources: COSLA's Children and Young People stream is genuinely education-relevant local-government discourse and would partly fill the gap left by the missing `ed_media`/`local_gov` category. Try the free Playwright route first; only escalate to paid scraping if the Playwright attempt is also blocked. Recommend as the first Playwright pilot. |

### Other

| Source | Original blocker | Rescue method | Effort | Dependency / cost flag | Worth doing? |
|---|---|---|---|---|---|
| TheJournal.ie | In pipeline, contributes 0 — login wall after rate-limit (§4, §11) | Already kept in weekly pipeline on the assumption the wall is temporary; a deliberate rescue would mean authenticated Playwright with a TheJournal.ie account | High — requires account, ToS review, credentialled CI, and Playwright | FLAG: ToS / account-of-record concerns; Playwright dependency; user approval required. | **NO.** Two reasons: (1) the wall may genuinely be temporary and the current "keep in pipeline, observe" approach is the cheapest possible rescue; (2) authenticated scraping against ToS is a policy escalation that should not be undertaken to recover a single Irish ed-media source when the empty slot is itself a finding (§7). |
| UK Parliament Education Select Committee | Committees API returns metadata only; body text only in PDFs (§13) | `pdfplumber` over the PDF URLs returned by the API | Medium — API integration is straightforward; PDF parsing is well-understood but variable per-document | FLAG: `pdfplumber` is a new project dependency. User approval required. | **MAYBE.** This is the strongest "rescue" candidate on the whole backlog because the data exists, is non-paywalled, and only needs a parser. But adopting it triggers two follow-on questions: (a) a new `parliament` source category (see §14 — would require NMF retrain), and (b) whether select-committee PDFs are the right "shape" of document for an NMF trained on web articles. Recommend as a scoped spike (parse 5–10 reports, eyeball topic fit) before any commitment. |

### Effort key

- **Low** — existing scraper, no new dependency, no new category.
- **Medium** — one scraper rewrite, or one new well-understood dependency (`pdfplumber`).
- **High** — Playwright infrastructure, credentialled access, paid service, or taxonomy + model retraining downstream.

### Rescue-method shortlist

The backlog clusters around three distinct asks. Bundling them simplifies user approval:

1. **Playwright dependency** (covers Education Scotland, NCCA-first-attempt, COSLA-first-attempt, and any future authenticated-paywall work). One approval, multiple downstream uses.
2. **`pdfplumber` dependency** (covers the Education Select Committee work and is reusable for any future PDF-only source).
3. **Paid scraper subscription** (only triggered if Playwright fails on COSLA / NCCA). Distinct, larger ask — keep it separate.

---

## PART 2 — Section 8 gaps: should atlas-ed-data adopt these?

Section 8 of `pipeline_decisions.md` documents the current architectural
choices. The questions below are gaps in that architecture worth a
yes / no / maybe decision.

### 1. URL-exact dedup only — should we add content-hash / MinHash near-duplicate detection?

**MAYBE.** The current `_postprocess()` deduplicates on URL only (§9, point 4). This is genuinely vulnerable to near-duplicates: gov.ie press releases that get re-posted with a tracking parameter, Schools Week articles that appear under both a category URL and a tag URL, and weekly inference files which §8 explicitly states are *not* cross-deduplicated. A SHA-256 content hash on normalised text is cheap (no new dependency, ~10 lines) and would catch byte-identical duplicates immediately. MinHash / shingling for true near-duplicates is heavier and probably overkill at the current corpus size (5,200 articles total). **Recommendation:** adopt content-hash dedup as a free win; defer MinHash unless near-duplicate contamination is observed in topic outputs. No approval flag (no new dependency, no schema change if hash is computed in-memory and not persisted).

### 2. No language filter — should we adopt fasttext `lid.176`?

**NO** (keep current approach). §9 already documents a deliberate choice: Irish-language articles are **flagged, not removed**, using function-word frequency, and the `language` column is built to be swapped to `langdetect` later. fasttext `lid.176` would be more accurate but is a heavier dependency (~125MB model file) and would only refine a column the project already has. The current threshold-based heuristic is good enough for the documented use case (flag `ga`, keep in dataset as a finding about bilingual discourse). **Recommendation:** revisit only if Scots Gaelic / Welsh become in-scope — at that point `langdetect` (lighter than fasttext) is the documented next step, not fasttext. No approval flag.

### 3. Add `backfill_run_id` column on `articles_raw`?

**YES — but FLAG: SCHEMA MIGRATION, user approval required.** Currently `articles_raw` has no way to attribute a row to a specific backfill execution (the analysis-side `articles_topics` and `drift_metrics` tables both have `run_id` per §11, but the raw table does not). A `backfill_run_id uuid` column would let us answer "which rows did the 2026-05-30 re-scrape touch?" and would make rollback of a bad run tractable — currently the only option after a bad backfill is manual surgery by URL. This is a small, additive migration (nullable column, backfilled to a sentinel for existing rows). **Approval needed for:** the migration itself, plus a decision on whether to retro-stamp existing rows with a sentinel like `pre-tracking` or leave them NULL.

### 4. Add `source_category` column on `articles_raw`?

**MAYBE — FLAG: SCHEMA MIGRATION, user approval required.** The `type` column already exists on `articles_raw` (§11) and carries the §15 taxonomy values (`government`, `think_tank`, etc.). A separate `source_category` would only be justified if we need a second axis of categorisation — e.g. distinguishing the §15 type from a finer-grained sub-category, or recording a per-article topical category (curriculum vs. policy vs. workforce) alongside the source-level type. **Without that second axis being defined**, this column is redundant with `type`. **Recommendation:** defer until the use-case is articulated. If the intent is "let me filter Schools Week articles into curriculum vs. policy", that is an analysis-side concern and belongs on `articles_topics`, not `articles_raw`. Approval would be required for both the migration and the prior taxonomy work.

### 5. upsert-on-url overwrites silently — keep or version?

**KEEP, with one caveat.** Silent overwrite is the correct default for this project because (a) the scrapers are the source of truth for raw text, (b) the §17 text-quality fixes (22 March 2026) explicitly relied on re-scraping and re-seeding to overwrite previously-bad text, and (c) versioning every raw-text revision would balloon row count without analytical benefit (the analysis layer already has `run_id` for that). The one caveat: silent overwrite combined with no `backfill_run_id` (gap 3) means an accidental destructive run is invisible after the fact. **Recommendation:** keep upsert-on-url, but adopt gap 3 (`backfill_run_id`) so that overwrites are at least *attributable* after the fact. No new approval flag for keeping the current behaviour; the approval flag sits on gap 3.

---

## Footer

- **Generated by:** the `wp-backfill` workflow on [timestamp at run].
- **Nothing committed to git.** This document is a planning artefact; no code, scraper, or config has been changed by the workflow that produced it.
- **No Supabase writes.** No rows were inserted, updated, or upserted to `articles_raw`, `articles_topics`, or `drift_metrics` as part of generating this document.
- **No schema migrations applied.** All schema-change proposals in Part 2 are recommendations only; the live Supabase schema is unchanged.

### Next-step gates requiring explicit user approval

1. **Any non-dry-run backfill** of atlas-ed-data sources — including any re-test of dropped sources listed in Part 1.
2. **Playwright dependency** — required before pursuing Education Scotland, NCCA, COSLA, or any authenticated-paywall rescue.
3. **`pdfplumber` dependency** — required before pursuing the UK Parliament Education Select Committee work (§13).
4. **Paid scraper subscription** (ScrapingBee / Bright Data, ~£30–50/mo) — required only if Playwright attempts on COSLA / NCCA fail and the source is still considered worth pursuing.
5. **UCL Library institutional-access negotiation** — required before any rescue of Irish Times or TES Scotland.
6. **Any `articles_raw` schema migration** — explicitly including the Part 2 gap 3 (`backfill_run_id`) and gap 4 (`source_category`) proposals.
7. **Any taxonomy expansion** that triggers an NMF retrain — including the §14 advocacy / union / parliament categories referenced by the Children's Rights Alliance and Education Select Committee entries.
