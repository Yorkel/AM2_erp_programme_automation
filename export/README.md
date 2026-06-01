# AtlasED — Education Policy Data Pipeline

> **Whose voices shape education policy?** This pipeline builds a cross-jurisdictional corpus that reveals structural asymmetries in who dominates education policy discourse across England, Scotland and the Republic of Ireland.

[![CI](https://github.com/Yorkel/atlas-ed-data/actions/workflows/weekly_scrape.yml/badge.svg)](https://github.com/Yorkel/atlas-ed-data/actions/workflows/weekly_scrape.yml)

**UCL Institute of Education** | 2026

*Built as part of a Level 6 AI Engineering Apprenticeship. Originally developed as an independent strand of the [ESRC Education Research Programme](https://educationresearchprogramme.org/). Cross-jurisdictional expansion to Scotland and Ireland funded by a UCL Grand Challenges Inequality Catalyst Grant.*

---

## The problem

Education policy in the UK and Ireland is debated by government, think tanks, unions, researchers and the media — but not equally. Some voices are amplified; others are structurally absent. Understanding *who speaks* is as important as understanding *what they say*.

This matters for policymakers, researchers, and the public: if certain actors dominate discourse, policy framing — and ultimately decisions — may be systematically biased.

AtlasED collects education policy articles from **16 sources across 3 countries**, cleans and structures them into a research corpus, and feeds them into a topic modelling pipeline that measures how policy framing diverges across jurisdictions.

## What we found (before any modelling)

The data collection process itself revealed a structural finding:

| | England | Ireland | Scotland |
|---|---|---|---|
| **Government share of corpus** | 17% | 77% | 37% |
| **Education journalism share** | 69% | 3% | 0% |
| **Free dedicated education outlet** | Schools Week | None | None |

**England has a rich, independent education media layer** (Schools Week publishes ~900 articles/year). **Scotland and Ireland do not** — TES Scotland, Irish Times, and The Scotsman are all paywalled.

**Smaller nations rely almost entirely on institutional voices; England has an independent media layer that Scotland and Ireland lack.**

This is not a data collection limitation — it is the data.

---

## The corpus

| Country | Sources | Training (retro) | Inference (weekly) |
|---|---|---|---|
| **England** | 6 | 3,943 articles | 207 (9 weeks) |
| **Ireland** | 7 | 746 articles | 65 (11 weeks) |
| **Scotland** | 5 | 511 articles | 107 (9 weeks) |
| **Total** | **18** | **5,200** | **379** |

NMF is trained separately per country on the retro corpus. BERTopic is run on a balanced cross-country dataset for comparative analysis. See [methodology notes](docs/internal/nmf_bertopic_methodology.md) for rationale.

### Sources

| Category | England | Ireland | Scotland |
|---|---|---|---|
| Government | DfE | Gov.ie | Gov.scot |
| Think tank | EPI | ESRI | SERA |
| Funder | Nuffield Foundation | — | — |
| Research org | FFT Datalab | ERC | — |
| Professional body | FED | Teaching Council | GTCS, ADES |
| Education media | Schools Week | Education Matters, RTÉ* | — |
| Civil society | — | — | Children in Scotland |

> *RTÉ contributes to weekly inference only (no retro archive). TheJournal.ie scraper is active but currently blocked by login wall.

---

## Architecture

```
┌─────────────────────┐
│   atlas-ed-data      │
│   (this repo)        │
│                      │
│   16 sources         │
│   (3 countries)      │
│   weekly automated   │
└──────────┬───────────┘
           │ seed_supabase.py
           ▼
┌─────────────────────┐
│   Supabase           │
│                      │
│   articles_raw       │──────┐
│   articles_topics    │◀─┐   │
│   drift_metrics      │◀─┤   │
└─────────────────────┘  │   │
                          │   │
┌─────────────────────┐  │   │
│   Analysis repo      │──┘   │
│                      │      │
│   NMF (K=30)         │◀─────┘
│   BERTopic           │
│   JSD divergence     │
│   Sentiment          │
└──────────┬───────────┘
           │
           ▼
┌─────────────────────┐
│   Streamlit          │
│   dashboard          │
│                      │
│   Topic explorer     │
│   Cross-country      │
│   comparison         │
│   Weekly divergence   │
└─────────────────────┘
```

**This is a fully automated, end-to-end data pipeline — not a one-off dataset.** GitHub Actions runs every Friday at 06:00 UTC → runs tests → scrapes all 3 countries → pushes to Supabase.

---

## Quick start

### Prerequisites

- Python 3.12+
- `.env` file with `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` (see `.env.example`)

```bash
git clone https://github.com/Yorkel/atlas-ed-data.git
cd atlas-ed-data
pip install -r requirements.txt
pytest tests/ -v                    # verify setup — 12 tests, all should pass
```

### Weekly scrape (all countries)

```bash
cd src
python run.py --country all --since 2026-03-14 --until 2026-03-20 --week 10
python seed_supabase.py --week 10   # push to Supabase
```

> In production, this runs automatically via GitHub Actions every Friday.

### Full retrospective (one-off)

```bash
python run.py --country all --until 2025-12-31
python seed_supabase.py                           # push all data
```

---

## Post-processing

Every scrape automatically applies:

1. **Empty text removal** — drops PDF links, landing pages, login-walled articles
2. **Title-only HE filter** — removes articles clearly about higher education (e.g. "University fees to rise") while keeping school articles that mention universities in passing
3. **Language detection** — flags Irish (`ga`) and Scots Gaelic (`gd`) articles
4. **Deduplication** — by URL

---

## Data schema

| Column | Description |
|---|---|
| `url` | Source article URL (unique identifier) |
| `title` | Article title |
| `date` | Publication date (YYYY-MM-DD) |
| `text` | Full article body text |
| `source` | Source key (e.g. `gov_ie`, `schoolsweek`, `sera`) |
| `country` | Jurisdiction: `eng`, `sco`, `irl` |
| `type` | Source category: `government`, `think_tank`, `funder`, `research_org`, `prof_body`, `ed_media`, `civil_society` |
| `institution_name` | Full institution name |
| `language` | ISO 639-1 code: `en`, `ga`, `gd` |

---

## Project structure

```
atlas-ed-data/
├── .github/workflows/
│   └── weekly_scrape.yml       # Automated Friday scrape + Supabase push
├── docs/
│   ├── pipeline_decisions.md   # All source decisions, architecture, known limitations
│   ├── dataset_analysis.md     # "Whose Voices Shape Education Policy?" analysis
│   ├── ethics.md               # UCL ethics approval (REC2360) + responsible scraping
│   └── scrape_log.md           # Auto-generated log of every scrape run
├── src/
│   ├── run.py                  # Main pipeline — scrape, clean, save
│   ├── seed_supabase.py        # Push to Supabase (articles_raw table)
│   ├── england/                # 6 scrapers: DfE, Schools Week, EPI, Nuffield, FFT, FED
│   ├── ireland/                # 7 scrapers: Gov.ie, ESRI, ERC, Teaching Council, Ed Matters, RTÉ, TheJournal
│   └── scotland/               # 5 scrapers: Gov.scot, SERA, GTCS, ADES, Children in Scotland
├── tests/
│   └── test_pipeline.py        # 12 tests: imports, schema validation, Supabase connection
├── requirements.txt            # 8 dependencies
└── data/                       # Gitignored — regenerate by running scrapers
    ├── training/england/       # 3,943 articles (Jan 2023 – Dec 2025)
    └── inference/{eng,irl,sco}/ # Retro + weekly CSVs
```

---

## Extending the pipeline

Adding a new source requires one scraper file and two lines of registration:

```python
# 1. Create src/<country>/newsource.py with the standard interface
def scrape_newsource(since_date: "date | None" = None, until_date: "date | None" = None,
                     output_path: "str | None" = None, append: bool = False) -> list[dict]:
    """Scrape News Source via [method]."""
    # return list of dicts with url, title, date, text

# 2. Register in src/run.py
SCRAPERS["eng"].append(("newsource", scrape_newsource))
SOURCE_META["newsource"] = {"country": "eng", "type": "think_tank", "institution_name": "News Source"}
```

See [docs/pipeline_decisions.md](docs/pipeline_decisions.md) for source selection criteria and the full decision log.

---

## Ethics

This project has full ethical approval from the UCL Institute of Education Research Ethics Committee (REC2360). All data is from publicly accessible sources. No personal data is collected. No paywalls are circumvented. See [docs/ethics.md](docs/ethics.md).

---

## Known limitations

| Limitation | Detail |
|---|---|
| Ireland/Scotland have fewer articles | Structural finding — reflects real media landscape differences |
| No free education journalism in Scotland/Ireland | TES, Irish Times, Scotsman all paywalled |
| TheJournal.ie blocked mid-project | Login wall appeared after rate limiting. Kept in pipeline. |
| Gov.ie migration dates | Historical articles had wrong dates. Fixed via one-off script. |
| Education Scotland not scrapeable | JS-rendered pages. Would need browser automation. |

See [docs/pipeline_decisions.md](docs/pipeline_decisions.md) §16 for the full table.

---

## Future expansion

| Category | England | Ireland | Scotland |
|---|---|---|---|
| Union | NEU | INTO | EIS |
| Parliament | Westminster Ed Select Committee | Oireachtas | Scottish Parliament |
| Advocacy | Children's Commissioner | Children's Rights Alliance | *(already included)* |

---

## Related repositories

- **[AtlasED Analysis Pipeline](https://github.com/Yorkel/atlas-ed-pipeline)** — NMF topic modelling, BERTopic, JSD divergence, sentiment analysis
- **AtlasED Dashboard** — Streamlit app for exploring cross-jurisdictional education policy discourse

---

**Licence:** Code and documentation available for academic and non-commercial use. © UCL Institute of Education 2026. For commercial reuse, contact l.yorke@ucl.ac.uk.
