# Disabled Sources — Awaiting Per-Source Keyword Filter

Sources commented out in `src/scraping/sources.yml` because they publish broad content beyond UK education. To be re-enabled once the per-source keyword filtering feature lands (see the **Future fix** section below).

### Dropped pending keyword-filter (will re-enable)

| Source | Date disabled | Reason | Rows deleted |
|---|---|---|---|
| `institute_for_government` | 2026-05-16 | Feed is general UK politics (Westminster, civil service, manifestos, Starmer, Covid fraud). 0/8 sampled titles were education. | 10 |
| `joseph_rowntree_foundation` | 2026-05-16 | Feed is poverty/housing/welfare focused (rent control, homes, wealth inequality). ~0/8 sampled titles were directly education. | 10 |
| `child_poverty_action_group` | 2026-05-16 | Feed is welfare-benefits focused (Welfare Rights Bulletins, advising low-income families, LCWRA, cancer treatment guidance). Education tangential. | 4 |
| `digital_poverty_alliance` | 2026-05-16 | Feed covers digital inclusion broadly (landline switchover, Freeview TV, public devices). Only ~1/8 entries touch education. | 10 |
| `post_parliament` | 2026-05-16 | POST publishes science briefings across ALL policy areas (airport health, conspiracy theories, defence R&D, flood resilience). 0/8 sampled were education. Same shape as IfG/JRF. | 10 |
| `ippo_international_public_policy_observatory` | 2026-05-16 | Broad policy content (data-led policy, carbon footprint of doorstep deliveries, international policymaking). 0/4 sampled were education. | 1 |
| `wales_centre_for_public_policy` | 2026-05-16 | Broad Welsh policy (local govt model, net zero, social cohesion, probation, child poverty in Wales). 0/7 specifically education. | 10 |
| `lpips` | 2026-05-16 | LPIPS (Birmingham) publishes broad place/skills/industrial-policy content (Japan secondments, fashion/textiles, AI in local govt, MG Rover, Green Industrial Policy). 0/7 schools/education. | 10 |
| `scotland_digital_blog` | 2026-05-16 | Scottish Gov Digital Services blog (data access, supplier assurance, LiDAR, ScotAccount). 0/7 education — wrong gov.scot blog (it's the IT/data one, not the education one). | 9 |
| `scotland_scottish_parliament_blog` | 2026-05-16 | SPICe Spotlight publishes broad parliamentary explainers (committees, Parliamentary Bureau, party formation). 0/7 specifically education. | 10 |
| `ni_ni_executive_publications` | 2026-05-16 | NI Executive blanket publications feed covers ALL departments. ~2/7 sampled were education. Alternative: NI Department of Education-specific feed. | 0 |
| `ucl_research_for_the_real_world_ioe_podcast` | 2026-05-16 | IOE podcast feed mixes academic life, research ethics, PhD experiences with some education content. | 0 |

### Dropped out of scope (will NOT re-enable)

These are pure higher-education sector publications. Newsletter scope is schools/pre-HE/FE — not HE-about-itself. Even with a keyword filter, content from these would not be in scope.

| Source | Date disabled | Reason | Rows deleted |
|---|---|---|---|
| `wonkhe` | 2026-05-16 | HE sector publication (university mergers, OfS, student loans, university governance, HE financial state). | 30 |
| `hepi` | 2026-05-16 | Higher Education Policy Institute. Output is HE-only (admissions, OfS, governors, HE student experience). | 10 |

### Dropped pending alternative ingestion (will re-enable via different mechanism)

| Source | Date disabled | Reason | Replacement plan | Rows deleted |
|---|---|---|---|---|
| `chartered_college_of_teaching` | 2026-05-16 | `chartered.college/feed` publishes WordPress top-level pages (partner directory entries), NOT journal articles or blog posts. All alternative `/category/*/feed` URLs returned empty. | Set up a Google Alert with query `site:chartered.college`, register the alert RSS URL as `type: google_alert` in `sources.yml`. | 2 |
| ~~`bera`~~ | ~~2026-05-16~~ | ~~`bera.ac.uk/feed` returns 0 entries~~ | ~~Google Alert `site:bera.ac.uk`~~ | ~~6~~ |
| **RE-ENABLED 2026-05-17** | | Investigation showed the feed is behind a JS bot challenge (HTTP 415 on direct, HTML challenge page on browser UA). Wired via Google Alert `site:bera.ac.uk` instead. URL in `sources.yml`. | | |
| `esrc_ukri` | 2026-05-16 | Misconfigured: `ukri.org/feed` is the general UKRI feed (MRC funding updates, neutrino experiments, spin-out dashboards), NOT ESRC-specific. | Find the actual ESRC subdomain feed (`esrc.ukri.org` or similar) or set up Google Alert `site:esrc.ukri.org`. | 9 |
| `confederation_of_school_trusts` | 2026-05-16 | `cstuk.org.uk/rss.xml` publishes internal/test pages (`"TEST Callum for html emails"`, `"[WIP] CST Partnership Enquiry Form"`) and conference booking pages, not articles. CST is a legitimate sector body. | Google Alert `site:cstuk.org.uk`. | 0 |
| `future_generations_commissioner_for_wales` | 2026-05-16 | `futuregenerations.wales/feed` publishes WordPress placeholder posts (`"Hello world!"`, `"post 1"`, `"post 2"`). Feed is unmaintained. | Google Alert `site:futuregenerations.wales`. | 0 |
| `ucl_ecf_staffroom` | 2026-05-16 | Duplicate feed URL — points at `feeds.transistor.fm/ioe` exactly like `ucl_research_for_the_real_world_ioe_podcast`. ECF Staffroom must have its own Transistor.fm URL. | Find the correct ECF Staffroom Transistor URL on UCL IOE's podcast page. | 21 |
| `ucl_closer_blog` | 2026-05-16 | `closer.ac.uk/feed` is mostly job vacancies (Research Associate, Internship x4, Technical Manager) — not research content. CLOSER (Cohort & Longitudinal Studies) is a legitimate UCL research centre. | Find a CLOSER research/news feed, or Google Alert `site:closer.ac.uk -vacancy`. | 0 |

## Related URL fix (not a drop, just a feed-URL correction)

| Source | Date | Change |
|---|---|---|
| `belfast_telegraph` | 2026-05-16 | Switched from site-wide feed (`/rss`) to education-section feed (`/news/education/rss`). 58 off-topic rows deleted, re-scraped to 50 education-only rows. |

## Future fix — per-source keyword filter

When a source's feed contains a mix of education + non-education content, the cleanest fix is a per-source `require_keywords` parameter checked at ingestion in `rss_adapter.py`. Proposed shape:

```yaml
- name: institute_for_government
  type: rss
  scraper: src.scraping.rss_adapter
  params:
    feed_url: https://www.instituteforgovernment.org.uk/rss
    require_keywords:
      - school
      - teacher
      - pupil
      - student
      - university
      - college
      - education
      - curriculum
      - ofsted
      - dfe
      - send
      - ehcp
      - fe
      - he
```

The adapter would only build an `Article` if the title OR body contains at least one keyword. Topic-specific feeds (e.g. BBC Education, Schools Week) wouldn't set this param.

When this lands, re-enable each disabled source in `sources.yml` by uncommenting and adding a `require_keywords` block.

## How to re-enable a source

1. Implement per-source keyword filtering in `src/scraping/rss_adapter.py` (~20 lines)
2. In `sources.yml`, uncomment the source block and add an appropriate `require_keywords` list
3. Re-scrape with `python -m src.scraping.run --source <name> --since 2026-01-06`
4. Move its row in this table to a "Re-enabled" section with the date
