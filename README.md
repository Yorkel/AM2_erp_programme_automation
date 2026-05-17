---
title: ERP Classifier
emoji: 📰
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8000
pinned: false
---

# ERP Newsletter Automation — AM2

Semi-automation of the weekly ESRC Education Research Programme newsletter. The newsletter has been manually curated since July 2023 by two team members who spend approximately 7 hours per week scanning ~55 sources, assigning articles to sections, deduplicating, and writing editorial descriptions.

This project builds a pipeline to handle the administrative sorting — gathering, classifying, and deduplicating — so the curators focus on editorial judgement.

---

## What this builds

| Component | What it does |
|---|---|
| **Section classifier** | Given an article title, predicts which of 6 newsletter sections it belongs in |
| **Semantic deduplication** | Groups articles from different sources covering the same story |
| **Newsletter draft** *(stretch)* | Generates a structured draft from classified + deduplicated articles |

Five models are trained and compared for the classifier — from a TF-IDF baseline to fine-tuned transformers to LLM-based zero/few-shot classification. See [docs/project_plan.md](docs/project_plan.md).

---

## Project structure

```
data/
├── raw/
│   └── newsletters_html/         102 HTML newsletter files (issues 3–102)
├── processed/
│   └── newsletter_items_nov.csv  1,668 extracted items, issues 1–87
└── training/
    └── classifier_training.csv   Clean labelled data (after label normalisation)

docs/
├── project_plan.md               Full plan: models, phases, tech stack
├── next_steps.md                 5 immediate next steps
├── process_curators_follow.md    Current manual process + questions for curators
├── datasets.md                   Dataset descriptions and label normalisation map
├── reading_list.md               Transformers, LLMs, MLOps — ordered reading list
└── ethics_security.md

notebooks/
├── 00_label_normalisation_eda.ipynb   (to create)
├── 01_experiment_setup.ipynb          (to create)
├── 02_baseline_classifier.ipynb       (to create)
└── [legacy exploratory notebooks]

src/
├── extract/
│   ├── extract00_newsletters.py       Parses HTML newsletter files → CSV
│   └── extract01_full_article.py      Fetches full article text from URLs
├── classify/                          (to build)
└── pipeline/                          (to build)

models/                                Saved model artefacts (gitignored)
```

---

## Current status

- [x] Training data extracted: 1,668 labelled items from 87 newsletters
- [x] Section taxonomy confirmed: 6 classifiable sections
- [ ] Issues 88–102 extracted
- [ ] Label normalisation complete
- [ ] Baseline classifier built
- [ ] Transformer models trained and compared

See [docs/next_steps.md](docs/next_steps.md) for the immediate to-do list.

---

## Newsletter sections

| Section | Label |
|---|---|
| Teacher recruitment, retention & development | `teacher_workforce` |
| EdTech | `edtech` |
| Political environment and key organisations | `political_environment` |
| Four Nations | `four_nations` |
| Research – Practice – Policy | `research_practice_policy` |
| What matters in education? | `what_matters` |

*Update from Programme* and *Update from PI* are internal sections — always manually written, not classified by the model.

---

## Installation

```bash
pip install -r requirements.txt
```
