# Whose Voices Shape Education Policy?
## Comparative Discourse Ecosystem Analysis: England, Ireland, Scotland
UCL Institute of Education | Updated 22 March 2026

---

## 1. Comparative Source Table

The table below maps each organisation in the corpus to an equivalent functional slot across all three countries. Where a slot is absent in a given country, the cell is left empty. This is a structural map, not a claim about relative importance.

| Slot | England Org | England Type | Ireland Org | Ireland Type | Scotland Org | Scotland Type |
|---|---|---|---|---|---|---|
| Central govt | DfE | Government | Gov.ie | Government | Gov.scot | Government |
| Policy think tank | EPI | Education think tank | ESRI | Broad social research institute | SERA | Academic research assoc. |
| Foundation / funder | Nuffield Foundation | Private foundation | — | — | — | — |
| Data / research body | FFT Datalab | Independent data body | ERC | University research centre | — | — |
| Professional body | FED | Professional body | Teaching Council | Professional body | GTCS | Professional body |
| Professional body 2 | — | — | — | — | ADES | Professional assoc. (leaders) |
| Ed journalism | Schools Week | Specialist ed journalism | Education Matters | Specialist ed journalism | — | — |
| Advocacy / civil society | (not included) | — | (not included) | — | Children in Scotland | Advocacy body |

### Article counts and proportions

| Slot | England | % | Ireland | % | Scotland | % |
|---|---|---|---|---|---|---|
| Central govt | 679 | 17% | 507 | 68% | 188 | 37% |
| Policy think tank | 111 | 3% | 134 | 18% | 24 | 5% |
| Funder | 106 | 3% | — | — | — | — |
| Data / research body | 202 | 5% | 32 | 4% | — | — |
| Professional body | 104 | 3% | 40 | 5% | 117 | 23% |
| Ed media | 2,741 | 69% | 33 | 4% | — | — |
| Civil society | — | — | — | — | 182 | 36% |
| **Total** | **3,943** | | **746** | | **511** | |

> Note: Ireland total reduced from 1,036 to 746 after scraper text quality fixes (22 March 2026). 476 articles with empty text removed (gov.ie landing pages, TheJournal.ie login wall). Teaching Council articles now contain full HTML text (previously WP API excerpts only).

---

## 2. Notes on Comparability

Not all organisations filling the same slot are equivalent in form or function. Three distinctions matter:

### 2.1 Think tanks: form and policy orientation differ

All three countries have an organisation occupying the think tank functional slot, but the institutional type varies significantly:

- **England: EPI (+ Nuffield Foundation)** — EPI is a dedicated education policy think tank producing analysis directly aimed at influencing DfE policy. Nuffield is a private foundation funding education research. Both are part of a mature, well-resourced education policy ecosystem with direct lines to government.

- **Ireland: ESRI** — The Economic and Social Research Institute is a broad social research body covering economics, housing, health, and education. Education is one research area among many. Their education output is academically rigorous but less policy-prescriptive than EPI. The education content was extracted using ESRI's own topic filter (`?research_areas[]=63`).

- **Scotland: SERA** — The Scottish Educational Research Association is an academic membership body, not a policy think tank. Their output is conference proceedings, research summaries, and member communications rather than the policy briefs and rapid-response analyses that EPI produces. Only 24 articles in the corpus reflects this different function.

**Implication for analysis:** The "think tank" topic distribution will reflect different institutional functions across countries. England's think tank content is policy-oriented; Ireland's is broader social research; Scotland's is academic.

### 2.2 Professional bodies: scope and function differ

- **England: FED** — Foundation for Educational Development. School leadership focused.
- **Ireland: Teaching Council** — Statutory regulator for the teaching profession. Publishes regulatory updates, registration requirements, professional standards.
- **Scotland: GTCS + ADES** — GTCS is the statutory teaching regulator (equivalent to Teaching Council). ADES is a professional network for education directors/leaders (closer to FED). Scotland has two sources in this category.

### 2.3 Education journalism: the most significant structural difference

- **England** has Schools Week — a free, dedicated, high-volume education news outlet publishing multiple articles daily (~900/year). This creates a rich, publicly accessible critical media layer between government and the profession. Schools Week alone constitutes 69% of the England corpus.

- **Ireland** has Education Matters — a smaller specialist outlet (33 articles). TheJournal.ie had education coverage but became inaccessible due to a login wall during scraping (163 articles found but all returned empty text). The Irish Times is fully paywalled. RTÉ keeps no archive for the retro period but contributes to weekly inference scrapes (typically 5-9 articles per week from Feb 2026 onwards).

- **Scotland** has no free dedicated education journalism outlet. TES Scotland is fully paywalled. The Herald and Scotsman are also paywalled.

**Implication for analysis:** England's topic model will be heavily shaped by journalistic framing — investigative reporting, editorial commentary, stakeholder reaction pieces. Ireland and Scotland's models will reflect institutional/governmental framing — press releases, policy announcements, research summaries. Cross-country JSD scores will partly measure this structural difference in **who speaks** about education policy, not just differences in **what they say**.

### 2.4 Advocacy: only Scotland has a dedicated source

Children in Scotland is an advocacy body representing children's rights and services organisations. Neither England nor Ireland has an equivalent in the current corpus (Children's Commissioner for England and Children's Rights Alliance for Ireland are on the future expansion list).

This means Scotland's corpus includes a civil society voice that England and Ireland lack. At 35% of the Scotland corpus, this is a significant framing influence.

---

## 3. Structural findings from the data collection process

### 3.1 The education media ecosystem differs fundamentally across jurisdictions

The data collection process itself revealed a key structural difference: **the degree to which education policy is publicly debated through independent media varies dramatically across the three countries**.

England has a mature, open education media ecosystem with Schools Week providing daily free coverage. Scotland and Ireland lack this entirely — their education discourse is mediated primarily through government communications, professional bodies, and (to a lesser extent) research organisations.

This is not a data collection limitation — it is a finding about the structure of education policy discourse in each jurisdiction.

### 3.2 Government dominance varies

| Country | Govt share of corpus |
|---|---|
| Ireland | 68% |
| Scotland | 37% |
| England | 17% |

Ireland's corpus is overwhelmingly governmental — the Department of Education's press releases and publications dominate. Scotland is more balanced between government and civil society. England's government share is diluted by the volume of journalism.

### 3.3 Corpus size reflects real differences

| Country | Articles | Population | Articles per million people |
|---|---|---|---|
| England | 3,943 | 56m | 70 |
| Ireland | 746 | 5m | 149 |
| Scotland | 511 | 5.5m | 93 |

Per capita, Ireland still produces more scrapeable education policy content than England — but it is concentrated in government channels rather than distributed across media and civil society. The reduction from 1,036 to 746 reflects the removal of empty-text articles (gov.ie landing pages, TheJournal.ie login wall) after scraper quality fixes.

---

## 4. Methodological implications for NMF/BERTopic analysis

1. **JSD scores between countries will reflect both policy differences AND structural ecosystem differences.** This should be acknowledged in the analysis.

2. **Topic distributions will be shaped by source type.** England's topics will be more journalistic (framed as stories, controversies, reactions). Ireland's will be more governmental (framed as announcements, initiatives, statistics). Scotland's will mix government and advocacy framing.

3. **The language column allows sensitivity analysis.** A small number of Irish-language articles (3 flagged as `ga`) are retained in the corpus. Their influence on topic models can be tested by running with and without them.

4. **The title-only HE filter was applied consistently across all three countries** to remove articles clearly about higher education/universities. This was a light-touch filter (26 removed from England, 28 from Ireland) that preserves articles mentioning HE in passing while removing genuinely HE-focused content.

---

## 5. Future expansion sources

| Category | England | Ireland | Scotland |
|---|---|---|---|
| Advocacy | Children's Commissioner | Children's Rights Alliance | *(already included: Children in Scotland)* |
| Union | NEU | INTO | EIS |
| Parliament | Westminster Education Select Committee | Oireachtas | Scottish Parliament |

> Adding these would require retraining the NMF model. Deferred to a future iteration.
