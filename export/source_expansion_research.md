# Source Expansion Research — Planning Memo

**Status:** research only. Nothing committed, nothing registered, no schema changes. Approval gate required before any candidate is added to `src/run.py`.

## Scope

Five parallel agents (eng / sco / wal / ni / irl) searched for sources to fill gaps in the existing corpus. This memo dedupes their candidate lists, ranks each candidate on three axes (gap-filling × feasibility × archive depth), and surfaces the strongest cross-jurisdictional adds.

- **Language constraint:** English (or English-side of bilingual sites). Welsh and Irish-medium content is out of scope for this pass.
- **Feasibility shorthand:** WP REST 200 with JSON post array = "easy WP". Non-WP CMS that returns HTML cleanly = "HTML scrape". Cloudflare / WAF / 403 = "blocked" and flagged.
- **What's already in the corpus** (for context, not researched here): gov.uk DfE publications, gov.scot, gov.wales, gov.ie, Schools Week, EPI, Sutton Trust, CfEY, Children's Commissioner (Eng), GTCS, ADES, Children in Scotland, SERA, SPICe Spotlight (queued), Teaching Council (IRL), ESRI, ERC, defenddigitalme, ucl_ioe_blog, scot_gov_digital_blog.
- **What was researched:** the four flagged gap categories per jurisdiction — unions, regulators, parliament, advocacy — plus adjacent thinks tanks, prof bodies, and ed media where existing coverage was thin.

## Ranking scheme (per candidate, 3-axis sum 3-9)

| Axis | 1 | 2 | 3 |
|---|---|---|---|
| **Gap-filling** | Duplicates existing coverage | Adjacent / partial overlap | Fills empty category × jurisdiction cell |
| **Feasibility** | Paywalled, JS-shell, hard block | Non-WP HTML scrape required | WP REST 200, EN-clean |
| **Archive depth** | Thin / <3 yrs / low volume | Moderate (3-10 yrs) | Deep (10+ yrs) or high cadence |

---

## Cross-jurisdiction dedupe notes

Reviewing the 5 candidate lists, only one true domain overlap surfaced:

- **INTO** appears once (irl batch). The ni agent noted INTO as already-covered as ROI union; INTO does have an NI branch but the domain (`into.ie`) is the same — treat as **single source with irl + ni applicability**. Rows below: listed once under IRL with an "(also serves NI)" tag.
- **NEU, NASUWT, NAHT, ASCL** were probed by the eng agent and rejected (Cloudflare 403 / non-WP). They were not re-probed for the Welsh / NI sides. The wal agent noted NEU Cymru content is buried under the UK NEU site and unionised-Cymru content is hard to isolate; deferred.
- **UTU (NI)** is NI-only; not a multi-jurisdiction case.

No other domain-level dupes. The candidate sets are otherwise jurisdiction-clean.

---

## England (eng) — 12 candidates

| Name | URL | Category | Lang | WP? | Score (gap+feas+depth) | Notes |
|---|---|---|---|---|---|---|
| Ofqual blog | https://ofqual.blog.gov.uk/ | regulator | en | yes | 3+3+2 = **8** | First dedicated regulator voice in eng. Same WP infra as ucl_ioe_blog. |
| Education Inspection blog (Ofsted) | https://educationinspection.blog.gov.uk/ | regulator | en | yes | 3+3+2 = **8** | Fills Ofsted gap; HMCI commentary not in gov.uk pubs. |
| FE Week | https://feweek.co.uk/ | ed_media | en | yes | 3+3+3 = **9** | Sister to Schools Week; entire FE sector currently absent. Post id 156k+. |
| HEPI | https://www.hepi.ac.uk/ | think_tank | en | yes | 3+3+3 = **9** | Only UK HE-policy think tank. Daily-cadence blog since 2003. |
| Chartered College of Teaching | https://chartered.college/ | prof_body | en | yes | 3+3+2 = **8** | Fills eng prof_body gap; analogue of GTCS and Teaching Council. |
| Learning and Work Institute | https://learningandwork.org.uk/ | research_org | en | yes | 3+3+2 = **8** | Only adult/lifelong learning research org. |
| The Education Hub (DfE) | https://educationhub.blog.gov.uk/ | government | en | yes | 2+3+2 = **7** | Adjacent to existing gov.uk DfE scrape; check URL overlap first. |
| Centre for Social Justice | https://www.centreforsocialjustice.org.uk/ | think_tank | en | yes | 2+3+3 = **8** | Centre-right voice, diversifies think_tank set. Exclusions/Absence Trackers. |
| 5Rights Foundation | https://5rightsfoundation.com/ | advocacy | en | yes | 2+2+2 = **6** | Global org — needs UK filter. EdTech focus is growing not central. |
| FE News | https://www.fenews.co.uk/ | ed_media | en | yes | 2+2+3 = **7** | Mixed practitioner/PR content — quality filter needed. Post id 558k+. |
| Social Market Foundation | https://www.smf.co.uk/ | think_tank | en | yes | 2+2+2 = **6** | Education is a sub-stream; topic filter needed. |
| Civitas | https://www.civitas.org.uk/ | think_tank | en | yes | 2+2+3 = **7** | Adds ideological diversity but heavy non-ed content. |

**Remaining eng gaps after these adds:** unions (NEU, NASUWT, NAHT, ASCL — all Cloudflare 403 or non-WP, blocking entire union category); Commons / Lords Library (Cloudflare 403); committees.parliament.uk (metadata-only); IFS, IPPR, NFER, Demos, Policy Exchange (not on WP REST). Recommend a separate RSS/HTML-fallback workstream for the unions+parliament tier; do not add as WP scrapers.

---

## Scotland (sco) — 10 candidates

| Name | URL | Category | Lang | WP? | Score | Notes |
|---|---|---|---|---|---|---|
| SSTA | https://ssta.org.uk/ | union | en | yes | 3+3+2 = **8** | First sco union source (EIS is non-WP). Active May 2026. |
| Universities Scotland | https://www.universities-scotland.ac.uk/ | prof_body | en | yes | 3+3+2 = **8** | First sco HE voice. |
| Scottish Funding Council | https://www.sfc.ac.uk/ | government | en | yes | 3+3+2 = **8** | First sco tertiary funder/regulator. |
| Enlighten (Reform Scotland) | https://www.enlighten.scot/ | think_tank | en | yes | 3+3+3 = **9** | Adds second sco think tank; Commission on School Reform archive to 2011. |
| Scottish Children's Services Coalition | https://www.thescsc.org.uk/ | civil_society | en | yes | 3+3+2 = **8** | Specialist ASN advocate. WP category `additional-support-needs` (21 posts). |
| School Leaders Scotland | https://www.sls-scotland.org.uk/news/ | prof_body | en | unknown | 3+1+1 = **5** | Probe failed (connection 000). Re-test from runner host. |
| Connect (SPTC) | https://connect.scot/ | civil_society | en | no | 3+2+1 = **6** | Parent voice; custom PHP CMS. Sitemap-based scraper needed. |
| Royal Society of Edinburgh — Education | https://rse.org.uk/programme/education/ | research_org | en | unknown | 2+2+2 = **6** | 403 on WP probe — try realistic UA before Playwright. |
| Holyrood Magazine — Education | https://www.holyrood.com/portfolios/education.htm | ed_media | en | no | 3+2+3 = **8** | Strongest open-access sco ed_media after TES Scotland dropped. Since 1999. |
| CSPP21 | https://cspp21.co.uk/ | think_tank | en | yes | 2+2+1 = **5** | Cross-party but UK-wide content mixed in; needs topic filter. |

**Remaining sco gaps after these adds:** EIS (largest teaching union — non-WP, would need HTML scraper); Holyrood ECYP Committee (metadata-only); Education Scotland and SQA (both dropped previously — see re-test section). Scotsman education section worth a separate probe.

---

## Wales (wal) — 11 candidates

| Name | URL | Category | Lang | WP? | Score | Notes |
|---|---|---|---|---|---|---|
| Estyn | https://estyn.gov.wales/ | regulator | en-mixed | yes | 3+3+2 = **8** | First Welsh regulator. CY twin at estyn.llyw.cymru — filter to EN URLs. |
| Education Wales Blog | https://educationwales.blog.gov.wales/ | government | en-mixed | yes | 3+3+2 = **8** | Ministerial voice not in gov.wales PDF set. 370 posts. |
| IWA | https://www.iwa.wales/ | think_tank | en-mixed | yes | 3+3+3 = **9** | Education tag (75 posts) + HE tag (96). Clean WP filter. |
| WISERD | https://wiserd.ac.uk/ | research_org | en-mixed | yes | 3+3+3 = **9** | ESRC-designated; EN at /news/, CY at /cy/newyddion/. 2226 posts. |
| Senedd Research | https://research.senedd.wales/ | parliament | en-mixed | no | 3+2+2 = **7** | First Welsh parliament source. Umbraco/IIS — HTML scrape of /research-articles/. |
| WCPP | https://wcpp.org.uk/ | think_tank | en-mixed | yes | 3+2+2 = **7** | wp-json blocked at edge; /feed/ RSS works. |
| Qualifications Wales | https://qualifications.wales/ | regulator | en-mixed | no | 3+2+2 = **7** | Umbraco — HTML scrape of /news-views/. |
| Nation.Cymru | https://nation.cymru/ | ed_media | en | yes | 3+2+3 = **8** | 60K posts, no education category — keyword filter mandatory. Fills "no Schools Week" gap. |
| Education Workforce Council Wales | https://www.ewc.wales/ | prof_body | en-mixed | no | 3+2+2 = **7** | Joomla-style — bespoke HTML/PDF scrape. Statutory body covering 88K registrants. |
| Children in Wales | https://www.childreninwales.org.uk/ | civil_society | en-mixed | no | 3+1+2 = **6** | Custom PHP CMS, no RSS — bespoke scraper for /news-events/news/. |
| ColegauCymru | https://www.colleges.wales/ | prof_body | en-mixed | no | 2+2+2 = **6** | Only FE/post-16 voice; /en/ path filter clean. |

**Remaining wal gaps after these adds:** Children's Commissioner for Wales (Cloudflare 403); Bevan Foundation (Cloudflare 403); UCAC (Welsh-language only); Medr (Cloudflare-blocked); NEU Cymru (no isolated subdomain). Wales Online has a dedicated education editor (Abbie Wightwick) but excluded as generic news.

---

## Northern Ireland (ni) — 13 candidates

NI is a brand-new jurisdiction; previously zero sources. The 13 candidates cover the core taxonomy from scratch.

| Name | URL | Category | Lang | WP? | Score | Notes |
|---|---|---|---|---|---|---|
| DENI | https://www.education-ni.gov.uk/news | government | en | no | 3+2+2 = **7** | First NI source ever. Sitecore — HTML scrape with pagination. |
| ETI | https://www.etini.gov.uk/news | regulator | en | no | 3+2+2 = **7** | NI Ofsted analogue. Mostly PDF inspection reports. |
| NICCY | https://www.niccy.org/ | civil_society | en | yes | 3+3+2 = **8** | Statutory children's commissioner. Clean WP API, recent 2026 posts. |
| NICIE | https://nicie.org/news/ | advocacy | en | yes | 3+3+2 = **8** | Integrated education — unique NI structural feature. |
| Integrated Education Fund | https://www.ief.org.uk/our-work/news/ | funder | en | yes | 3+3+2 = **8** | Funder + advocacy hybrid. Commissions QUB/Ulster research. |
| Children's Law Centre NI | https://childrenslawcentre.org.uk/ | civil_society | en | yes | 3+3+2 = **8** | SEND tribunals + education rights litigation. May 2026 Assembly submission post. |
| CiNI | https://www.ci-ni.org.uk/ | civil_society | en | yes | 3+3+2 = **8** | Umbrella for ~100 NI children's-sector orgs. |
| Pivotal Public Policy Forum | https://www.pivotalpolicy.org/our-work/news-events | think_tank | en | no | 3+2+2 = **7** | Only NI think tank. Recently migrated domain — seed both. |
| UTU | https://www.utu.edu/news/ | union | en | no | 3+2+2 = **7** | Only NI-HQ'd teaching union. Aspect Media CMS. |
| NI Assembly Research Matters | https://www.assemblyresearchmatters.org/ | parliament | en | yes | 3+2+2 = **7** | RaISe blog. WP API 401 on probe — retry with realistic UA. |
| Slugger O'Toole — Education | https://sluggerotoole.com/category/education/ | ed_media | en | yes | 2+3+3 = **8** | 20+ yrs archive; politics blog with education vertical. Filter by category. |
| CCEA | https://ccea.org.uk/about/news | regulator | en | unknown | 3+1+2 = **6** | Curriculum + qualifications authority. Cloudflare 403 — needs UA retry or Playwright. |
| NIOPA (QUB) | https://niopa.qub.ac.uk/ | research_org | en | no | 2+2+3 = **7** | DSpace repository — OAI-PMH or DSpace REST. Mostly PDFs. |

**Remaining ni gaps after these adds:** CCMS, NIVT, EANI (all blocked or dead); QUB main site (404); Belfast Telegraph (paywall). Irish-medium primary (Comhairle na Gaelscolaíochta) excluded per language constraint.

---

## Republic of Ireland (irl) — 12 candidates

| Name | URL | Category | Lang | WP? | Score | Notes |
|---|---|---|---|---|---|---|
| INTO (also serves NI) | https://www.into.ie/ | union | en | yes | 3+3+3 = **9** | First irl union. 2000 posts. Multi-jurisdiction. |
| HEA | https://hea.ie/ | regulator | en | yes | 3+3+2 = **8** | First irl HE regulator. 339 posts. Recent GenAI in HE framework. |
| ETBI | https://www.etbi.ie/ | prof_body | en | yes | 3+3+2 = **8** | 16 ETBs. Junior cycle / FET / apprenticeships. |
| Educate Together | https://www.educatetogether.ie/ | civil_society | en | yes | 3+3+2 = **8** | Multi-denominational patron body. 984 posts. |
| CPSMA | https://www.cpsma.ie/ | prof_body | en | yes | 3+3+2 = **8** | Catholic patron — covers ~85% of primary schools. 644 posts. |
| IUA | https://www.iua.ie/ | prof_body | en | yes | 3+3+2 = **8** | Seven research-intensive universities. 737 posts. |
| AONTAS | https://www.aontas.com/ | civil_society | en | yes | 3+3+2 = **8** | First adult/lifelong learning voice for irl. 613 posts. |
| Education Magazine (Ireland) | https://educationmagazine.ie/ | ed_media | en | yes | 3+3+3 = **9** | Strongest irl ed_media after TheJournal blocked. 1643 posts. |
| Oireachtas Education Committee | https://www.oireachtas.ie/en/committees/34/education-and-youth/ | parliament | en | no | 3+2+2 = **7** | data.oireachtas.ie provides XML/JSON listings — avoid PDF-only trap. |
| ASTI | https://www.asti.ie/ | union | en | yes (blocked) | 3+1+2 = **6** | wp-json 403/404. HTML scrape of /news/ listing. |
| Barnardos Ireland | https://www.barnardos.ie/ | civil_society | en | yes | 2+2+2 = **6** | Mixed fundraising + policy. Keyword filter needed. |
| Down Syndrome Ireland | https://downsyndrome.ie/ | advocacy | en | yes | 3+3+1 = **7** | Low volume (76 posts) but high signal. SET-allocation submissions. |

**Remaining irl gaps after these adds:** SEC (examinations.ie 403); NCCA (already dropped); TUI (ASP.NET, not WP); AsIAm (Webflow); Inclusion Ireland (401 auth-locked); JMB (.aspx); Catholic Education Partnership (WAF); publicpolicy.ie (WAF). Several of these are Playwright candidates.

---

## Top 10 cross-jurisdictional priorities

Ranked on combined score + breadth of gap filled. These should be the first 10 PRs if/when this work proceeds.

| Rank | Candidate | Jurisdiction | Category | Score | Why first |
|---|---|---|---|---|---|
| 1 | FE Week | eng | ed_media | 9 | Whole FE sector missing. Reuses schoolsweek scraper. |
| 2 | HEPI | eng | think_tank | 9 | Only UK HE think tank. Daily blog, 20+ yr archive. |
| 3 | IWA | wal | think_tank | 9 | Welsh think tank with clean Education tag filter. |
| 4 | WISERD | wal | research_org | 9 | ESRC national research centre for Wales. |
| 5 | Enlighten (Reform Scotland) | sco | think_tank | 9 | Second sco think tank; Commission on School Reform. |
| 6 | INTO | irl + ni | union | 9 | First irl union; multi-jurisdiction win. |
| 7 | Education Magazine (Ireland) | irl | ed_media | 9 | Strongest open-access irl ed_media after TheJournal dropped. |
| 8 | Ofqual blog | eng | regulator | 8 | First dedicated regulator voice in eng. |
| 9 | Education Inspection blog (Ofsted) | eng | regulator | 8 | Pairs with Ofqual; same WP infra. |
| 10 | NICCY | ni | civil_society | 8 | Opens NI jurisdiction with statutory children's body. |

The top 10 are all WP REST 200 with clean EN content — every one reuses an existing scraper pattern, so engineering cost is low.

---

## Already-dropped re-test candidates

Sources previously dropped that the agents surfaced with a possible rescue path:

| Dropped source | Rescue method proposed | Notes |
|---|---|---|
| NCCA (irl) | Playwright with realistic UA | Same Cloudflare pattern as CCEA NI; if CCEA rescue works, NCCA worth retry. |
| Education Scotland (sco) | Playwright (already used elsewhere) | Pattern confirmed working for similar 403 sites. |
| TES Scotland (sco) | Not rescued | Holyrood Magazine is the replacement, not a rescue. |
| Commons Library (eng) | None offered | Still Cloudflare-blocked. Workstream for RSS-based fallback. |
| committees.parliament.uk (eng) | None offered | Metadata-only API; full text remains unscrapeable via that path. |
| childcomwales.org.uk (wal) | None offered | Children in Wales is partial substitute, not rescue. |
| Bevan Foundation (wal) | None offered | Cloudflare 403 across all feeds. |
| TheJournal.ie | None offered | Education Magazine is substitute. |

CCEA (NI) is on the fence — agent flagged it as candidate (score 6) but warned the Cloudflare 403 mirrors NCCA. Treating CCEA as the "trial rescue" — if a realistic-UA fetch works, NCCA should be retried with the same method.

---

## Open questions (cannot resolve from web search alone)

1. **INTO openness** — WP REST returns 2000 posts but are member-only briefings included in that count? Need a manual spot-check of 10 random post IDs to confirm full body is public.
2. **CCEA primary language** — site is English-default but `/ga/` and `/ulster-scots/` paths exist for some content. If a candidate's WP feed mixes all three languages without a `lang` field, we need to filter on URL prefix or skip.
3. **Education Magazine (IRL) editorial mix** — 1643 posts but agent flagged some promotional content. Need a sample of 20 recent posts to estimate signal:noise ratio before committing.
4. **5Rights Foundation** — global org with UK office. Does the WP feed expose a country tag, or do we have to keyword-filter on body text? If only body-filter, yield may be too noisy.
5. **Senedd Research / DENI / ETI** — all Sitecore-family CMSes. Is there a single scraper pattern we can reuse across the three (gov.wales / gov-ni / DENI), or do they diverge enough to need three bespoke scripts?
6. **NI Assembly Research Matters** — WP API returned 401. Is this a real auth wall or just a missing Accept header? Re-probe needed.
7. **School Leaders Scotland** — probe returned connection-failure 000. Was this a transient network issue or a TLS handshake mismatch? Re-test from the runner host.
8. **Oireachtas data.oireachtas.ie** — agent flagged it as the workaround to the PDF-only committee page. Does the XML/JSON listing include opening-statement full text or only metadata + PDF links?
9. **Holyrood Magazine** — agent says no paywall on news/opinion but long-form may have a registration wall. Need to spot-check ~10 long-form articles.
10. **Pivotal Policy Forum domain migration** — old permalinks at pivotalppf.org should be in the seed list. Need to confirm whether old URLs redirect or 404.

---

## Approval gate

**Nothing here has been committed, registered, or scraped.** The user needs to approve, in this order:

1. **Top-10 priority list** — confirm or reorder the top 10 in the cross-jurisdictional table above.
2. **Per-candidate deep probe** — for each approved candidate, run a 10-post sample fetch + manual quality check before scraper wire-up. Especially for the open-questions list above.
3. **Scraper additions to `src/run.py`** — only WP REST 200 candidates go in first; non-WP HTML scrapers are a separate workstream.
4. **Dry-run, then full scrape** — standard pattern; results land in a staging table before promotion to `articles_topics`.
5. **Dropped-source rescue** — separate decision: do we want to attempt CCEA / NCCA / Education Scotland with Playwright as a coordinated effort, or keep that on the backlog?

No schema migrations expected — every candidate fits the existing `articles_topics` schema (per `docs/pipeline_decisions.md`). New `category` values introduced by NI (funder, advocacy) already exist in the schema for other jurisdictions, so no enum changes needed.
