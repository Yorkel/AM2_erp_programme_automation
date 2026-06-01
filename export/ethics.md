# Ethical Considerations

This document outlines the ethical considerations relevant to the data collected and used by this pipeline, covering data provenance, storage, scraping conduct, representation and the politics of AI-assisted analysis.

## 0. Ethics approval

This project has full ethical approval from the UCL Institute of Education Research Ethics Committee.

- **Reference:** REC2360
- **Title:** Whose Voices Shape Education Policy? Using AI to Reveal Inequalities in Public Debates Across England, Scotland and the Republic of Ireland
- **Data protection number:** Z6364106/2026/02/116
- **Approved:** 16 March 2026

---

## 1. Data provenance — all content is publicly available

All documents scraped by this pipeline are:
- Published on publicly accessible websites with no login, paywall or access restriction
- Produced by public bodies, registered charities, research organisations or commercial publishers in their capacity as public communicators
- Intended for public consumption (press releases, policy publications, research reports, news articles)

No personal data is collected. No data is collected from individuals. The pipeline collects institutional communications only.

No consent is required for collection or analysis. The pipeline does not engage with personal data and does not fall within the scope of data protection legislation in this respect.

---

## 2. Data storage and security

- All scraped data is stored **locally only** — the `data/` folder is gitignored and never pushed to any remote repository
- No scraped content is shared with third parties
- Data is stored in Supabase with row-level security enabled and access restricted via service key
- The training corpus and inference datasets are used solely for the research and analytical purposes described in this repository

---

## 3. Scraping conduct

- All scrapers include polite request delays (0.5–5 seconds between requests) to avoid placing excessive load on source websites
- Scrapers identify themselves via a descriptive User-Agent string
- No authentication bypass, rate limit circumvention or aggressive crawling is used
- The pipeline only collects content already publicly indexed and accessible

---

## 4. Representation and source selection

The selection of sources is a methodological and political decision that shapes what the tool "sees". This is made explicit rather than treated as a neutral technical choice.

**Current England sources** represent a particular slice of the education policy discourse: government communications, established think tanks, data-focused research organisations, a professional body, and mainstream education journalism. This reflects the institutional voices that are most prominent in formal policy debate.

**What is not included:** Grassroots organisations, teacher unions, parent groups, community voices and practitioner networks are not represented in the current corpus. The pipeline captures what institutions publish, not what teachers, parents or students say. This is a known limitation and is stated explicitly — the downstream analysis examines which voices are amplified in formal policy discourse, not which voices matter in education.

**Cross-jurisdiction design:** Scotland and Republic of Ireland sources are now included in the corpus. Running these through an England-trained model is deliberate — the places where the model's categories fit poorly reveal the England-centric assumptions built into the tool. This is central to the analytical purpose of AtlasED.

**Paywalled sources excluded:** Several potential sources (TES Scotland, Irish Times, TheJournal.ie) were excluded because their content is behind paywalls or login walls. No paywall circumvention was attempted. This is documented as a structural finding about the education media landscape — free, dedicated education journalism is largely absent in Scotland and Ireland.

---

## 5. The politics of AI-assisted analysis

This project takes seriously the political assumptions embedded in AI text analysis tools:

**What counts as a theme** is shaped by training data. A model trained only on English sources will categorise Scottish and Irish education debates through an English policy lens — this is not a neutral act.

**What gets coded as a priority or concern** depends on whose documents are included in the corpus. Underrepresented communities, regions or policy traditions may not appear as distinct topics even if they are active in public debate.

**Whose documents are included** encodes assumptions about institutional authority — what counts as a legitimate source of policy knowledge.

AtlasED is designed to make these assumptions visible rather than hide them. It is presented to users as a tool that encodes particular choices, which can and should be interrogated — not as an objective classifier producing authoritative results.

**Pipeline boundaries are not neutral:** The weekly inference batches impose an arbitrary time boundary (e.g. 9–15 January). An article published late on the last day of a window may appear in that week's batch or the following one depending on scraper timing. A system that reports "the top education topics this week" is not simply describing reality — it is constructing a particular slice of it. This boundary instability is preserved intentionally in the data rather than silently fixed, and is treated as a substantive observation about how automated pipelines shape the knowledge they produce.

**Evaluation without ground truth:** The topic model is evaluated through internal metrics (coherence scores) and qualitative inspection rather than comparison to pre-defined correct labels. This is standard practice for unsupervised topic modelling, but it means the model's output categories are not validated against any external standard of what education policy "really" covers. The categories that emerge reflect patterns in the training corpus — which is itself a curated selection of institutional voices. This is stated explicitly rather than treated as a limitation to be minimised.

---

## 6. Downstream use

**Newsletter automation:** Summarises recent education policy coverage. No individual-level data involved. Output is a communication tool, not an analytical claim.

**AtlasED:** An interactive tool with two purposes:

1. **Practical** — allows users to explore what topics are discussed, which voices are dominant, and how sentiment shifts across time and jurisdiction
2. **Critical** — by making its assumptions transparent and inviting users to challenge them, AtlasED is designed to surface the political choices embedded in AI-assisted policy analysis, not just to report on what it finds

Neither use involves automated decision-making that affects individuals.

---

## 7. Transparency

- Source selection criteria and exclusions are documented in [pipeline_decisions.md](pipeline_decisions.md) and in the scraper code itself
- The codebase is publicly available, allowing scrutiny of what data was collected and how
- Limitations of the corpus will be stated explicitly in any publications or outputs that draw on it
- Known data limitations (migration dates, empty text, language detection) are documented in project documentation
- Claude Code is used to assist with code review and generation; all AI-generated code is reviewed before committing
