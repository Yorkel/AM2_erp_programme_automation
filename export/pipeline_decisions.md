# AtlasED — Pipeline Decisions & Dataset Summary
UCL Institute of Education | Updated 18 March 2026

---

## 1. Dataset design (Option 2)

| | Training | Inference (historical) | Inference (live) |
|---|---|---|---|
| **England** | 1 Jan 2023 to 31 Dec 2025 *(reference distribution)* | Not applicable *(England trains; inference starts 2026)* | 1 Jan 2026 onwards — weekly, every Friday from 15 Jan 2026 |
| **Scotland** | None *(inference only by design)* | 1 Jan 2023 to 31 Dec 2025 *(full historical batch)* | 1 Jan 2026 onwards — weekly, every Friday from 15 Jan 2026 |
| **Ireland** | None *(inference only by design)* | 1 Jan 2023 to 31 Dec 2025 *(full historical batch)* | 1 Jan 2026 onwards — weekly, every Friday from 15 Jan 2026 |

> **Rationale:** NMF trained on England corpus only (K=30). Inference applied to Scottish and Irish documents using English model weights. This allows JSD and KL asymmetry to measure cross-national divergence from the English reference distribution.

> **Known gap:** 1–14 Jan 2026 not covered by batch or weekly pipeline. Documented in corpus notes.

---

## 2. Training cutoff and versioning

**Decision:** Articles published up to 31 December 2025 form the training corpus. Articles from 1 January 2026 onwards are inference data.

**Rationale:** This gives a clean 3-year training window (Jan 2023 – Dec 2025). Simulated weekly inference batches are then created from Jan 2026 onwards to test the pipeline before automated weekly runs begin in March 2026.

**Where enforced:** `TRAINING_CUTOFF = date(2025, 12, 31)` and `TRAINING_COUNTRIES = {"eng"}` in `src/run.py` — Scotland and Ireland always route to `data/inference/` regardless of date range.

**Training data versioning:** The merged training dataset is versioned as `training_data_v1.csv`. Future retraining produces `training_data_v2.csv` etc. This allows the deployed model to be clearly tied to the dataset it was trained on.

---

## 3. England — sources and article counts

### Source selection

Six sources covering government, think tanks, research organisations, a funder, a professional body and education journalism:

- **GOV.UK (DfE and arm's-length bodies)** — primary government voice; filtered post-scrape to core education bodies only (DfE, Ofsted, Ofqual, ESFA, Office for Students, Standards and Testing Agency, Institute for Apprenticeships, Skills England). Approximately 350 articles excluded where education is framed as international relations, economic growth, or operational delivery rather than domestic system governance.
- **EPI** — leading education policy think tank
- **Nuffield Foundation** — major education research funder
- **FFT Education Datalab** — leading data-driven education research organisation
- **Foundation for Educational Development (FED)** — professional body perspective
- **Schools Week** — primary free education journalism source covering policy developments

**What is deliberately excluded:** International education bodies (OECD, UNESCO), higher education-focused outlets, and employer/skills-focused organisations.

### Training data: Jan 2023 → Dec 2025

| Source | Category | Articles |
|---|---|---|
| Schools Week | ed_media | 2,741 |
| DfE (GOV.UK) | government | 679 |
| FFT Datalab | research_org | 202 |
| EPI | think_tank | 111 |
| Nuffield Foundation | funder | 106 |
| FED | prof_body | 104 |
| **Total** | | **3,943** |

### Category distribution

| # | Category | Articles | % |
|---|---|---|---|
| 1 | government | 679 | 17% |
| 3 | think_tank | 111 | 3% |
| 4 | funder | 106 | 3% |
| 5 | research_org | 202 | 5% |
| 6 | prof_body | 104 | 3% |
| 7 | ed_media | 2,741 | 69% |
| | **Total** | **3,943** | |

### Weekly inference: Jan 15 → Mar 13 2026

17–29 articles per week. 207 total across 9 weeks.

---

## 4. Ireland — sources and article counts

### Historical batch: Jan 2023 → 31 Dec 2025

| Source | Category | Method | Raw articles | After post-processing | Notes |
|---|---|---|---|---|---|
| Gov.ie (Dept of Education) | government | HTML (search page) | 820 | 799 | Press releases + publications. Migration date issue (see §11). |
| ESRI | think_tank | HTML | 137 | 134 | Education-filtered news + publications. |
| Teaching Council | prof_body | WP API | 36 | 36 | Admin/maintenance posts filtered during scraping. |
| ERC | research_org | WP API | 42 | 34 | ~3 Irish language articles. Some empty text articles dropped. |
| Education Matters | ed_media | WP API | 37 | 33 | All content types (yearbook, blog, news). |
| TheJournal.ie | ed_media | HTML | 163 | **0** | Login wall blocks text extraction (see §11). Kept in pipeline for weekly scrapes. |
| RTÉ News | ed_media | HTML | 0 | 0 | All articles are from 2026. No archive. Useful for weekly scrapes only. |
| **Total** | | | **1,235** | **746** | |

### Category distribution (after post-processing)

| # | Category | Ireland source(s) | Articles | % |
|---|---|---|---|---|
| 1 | government | Gov.ie | 799 | 77% |
| 3 | think_tank | ESRI | 134 | 13% |
| 5 | research_org | ERC | 34 | 3% |
| 6 | prof_body | Teaching Council | 36 | 3% |
| 7 | ed_media | Education Matters | 33 | 3% |
| | **Total** | | **746** | |

### Weekly inference: Jan 15 → Mar 13 2026

2–12 articles per week. 64 total across 9 weeks.

### Sources dropped

| Source | Reason |
|---|---|
| Irish Times | Almost entirely paywalled. 0 usable articles. |
| TASC | Broad social policy think tank. Only 8 articles matched education. |
| NCSE | Only 26 articles. Too few to justify a separate source. |
| Children's Rights Alliance | No matching category in England/Scotland. Deferred to future expansion. |
| NCCA | Cloudflare 403 blocks all automated access. Not scrapeable. |

### TheJournal.ie — login wall issue

TheJournal.ie (`/education/news/`) was initially scrapeable and returned 163 articles with full text during testing on 16 March 2026. After hitting HTTP 429 rate limit errors, the site began serving a login/donation wall. All 163 articles returned empty on subsequent runs.

**Decision:** Keep in weekly pipeline. The login wall may be temporary. For the historical batch, TheJournal.ie contributes 0 articles.

**Implication:** Ireland has effectively no education journalism in the historical dataset. This is a structural finding about the Irish education media landscape, not a data collection failure.

### Gov.ie — migration date issue

When gov.ie rebuilt their website in April 2025, all historical content was stamped with migration dates (2025-04-11 or 2025-04-12) instead of original publish dates. A one-off date-fix script fetched real "Published on:" dates from each article page. Future weekly scrapes are unaffected.

---

## 5. Scotland — sources and article counts

### Historical batch: Jan 2023 → 31 Dec 2025

| Source | Category | Method | Articles | Notes |
|---|---|---|---|---|
| Scottish Government | government | Search page HTML | 188 | 168 news + 33 publications (FOI/minutes filtered). HE content removed by post-processing. |
| Children in Scotland | civil_society | HTML | 182 | Only goes back to Jan 2024. |
| GTCS | prof_body | HTML | 67 | 6 pages, pagination uses `f308a811_page=N` parameter. |
| ADES | prof_body | WP API | 50 | 37 posts skipped as empty (file download links only). |
| SERA | think_tank | WP API | 24 | Small research association. ~8 articles/year. |
| **Total** | | | **511** | |

### Category distribution (after post-processing)

| # | Category | Scotland source(s) | Articles | % |
|---|---|---|---|---|
| 1 | government | Gov.scot | 188 | 37% |
| 3 | think_tank | SERA | 24 | 5% |
| 6 | prof_body | GTCS, ADES | 117 | 23% |
| 8 | civil_society | Children in Scotland | 182 | 36% |
| | **Total** | | **511** | |

### Weekly inference: Jan 15 → Mar 13 2026

6–26 articles per week. 107 total across 9 weeks.

### Sources dropped

| Source | Reason |
|---|---|
| TES Scotland | Fully paywalled. All articles blocked. |
| Education Scotland | JS-rendered — listing and article pages load content via JavaScript. `requests` library gets empty HTML shell. Would need Selenium/Playwright. Content is primarily curriculum updates, not policy discourse. |
| Audit Scotland | Not equivalent to other countries' sources. Audits public spending, not education-focused. |
| COSLA | Education-filtered news page exists (`Children and Young People` category) but Cloudflare 403 blocks all automated access. |

### Gov.scot scraper design

**Approach:** Uses education-filtered search pages (not sitemap):
- News: `https://www.gov.scot/news/?cat=filter&topic=education&sort=date`
- Publications: `https://www.gov.scot/publications/?cat=filter&topic=education&sort=date`

**Publications filtering:** Gov.scot publications contain large volumes of administrative documents (FOI releases ~40%, committee minutes ~20%, impact assessments ~10%). These are filtered by title keyword during scraping. Remaining publications (~30%) are policy-relevant: strategy documents, guidance, evaluations, statistics, frameworks.

**Text extraction:** Gov.scot article pages use `<main>` tag for content, not `<article>` or `div.body-content`.

### Education Scotland — JS rendering explained

Both listing and article pages are JavaScript-rendered. The raw HTML (what `requests` returns) contains no article content — only `<script>` tags. The browser's DevTools shows content because the browser executes JavaScript, but Python's `requests` library does not. Browser automation (Selenium/Playwright) would be needed but adds infrastructure complexity not justified for this source.

---

## 6. Cross-country comparison

| Category | England (count) | England (%) | Ireland (count) | Ireland (%) | Scotland (count) | Scotland (%) |
|---|---|---|---|---|---|---|
| government | 679 | 17% | 799 | 77% | 188 | 37% |
| think_tank | 111 | 3% | 134 | 13% | 24 | 5% |
| funder | 106 | 3% | 0 | 0% | 0 | 0% |
| research_org | 202 | 5% | 34 | 3% | 0 | 0% |
| prof_body | 104 | 3% | 36 | 3% | 117 | 23% |
| ed_media | 2,741 | 69% | 33 | 3% | 0 | 0% |
| civil_society | 0 | 0% | 0 | 0% | 182 | 36% |
| **Total** | **3,943** | | **746** | | **511** | |

---

## 7. Finding: education media landscape differences

A key finding from the scraper development process:

- **England** has Schools Week — a free, dedicated, high-volume education news outlet (~900 articles/year, 69% of the England dataset). This creates a rich, publicly accessible layer of education policy discourse between government and the profession.
- **Scotland** has no free equivalent. TES Scotland is fully paywalled. The Herald and The Scotsman are also paywalled. Education policy discourse is dominated by government, professional bodies, and civil society organisations.
- **Ireland** is similar. The Irish Times is fully paywalled. TheJournal.ie is now behind a login wall. RTÉ provides only ~37 recent stories with no archive. Government press releases (gov.ie) dominate at 77%.

**Methodological implication:** Cross-country divergence scores (JSD, KL asymmetry) will partly capture this structural difference in **who speaks** about education policy, not just differences in **what they say**. England's topic model is heavily shaped by journalistic framing; Scotland and Ireland's models reflect institutional/governmental framing. This should be flagged in the analysis as a feature of the data, not a limitation.

---

## 8. Architectural decisions

### England-only training

**Decision:** Only England sources are included in the training corpus. Scotland and Ireland are inference-only.

**Rationale:** The research question asks how the same education policy issues are framed differently across jurisdictions. Running Scottish and Irish documents through an England-trained model and examining where the model's categories fit poorly is itself part of the analysis — it surfaces the political assumptions built into the tool.

### One merged inference file per weekly run

Each weekly run produces a single merged CSV per country per week (e.g. `week01_2026-01-15.csv`) containing all sources. Training data keeps separate per-source CSVs for quality inspection.

### Append vs overwrite (training runs)

When running a training scrape with `--since`, the scraper appends to existing per-source CSVs. `run.py` deduplicates on URL, so overlap from a partial re-run is safe.

### Weekly inference boundary instability

Weekly inference batches are bounded by fixed date ranges (e.g. 9–15 Jan). An article published late on the last day of a window may appear in that week's batch or the following one depending on scraper timing. There is no deduplication across weekly inference files.

This is a deliberate methodological observation. The project is partly concerned with the instability of automated pipelines and how that instability propagates into outputs. A system that reports "the top education topics this week" is not neutral: what counts as "this week" is a boundary imposed by the pipeline, and articles near that boundary are unstable. This is preserved intentionally for analysis rather than silently fixed.

### Inference evaluation without ground truth

The pipeline uses unsupervised topic modelling. There are no pre-defined correct labels — the model discovers patterns from the training corpus. Ground truth is not a prerequisite.

Weekly batches of 15–30 articles are realistic for a specialised policy domain. A pipeline that finds nothing notable in 17 articles is making a valid finding ("quiet week"). Week-level percentage breakdowns are noisy at small N — this is flagged as a limitation of weekly granularity rather than a model failure.

**Evaluation methods:**

| Method | What it tells you |
|---|---|
| Coherence score (C_v) | Are the words within each topic semantically related? |
| Qualitative inspection | Do the top words/documents per topic make editorial sense? |
| Temporal stability | Do topics persist week-over-week in plausible ways? |
| Coverage check | What % of articles are assigned to a topic vs. noise? |

**Cross-jurisdiction angle:** When the England-trained model is applied to Scottish and Irish content, the places where it struggles (low coherence, high noise) are substantive findings revealing which assumptions in the training data are England-specific.

### Automatic validation after every inference write

`run.py` runs a lightweight validation check after writing each inference CSV:
- All expected columns present
- No rows with empty text
- Article count not zero; below 5 triggers a low-volume warning

Non-fatal — a scraper failing silently should be visible but should not prevent other sources' data from being saved.

---

## 9. Post-processing (applied to all countries)

All inference CSVs go through `_postprocess()` in run.py:

1. **Drop empty text** — removes rows where scraper got title/date but no article content
2. **Title-only HE filter** — removes articles where title contains HE terms AND title has no school-level terms
3. **Language flagging** — adds `language` column (Irish word frequency, threshold=8)
4. **Deduplication** — by URL

### Title-only HE filter

- **HE terms (in title):** `university`, `universities`, `college fees`, `undergraduate`, `postgraduate`, `phd`, `doctoral`, `campus`, `tuition fees`, `higher education`, `third level`
- **School terms (in title):** `school`, `teacher`, `pupil`, `primary`, `secondary`, `leaving cert`, `junior cycle`, `senior cycle`, `SNA`, `DEIS`, `curriculum`, `headteacher`, etc.
- **Rule:** Remove only if title has HE term AND title has NO school term

Chosen after a score-based filter proved too aggressive (removed all 163 TheJournal.ie articles and 303 total). Applied to England too for consistency: removed 26 from training (3,969 → 3,943) and 1 from inference.

### Language detection

Irish language articles are **flagged, not removed**. The `language` column uses function word frequency (` agus `, ` na `, ` tá `, etc., threshold 8+). Future-proof: can be replaced with `langdetect` library for Scots Gaelic (`gd`) and Welsh (`cy`).

---

## 10. Scraper design notes

### WordPress API `per_page` bug

Many WordPress sites silently cap `per_page=100` to 10-20. All WP API scrapers use `per_page=10`. Affected: SERA, ERC, Teaching Council, Education Matters, ADES.

### Gov.ie search page approach

Uses search page HTML (not sitemap — sitemap only contains school inspection reports):
- Press releases: `https://www.gov.ie/en/search/?category=Press+release&organisation=Department+of+Education+and+Youth`
- Publications: `https://www.gov.ie/en/search/?category=Publication&organisation=Department+of+Education+and+Youth`
- `data-createdat` attribute (lowercased by BeautifulSoup) provides dates. Parsed with `lxml`.

### ESRI education filtering

ESRI covers all policy areas. Uses ESRI's own filters:
- News: `https://www.esri.ie/news?keywords=education`
- Publications: `https://www.esri.ie/publications/browse?research_areas[]=63`

### RTÉ limited archive

RTÉ's education section keeps ~37 recent stories by design. Pagination beyond page 2 returns sidebar links. Scraper stops after 2 consecutive pages with no new articles. Useful for weekly scrapes only.

---

## 11. Supabase architecture

Three tables, written to by two repos:

**`articles_raw`** — this repo writes raw scraped data:
- `id` (uuid PK), `url` (unique), `title`, `article_date`, `text`, `source`, `country`, `type`, `institution_name`, `language`, `dataset_type`, `week_number`, `created_at`

**`articles_topics`** — analysis repo writes topic modelling results:
- Same base columns as `articles_raw` plus: `topic_num`, `dominant_topic`, `dominant_topic_weight`, `topic_probabilities`, `text_clean`, `run_id`, `sentiment_score`, `sentiment_label`, `contestability_score`, `election_period`

**`drift_metrics`** — analysis repo writes weekly divergence scores:
- `week_number`, `n_articles`, `js_divergence`, `mean_confidence`, `mean_contestability`, `high_contestability_rate`, `topic_concentration_hhi`, `n_topics_present`, alert flags, `run_id`, `computed_at`

**Flow:**
```
atlas-ed-data (this repo) → articles_raw
analysis repo reads articles_raw → processes → writes to articles_topics + drift_metrics
Streamlit dashboard reads from all three tables
```

**Security:** Row Level Security enabled on all tables. `SUPABASE_SERVICE_KEY` used server-side only. Stored as GitHub Secrets for Actions, `.env` locally.

---

## 12. Automation

### GitHub Action: weekly scrape

`.github/workflows/weekly_scrape.yml` runs every Friday at 06:00 UTC:
1. Runs `pytest tests/` (12 tests — imports, schema, Supabase connection)
2. Calculates week number and date range automatically
3. Scrapes all 3 countries via `run.py`
4. Pushes new articles to Supabase via `seed_supabase.py`
5. Generates summary of articles scraped per country

Can also be triggered manually via `workflow_dispatch`.

### Pre-commit secrets scanning

`detect-secrets` installed as pre-commit hook. Blocks commits containing strings that look like API keys. Baseline scan (2026-02-26): 4 flags, all confirmed false positives.

---

## 13. UK Parliament Education Select Committee — deferred

**What was explored:** The UK Parliament Committees API (`committees-api.parliament.uk/api/`) is publicly accessible and returns structured metadata for Education Committee publications (reports, correspondence, written evidence). The Education Committee has ID 203 and has published 139 reports and 479 items of correspondence.

**Why deferred:** Getting actual text content proved impractical:
- `committees.parliament.uk` returns 403 for scraping requests
- The API returns metadata only — report text is not included
- Full report text is only available as PDFs

**If revisited:** PDF parsing using `pdfplumber` on document URLs returned by the API.

---

## 14. Future expansion sources

### Advocacy (new category — all three countries)
- England: Children's Commissioner
- Scotland: Children in Scotland *(currently included)*
- Ireland: Children's Rights Alliance

### Union (new category — all three countries)
- England: NEU (National Education Union)
- Scotland: EIS (Educational Institute of Scotland)
- Ireland: INTO (Irish National Teachers' Organisation)

### Parliament (new category — all three countries)
- England: Westminster / Education Select Committee
- Scotland: Scottish Parliament
- Ireland: Oireachtas

> **Note:** Adding unions and parliament would require retraining the NMF model. Deferred to a future iteration.

---

## 15. Source type taxonomy

| Code | Label | Description |
|---|---|---|
| `government` | Central government | Government departments and ministerial communications |
| `think_tank` | Think tank / research | Policy research organisations |
| `funder` | Funder | Research funding bodies |
| `research_org` | Data / research body | Data-focused or university-based research organisations |
| `prof_body` | Professional body | Professional associations, regulatory bodies, leadership networks |
| `ed_media` | Education media | Specialist education journalism |
| `civil_society` | Civil society | Advocacy organisations, children's rights bodies |

---

## 16. Known data limitations

| Limitation | Impact | How addressed |
|---|---|---|
| Gov.ie migration dates | ~500 articles had wrong dates (2025-04-11/12 instead of real publish date) | Fixed via one-off script fetching real "Published on:" dates from each article page |
| Ireland/Scotland have fewer articles than England | Ireland 746, Scotland 511 vs England 3,943 | Structural finding — reflects real differences in education media landscape, not a data collection failure |
| No free education journalism in Scotland/Ireland | ed_media category is empty (Scotland) or minimal (Ireland: 33 articles) | Documented as finding about who shapes public discourse in each jurisdiction |
| TheJournal.ie blocked mid-project | 163 articles lost from Ireland historical dataset | Kept in weekly pipeline — login wall may be temporary. 0 articles in retro. |
| Empty text articles | PDF links, landing pages, index pages return no paragraph content | Removed during post-processing (171 from Ireland, varying from others) |
| HE content mixed in | Government education topics include university/college articles | Filtered by title-only HE filter across all three countries |
| Irish/Scots Gaelic articles | Small number of non-English articles in corpus | Flagged with `language` column (`ga`/`gd`), kept in dataset as a finding about bilingual policy discourse |
| RTÉ no archive | Only ~37 recent stories visible, 0 for retro period. RTÉ contributes to weekly inference data but is absent from the training corpus due to its lack of a public archive. RTÉ articles are assigned topics based on training distributions learned from other Ireland sources. | Included for weekly scrapes going forward only. Noted as methodological limitation. |
| Children in Scotland no 2023 data | Site only goes back to Jan 2024 | 182 articles from 2024-2025 only. Documented gap. |
| ADES empty posts | 37 of 87 WP posts are file download links with no text | Skipped during scraping. 50 articles with actual text content kept. |

---

## 17. Scraper text quality fixes (22 March 2026)

Initial topic modelling revealed that boilerplate text in scraped articles was contaminating NMF topics — repeated footer blocks, header prefixes, and download link text were creating junk topics rather than meaningful policy discourse patterns. Four Ireland scrapers were updated:

| Source | Problem | Fix | Impact |
|---|---|---|---|
| **ESRI** | Every article included full footer block: address, phone, cookies statement, "Web Design by Annertech" (~500 chars per article) | Strip text at first footer marker (`"The Economic and Social Research Institute Whitaker Square"`) | Prevents a "boilerplate" topic from dominating ESRI articles in NMF |
| **Teaching Council** | WP API returned 1-2 sentence excerpts (74-145 chars) instead of full articles | Switched to hybrid approach: WP API for listing + HTML fetch for full article text (1,386-4,739 chars) | Articles now contain enough text for meaningful topic assignment |
| **Gov.ie** | Every article started with "From: Department of Education and Youth" prefix; some had "(PDF)" references | Strip prefix and PDF markers from extracted text | Removes repeated government attribution text from topic model input |
| **ERC** | Articles ended with download link text ("Read the full report here", "Check out the infographic here") | Skip paragraphs containing download link phrases | Minor cleanup — prevents link text from appearing in topic keywords |

**Action taken:** Full re-scrape of Ireland retro (Jan 2023 → Dec 2025) + all weekly inference files (weeks 1-11) with fixed scrapers. Re-seeded to Supabase.

---

## 18. Data columns

All output CSVs share this schema:

| Column | Description |
|---|---|
| `url` | Article URL (unique identifier) |
| `title` | Article title |
| `date` | Publish date (YYYY-MM-DD) |
| `text` | Full article text |
| `source` | Source identifier (e.g. `gov_ie`, `esri`, `schoolsweek`) |
| `country` | Country code (`eng`, `sco`, `irl`) |
| `type` | Source category (see §15) |
| `institution_name` | Full institution name |
| `language` | ISO 639-1 language code (`en`, `ga`) |

---

© UCL Institute of Education 2026. All rights reserved.
Contact l.yorke@ucl.ac.uk for reuse enquiries.
