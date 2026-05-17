# Source roster gaps — 2026-05-17

Analysis of the 59 newsletter items (#97-104, Jan-Mar 2026) that the in-house scraper failed to capture. These are URLs that the curator chose for publication but our pipeline didn't see. **Use as the prioritised roadmap for the source-roster v2.**

## Headline numbers

- **65 newsletter items** were published during the inference window (Jan 7 → May 12 2026)
- **6 caught** by our scrape (9.2%) — `epi` (×2), `schoolsweek` (×2), `dfe` (×2)
- **59 missed** (90.8%)
- Of 103 "live" sources in `sources_master.csv`, **only 27 actually produced articles** in the latest backfill. **76 are silent.**

## Bucketed roadmap

### A — Sources NOT in the roster at all (add)

| Domain | Count missed | Notes |
|---|---:|---|
| `tes.com` | 3 | TES — Times Educational Supplement. Mainstream education news. |
| `theconversation.com` | 3 | Academic-led opinion + analysis. |
| `ifs.org.uk` | 2 | Institute for Fiscal Studies — annual education spending reports etc. |
| `nuffieldfoundation.org` | 1 | Funding announcements + research. (We have `nuffield` for research outputs but the foundation funding pages are separate.) |
| `tandfonline.com` | 1 | Academic journal hosting. Probably specific journals matter. |
| `fenews.co.uk` | 1 | FE News — further education sector. |
| `oecdedutoday.com` | 1 | OECD Education Today blog. |
| `medr.cymru` | 1 | Medr — new Welsh post-16 education body. |
| `gov.wales` | 1 | Welsh Government. (`gov_scot` covers Scotland; no Wales equivalent yet.) |
| `hwb.gov.wales` | 1 | Hwb — Welsh Gov education portal. |
| `education-ni.gov.uk` | 1 | NI Department of Education. |
| `educationendowmentfoundation.org.uk` | 1 | EEF — already in roster but silent. Confirm scraper runs. |
| `blog.bham.ac.uk` | 1 | Birmingham university blog. |
| `profbeckyallen.substack.com` | 1 | Substack — listed in roster but silent. |

**Action:** evaluate each on signal-to-noise (does the curator pick from here often?). Add the high-value ones to `sources_master.csv` with appropriate ingestion mechanism (RSS, Google Alert, or custom scraper).

### B — Parliament-specific (probably worth a single Parliament scraper)

| Domain | Count missed |
|---|---:|
| `committees.parliament.uk` | 2 |
| `commonslibrary.parliament.uk` | 1 |
| `researchbriefings.files.parliament.uk` | 3 |

Total **6 missed items** — Parliament committee work, House of Commons Library briefings, and downloadable research PDFs. Currently no Parliament scraper exists; Education Select Committee is on the silent list.

**Action:** add `parliament_committees` and `commons_library` scrapers. Or one Google Alert `site:parliament.uk education` covering both.

### C — gov.uk subdomain gaps (biggest single fix)

| Subdomain | Count missed | Pattern |
|---|---:|---|
| `gov.uk` (main, beyond /government/news) | 8 | DfE scraper only covers `/government/news/...`; misses other DfE-relevant paths |
| `assets.publishing.service.gov.uk` | 5 | DfE PDFs — strategy docs, research reports, white papers |
| `educationhub.blog.gov.uk` | 1 | DfE blog — separate subdomain |
| `consult.education.gov.uk` | 1 | DfE consultations |

Total **15 missed items** — DfE-adjacent content the current scraper isn't reaching.

**Action:** extend the `dfe` scraper to handle these subdomains. Or split into two scrapers (`dfe_news` + `dfe_publications_pdfs`). The PDFs (assets.publishing.service.gov.uk) are *linked from* gov.uk announcements, so following those links during scraping would catch many of them automatically.

### D — Sources we have but missed specific items (subdomain / feed coverage)

| Source we have | Subdomain we missed | Count |
|---|---|---:|
| `bbc_education` (specific feed) | `bbc.co.uk/news/articles/...` (general) | 2 |
| `belfast_telegraph` (whole-paper feed) | a SEND-related article slipped past | 1 |

**Action:**
- Add a BBC news catch-all Google Alert filtered for `education` keywords
- Investigate why Belfast Telegraph's RSS missed one article (cache lag? title filter? URL format edge case?)

### E — Sources on the disabled list (Bucket A keyword filter waitlist)

| Domain | Count missed |
|---|---:|
| `instituteforgovernment.org.uk` | 3 |
| `bera.ac.uk` (publication-specific) | 3 |
| `jrf.org.uk` | 1 |
| `chartered.college` (`my.chartered.college`) | 2 |
| `upen.ac.uk` | 1 |

These are sources we **deliberately disabled** pending the `require_keywords` filter. Re-enabling them is blocked on that feature (currently parked).

**Action:** when the keyword-filter feature lands, re-enable Bucket A sources (12 total) — these missed items should then start flowing in.

### F — Sources in the roster but silent (76 sources)

The biggest mystery: 76 sources marked `live` produced 0 articles. Notable silent sources (from the analysis):
- `nfer_national_foundation_for_educational_research`
- `eef_education_endowment_foundation`
- `naht_national_association_of_head_teachers`
- `neu_national_education_union`
- `education_select_committee`
- `local_government_association`
- `nesta`
- `centre_for_education_and_youth`
- `bera` (just re-enabled, Google Alert may not have fired yet)
- `knowledge_exchange_unit_parliament`
- Most academic researcher Google Alerts

**Action:** query `scrape_runs` to triage:
- `status='error'` → fix the scraper
- `rows_scraped=0` with `status='ok'` → source has no recent content (acceptable)
- No rows at all → source never ran (config issue)

SQL for diagnosis is in `docs/decisions/source_roster_gaps_2026_05_17.md` companion section below.

## Prioritised fix list

| Priority | Action | Expected gain (newsletter items recovered) |
|---|---|---:|
| 1 | Extend `dfe` scraper to handle gov.uk subdomains + linked PDFs | +15 |
| 2 | Triage the 76 silent sources via `scrape_runs` | depends — some will be quick wins |
| 3 | Add Parliament scraper (committees + commons library + research briefings) | +6 |
| 4 | Build per-source keyword filter, re-enable Bucket A | +10 |
| 5 | Add Wales / NI gov scrapers (gov.wales, education-ni.gov.uk, hwb.gov.wales, medr.cymru) | +5 |
| 6 | Add TES, IFS, The Conversation, FE News, Nuffield Foundation as RSS or Alerts | +10 |
| 7 | Add a general BBC catch-all Google Alert filtered for `education` | +2 |

**Total potential gain if all addressed:** +48 of 59 missed = 91%+10% baseline ≈ **~95% coverage**.

## AM2 evidence value

This document evidences:
- **K20** — sources of error / coverage bias, with a concrete remediation roadmap
- **K11 / S22** — platform architecture (decision to use a hybrid of custom scrapers + Google Alerts + RSS, with documented gaps)
- **K30 / S33** — identifying ML use cases and the boundary between automated scraping and curator selection

> "Measured scrape-to-newsletter conversion at 9.2% (6/65). Identified 7 buckets of coverage gaps. The biggest single fix is extending the DfE scraper to handle gov.uk subdomains, which would recover 15 of 59 missed items. Documented full roadmap in `docs/decisions/source_roster_gaps_2026_05_17.md`."

## Related

- [`docs/decisions/data_layer_design.md`](data_layer_design.md) — data layer
- [`docs/decisions/disabled_sources.md`](disabled_sources.md) — Bucket A/B/C disabled sources
- [`data/sources_master.csv`](../../data/sources_master.csv) — canonical source roster
- [`src/scraping/sources.yml`](../../src/scraping/sources.yml) — live ingestion config
