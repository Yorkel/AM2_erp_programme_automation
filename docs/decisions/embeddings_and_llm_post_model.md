# Taxonomy findings & transferable insights

What the held-out evaluation (NB11), embedding separability (NB13), and the LLM comparison (NB14)
revealed about the classifier's category structure — and the generalisable lessons. Companion to
`model_redesign_and_retraining.md`. Engineering/analysis record, not the AM2 prose.

---

## 1. The headline finding: the taxonomy mixes three organising principles

The six curator categories are not all the same *kind* of thing. Three independent methods agree:

| Category | Confusion matrix (NB11) | Embedding purity (NB13) | Unsupervised KMeans (NB13) | Verdict |
|---|---|---|---|---|
| edtech | clean (0.82 F1) | 0.79 | own cluster, purity 0.89 | **real content topic** |
| teacher_rrd | clean (0.74) | 0.67 | own cluster, purity 0.79 | **real content topic** |
| four_nations | clean (0.90 F1) | 0.61 | **no cluster** — scattered | **geographic cross-cut, learned lexically** |
| policy_practice_research | confused (0.59) | 0.52 | smeared, purity 0.52 | **editorial framing** |
| political_environment_key_orgs | confused (0.50) | 0.45 (**negative silhouette**) | smeared, purity 0.40 | **editorial framing** |
| what_matters_ed | confused (0.65) | 0.49 | **two** low-purity clusters | **umbrella over sub-themes** |

*(Confusion-matrix F1s are the skew-corrected held-out values, 2026-06-12 re-run. The triangle is still
the ceiling but narrower than the pre-fix read: editorial 0.50-0.65 vs concrete 0.82-0.90. Embedding /
cluster numbers are from NB13, which used the correct input and are unaffected by the skew fix.)*

The three "principles": **content topic** (edtech, teacher_rrd) · **geography** (four_nations) ·
**editorial framing** (the policy/political/what_matters "triangle"). Forcing them into one flat,
single-label scheme produces confusion exactly at the principle boundaries — which is where ~24 of
the model's ~41 held-out errors land.

### Key numbers
- Embedding purity: **concrete 0.69 vs editorial 0.49** (k=10 neighbours).
- Editorial-trio 3-way silhouette **0.021** (≈ inseparable) vs concrete trio **0.101** (~5×).
- Trio centroid cosine distances: political↔what_matters **0.079** (closest), policy↔political **0.115**.
- Unsupervised clusters vs curator labels: **ARI 0.21, NMI 0.27** — moderate, and *that is the finding*.
- **Class size ≠ performance (rules out "more data" as the fix):** four_nations is the *smallest*
  training class (165) yet the *best* (F1 0.90); political is the *largest* (315) yet the *worst* (0.50);
  policy (221) and what_matters (256) are mid-to-large yet weak. The weak classes are **not
  under-sampled** — they have plenty of data and overlap in *meaning*. Collecting more data for them
  wouldn't help; the ceiling is label design, not data quantity. (Class balance is moderate overall,
  12–22%, so imbalance isn't driving the gaps either.)

## 2. The four_nations insight (resolves the purity-vs-F1 puzzle)
four_nations has the **best held-out F1 (0.90)** but **no content cluster** — its 165 items scatter
across every cluster (69 land in the curriculum/Ofsted cluster — note "wales" is in that cluster's
top terms). Reason: it isn't a *topic*, it's a *geographic tag* that cross-cuts the real topics. The
classifier nails it via a cheap **lexical signal** (nation names), which is why purity (proximity) is
only middling while F1 (a learned boundary) is top. **Design implication:** four_nations should be a
**separate geographic facet/tag**, not a peer content category. The taxonomy conflates two axes
(content × geography) — faceted / multi-label territory.

## 3. The what_matters_ed insight (blind LLM naming, NB13/NB14)
Naming the discovered clusters from keywords *without* the labels, then comparing:
- edtech → "AI in Education", teacher_rrd → "Teacher Recruitment/Retention/Pay" (**exact match** — validated)
- policy → "Policy, Research & Evidence" (match); political → "Curriculum, Ofsted & Inspection" (the data
  organises it by *subject*, the curator by *organisation* — different axis)
- **what_matters_ed splits into TWO distinct themes:** "Pupil Attendance & Absence" and
  "Child Poverty & Young People". An independent namer would never group these — `what_matters_ed` is an
  **umbrella**, a candidate to *split*, not merge.

Two directions of "missing category": four_nations = a taxonomy category with **no data cluster**;
attendance + child poverty = data clusters with **no taxonomy name**.

---

## 4. The stakeholder tension (the most important insight)
This conflicts with what the curator wants — and that's the point.

- The **curator isn't wrong**; they optimise a different objective. ML wants *content-separable*
  categories; the editorial taxonomy serves *readers* (a "what matters" section exists because the
  audience cares, not because it's statistically clean). The conflict is **model-learnability vs
  editorial-utility** — two legitimate goals.
- **A taxonomy can be correct for its purpose and unlearnable for ML at the same time.** Curator
  "stubbornness" is fitness-for-editorial-purpose, not error.
- **Resolution — decouple internal from external taxonomy:** the model classifies on a
  content-optimised internal scheme (geography as a facet, what_matters split) and **maps back** to the
  curator's editorial categories for display. Curator keeps their sections; model gets learnable targets.
- **Human-in-the-loop already absorbs the conflict:** the curator reviews everything, so the model only
  needs good top-2 candidates, not a perfect call on a fuzzy boundary.
- **Engineer's role = evidence, not override:** bring the clustering/blind-naming to a conversation
  ("the data suggests what_matters is two things — want to split it?"); the editorial call stays theirs.
  (S27/K21 stakeholder collaboration.)

## 5. Trained model vs LLM — what NB14 actually showed (hypothesis refuted)

**We hypothesised the opposite of what we found.** The intuition was: an LLM *following the curator's
written boundary rules* should beat a trained model on the fuzzy triangle, since the trained model has
to *learn* an (apparently) unlearnable boundary. **NB14 refuted it.**

**Clean, controlled result** (after fixing two setup artefacts — see §5a):
- Claude few-shot **held-out 0.634** vs production **0.725** (−0.09) — competitive, not catastrophic.
- **Val control: Claude 0.724**, reproducing NB06's ~0.717 (1 parse error) → the setup is sound, so the
  held-out gap is a **real data effect**, not an artefact.
- Claude **wins four_nations (1.00)**, is close on the other concrete classes, and **ties on top-2
  (0.879 = production)** — for a top-2 human-in-loop surface, Claude is just as useful.
- Claude **loses the editorial triangle (0.39 vs 0.58)**, especially policy (0.24 vs 0.59).

**Mechanism:** Claude systematically reads research-sector orgs (UKRI, British Academy, UPEN, NCCPE) as
*political* where the curator labels *policy*. The curator's policy/political boundary is **idiosyncratic
and only learnable from many labels**, not expressible in a prompt rule. Claude also drops more
val→held-out (0.724→0.634) than production (0.750→0.725), because the held-out is heavy on exactly these
research-org items.

**Corrected principle (reverses our guess):** for a taxonomy whose boundary is *idiosyncratic to the
labeller*, a model **trained on the curator's labels beats rule-following — even on the fuzzy classes.**
An LLM wins only where the boundary is genuinely *rule-expressible* (e.g. four_nations = a country name).
Best of both = a **hybrid** (trained model overall; LLM or top-2 surfacing where it adds value on the
clear classes). The trained model also wins on cost, determinism and reproducibility (see §5a).

### 5a. LLM output-reliability is fragile (a finding in its own right)
Just *measuring* Claude reliably took two fixes the trained model never needs:
1. **Prompt-format sensitivity** — the *same* few-shot examples as a flat `[tag]` list vs grouped under
   category headers changed the score materially. Cosmetic layout, not content.
2. **Output-parsing brittleness** — asking for JSON-in-prose and `json.loads`-ing it failed on many
   responses (code fences / preamble / truncation), producing a **fake 0.149** that was really a
   parse-failure *rate*, not a classification score. Needed robust regex extraction + larger max_tokens.

**Implication:** an LLM classifier needs careful prompt **and** output engineering before its numbers can
even be *trusted*, whereas the trained model returns a deterministic, reproducible result. That
**reliability gap is real evidence for the trained model in production**, independent of where the final
accuracy lands.

---

## 6. Transferable engineering principles (CPD / Engineering Principles)
1. **Validate a taxonomy against the data before committing** — embed → cluster → blind-name → compare.
   Surfaces phantom categories (taxonomy has, data lacks) and missing ones (data has, taxonomy lacks).
2. **Triangulate** — confusion matrix, kNN purity, silhouette, unsupervised clusters, blind LLM naming;
   each is blind to something. The four_nations puzzle only resolved across multiple lenses.
3. **"The classifier can predict it" ≠ "it's a real concept"** — four_nations is lexically learnable but
   not a semantic cluster. High accuracy can hide an incoherent category.
4. **The ceiling often lives in the labels, not the model** — when categories overlap *in the data*, no
   model separates them; spend effort on label design, annotation guidelines, IAA.
5. **Real taxonomies are faceted; we force them flat** — content × geography × source × frame are
   different axes; flat single-label collapses them and errors cluster at the axis boundaries.
6. **embed → cluster → blind-name → compare is a reusable taxonomy-audit recipe.**

## 7. Clustering in future newsletter research — role and limits
Clustering is a **discovery & monitoring** tool, not a taxonomy replacement. It organises by dominant
content vocabulary, so it will **merge** editorial framings that share words, **miss** cross-cutting
attributes (geography, audience, source), and **split** umbrellas into sub-themes. Right jobs:
emerging-theme detection ("what's new this week"), **drift monitoring** (a new cluster over time = a
distribution shift), and periodic taxonomy audits. Newsletter cautions seen in this run: short text →
weak clusters (silhouettes ~0.1); **source-name leakage** into topics (`schoolsweek`, `upen` surfaced
as topic words — they're sources); topics evolve → re-cluster, don't freeze.

### Other approaches (menu)
- **Representations:** stronger embedder (MPNet/E5/BGE/GTE); domain-adapted/fine-tuned; LLM embeddings;
  **aspect/instruction embeddings** (embed once "for topic", once "for geography" — attacks the faceting).
- **Algorithms:** HDBSCAN (variable k + noise bucket isolates cross-cuts like four_nations); BERTopic;
  hierarchical/agglomerative (reveals the umbrella tree); soft/GMM (partial membership matches fuzziness);
  LDA/NMF; choose k via silhouette/elbow/gap rather than forcing k=6.
- **Faceted design (the real fix):** multi-label; hierarchical (concrete vs editorial, geography a branch);
  pull geography out via NER → tag, cluster only on content.
- **LLM-driven:** few-shot with boundary rules; **taxonomy induction** (ask the LLM to propose a taxonomy
  from scratch, compare to curator's); reproducible blind cluster-naming; LLM-as-judge for boundary cases.
- **Validating clusters:** inter-annotator agreement; cluster stability (bootstrap/over time);
  intrinsic (silhouette/Davies-Bouldin/Calinski-Harabasz) + extrinsic (ARI/NMI/homogeneity/completeness).

## 8. Cross-country insights (if this extends beyond the four UK nations)
1. **Geography is always a facet, never a content category** — the four_nations lesson generalises to
   "country": tag it structurally, cluster content separately.
2. **Taxonomies are nationally specific** (Ofsted/GCSE don't transfer) — re-audit per country; the audit
   *method* transfers even when the taxonomy doesn't.
3. **Multilingual is a representation problem** — use multilingual embeddings (LaBSE, multilingual-E5) or
   language dominates clustering (everything in one language clusters together regardless of topic).
4. **Cross-country comparison needs a shared embedding space** so equivalent topics align across countries.
5. **Monitor drift per country** — distributions shift independently.

## 9. Publication seed
There is a **practitioner / case-study / methods paper** here, not a novel-algorithm paper:
*"Auditing a stakeholder-imposed taxonomy against the data (embed → cluster → blind-LLM-name → compare),
and the editorial-utility-vs-model-learnability tension in human-in-the-loop curation."* To be
publishable it needs: the method applied to >1 dataset, formal evaluation, and positioning against the
faceted-classification + LLM-taxonomy-induction literature. Venues: applied-ML / ed-tech / HCI-CSCW
(the human-in-the-loop angle). Pairs with the existing BERA workstream.

---
Related: `model_redesign_and_retraining.md`, NB11 (held-out + skew fix), NB13 (separability + unsupervised),
NB14 (LLM vs production), NB06/NB08 (Claude classifiers + the "triangle").
