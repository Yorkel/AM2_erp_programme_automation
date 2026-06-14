# Reflections & Learning Log

---

### Top-2 predictions — thinking beyond the model (2026-04-03)

During the baseline evaluation (notebook 03), I noticed that recall mattered more than precision for this use case — the curator can remove a wrong suggestion easily but can't find articles buried in the wrong category. This led me to check top-k accuracy, which showed that top-2 captures 82% (vs 62% top-1). Rather than just reporting a single predicted category, the pipeline will show two suggestions with confidence scores so the curator can confirm obvious ones quickly and focus on close calls.

This is a standard approach in applied ML (recommendation systems, medical triage, content moderation) but I arrived at it independently by thinking about what the curator actually needs rather than just optimising the metric. Good reminder that building a useful tool means designing the output for the person using it, not just maximising F1.

---

### Category overlap is a data problem, not a model problem (2026-04-03)

Across all three models (TF-IDF, sentence transformer, DistilBERT), the same three categories cause most errors: `political_environment`, `policy_practice_research`, and `what_matters_ed`. These categories describe different dimensions of the same articles — *who* published it, *what type* of work it is, and *what topic* it covers. A single article can legitimately belong to all three.

False positive analysis on DistilBERT revealed that even a fine-tuned transformer falls back on keyword-like patterns with only 942 training rows — triggering on "teacher" or "school" regardless of the article's actual focus. This reinforces that the bottleneck is label ambiguity and dataset size, not model capacity.

**Lesson:** should have run false positive analysis on the baseline too, not just DistilBERT — would have caught this pattern earlier. Will include it for the final model in notebook 07. Also worth discussing with curators whether multi-label classification (articles belonging to multiple categories) would be more honest than forcing a single label.

---

### The remaining misses aren't model failures — they're labelling disagreements (2026-04-03)

After running all 5 models, the same ~11 articles appear in every model's missed list. These are articles where the curator made a reasonable judgement call but an equally reasonable alternative exists. No model can predict which way the curator will go because both labels are valid.

This means 93.4% top-2 accuracy is probably the ceiling for single-label classification on this data. The remaining 7% is genuine ambiguity — two curators might disagree on these too.

---

### Curator editorial balancing justifies top-2 even further (2026-04-03)

The curators mentioned they also balance articles across newsletter sections — if one section has too many articles, they'll move some to another section where they also fit. This means the "correct" label can change week to week based on editorial context the model can't see.

Top-2 suggestions are essential for this workflow: the model identifies which categories an article is relevant to, and the curator slots it into whichever section needs filling. The model does relevance matching, the curator does editorial balancing. This isn't a workaround for model weakness — it's the right design for how the newsletter is actually produced.

---

### AM2 as an empirical Structured Specification Testing paper — connecting to theory (2026-04-03)

Running five different models on the same newsletter corpus and getting meaningfully different classification outputs is an empirical demonstration of specification sensitivity. The outcome is not solely a function of the data, but of the specification choices made by the engineer — which model, which features, which prompt wording. This connects AM2 to the Structured Specification Testing framework as a second domain proof alongside AtlasED (unsupervised topic modelling). Two ML paradigms, same structural finding.

**Three concepts from the AM2 evidence:**

**1. Specification sensitivity** — F1 variance per class across the five models shows which categories are most sensitive to the model specification choice. Classes with high variance (like `policy_practice_research` ranging from 0.54 to 0.75 recall across models) are where the specification matters most. This is Specification Sensitivity operationalised in a classifier context — the same argument made with JSD and Wasserstein in AtlasED, now shown with F1 variance across model specifications.

**2. Proxy concentration** — the TF-IDF top features inspection (notebook 03) revealed that "Wales" is the top feature for `four_nations` and "schoolsweek" is a top feature for `political_environment`. The question is whether these words are genuinely measuring the construct (the policy category) or are proxies — author names, publication names, country-specific terminology. If "Wales" is the top feature for `four_nations`, that's a proxy concentration problem: the model is using geography as a shortcut for a construct that's supposed to be about policy scope. This directly mirrors Obermeyer et al. (2019) — a single proxy choice systematically distorts what the model is actually measuring.

**3. Prompt specification as engineering choice** — DSPy rewrote the category descriptions to be generic textbook definitions, stripping out the curator-specific disambiguation cues. The result was worse (0.634 vs 0.717). Three prompt specifications on the same model (zero-shot, hand-crafted few-shot, DSPy-optimised) produced three different results. This demonstrates that prompt wording is a consequential specification choice — and that automatic optimisation without domain understanding can make things worse. The prompt's value comes from encoding knowledge that isn't in the training data; automating prompt writing strips out exactly the thing that made it good.

**4. Low variance ≠ robustness** — `teacher_rrd` has the lowest F1 variance across all models (0.0003) but the false positive analysis reveals 11 false positives from a consistent shared bias. All models trigger on "teacher" mentions because "policy affecting teachers" and "teacher workforce issues" are semantically near-identical — the difference is editorial intent, not meaning. Low specification sensitivity can mask systematic error when all specifications share the same proxy. This is a methodological finding: specification sensitivity metrics must be paired with error analysis to avoid false confidence in low-variance categories.

**5. Metadata as a specification choice** — adding one-hot encoded metadata hurt TF-IDF (-6.5 points) but helped sentence transformer (+1.5 points). Same features, same data, different model specification → opposite effect. Whether to include metadata is itself a consequential specification choice whose impact depends on the model it's paired with.

**6. Calibration divergence across specifications** — TF-IDF and sentence transformer are underconfident, DistilBERT is overconfident. Same val set, same predictions, different confidence profiles depending on model specification. The hybrid routing threshold depends entirely on which model's calibration you trust — a practical consequence of specification sensitivity.

**7. Preprocessing as specification choice** — minimal text preprocessing (keep casing, punctuation, no stemming) favours transformer/embedding models over TF-IDF. More aggressive preprocessing might have improved TF-IDF but wouldn't change the fundamental limitation: keyword matching can't distinguish "policy affecting teachers" from "teacher workforce issues." Worth testing to quantify the effect, but the ceiling for keyword matching is lower than embeddings regardless. This is an honest self-reflection: the preprocessing choice shaped which models could succeed.

**8. Ground truth as specification** — calibration plots show both TF-IDF and ST are consistently above the diagonal (more accurate than labels suggest). This means the models are learning real patterns that the labelling schema doesn't cleanly capture. The ground truth labels are themselves a specification — the curator's editorial judgement on a given day. A different curator, or the same curator on a different day, might have labelled differently. For the SST framework: specification sensitivity isn't just about model choice, it includes the labelling specification itself. Inter-annotator agreement testing would quantify this.

**9. Label consistency check — ground truth disagrees with itself** — motivated by the finding that all five models struggled on the same ~11 articles and that calibration curves showed both models were more accurate than labels suggested. If models consistently "get it wrong" on the same articles, maybe the labels are wrong, not the models. Found semantically near-identical articles with different labels in the training data: "Revisiting the notion of teacher professionalism" (Müller & Cook) was labelled `teacher_rrd` in one newsletter and `policy_practice_research` in another (cosine similarity 0.884). Same paper, same curator, different label. This confirms the ~7% model miss rate includes cases where the ground truth itself is inconsistent. The model's ceiling is bounded by human labelling consistency, not just model capacity. **Limitation:** inter-annotator agreement testing was not possible as only one curator labels the newsletter. If a second annotator were available, measuring agreement would establish the human ceiling that any model should be compared against — recommended for future work.

**10. Low proxy concentration strengthens the specification sensitivity argument** — the TF-IDF model is mostly construct-driven (only 5/60 top features are proxies at 8.3%). This means the specification sensitivity found across models (edtech variance 0.015, F1 range 0.30) comes from genuine differences in how models process the same construct terms, not from proxy shortcuts. The same good features produce different results depending on which model processes them — the specification is the model architecture itself, not the feature selection. For the SST paper: proxy concentration analysis is a necessary audit step (to rule out proxies as the explanation), but the real specification sensitivity in this data comes from model architecture choices.

**11. Prompts are specifications, not neutral instructions** — the +19 over-prediction of `policy_practice_research` by Claude is a direct consequence of the category description wording ("research reports, academic studies, evidence reviews"). Different wording → different results, as proven by DSPy (0.634 vs 0.717). There is no neutral prompt — every wording encodes a normative position about what the categories mean. Proxy analysis for LLMs is an open research question: you can't extract feature weights like TF-IDF, but the prompt itself is the specification that shapes which signals Claude prioritises. The ablation approach (removing source names from articles and checking if predictions change) and chain-of-thought analysis are potential methods — flagged for future work.

**12. What specification analysis revealed that accuracy alone couldn't** — without this analysis, we would have just said "sentence transformer scored 0.765, best model, done." The SST framework revealed: (1) model choice matters more for some categories than others (edtech swings 0.30, teacher_rrd barely moves); (2) low variance can hide shared bias (teacher_rrd looks stable but all models share keyword-triggering); (3) Claude and ST aren't just different in accuracy, they answer different questions (65% disagreement with systematic direction); (4) ground truth is itself a specification (same article labelled differently by the same curator); (5) prompt wording changes outcomes by 0.28 F1 for some categories; (6) the model uses legitimate features, not shortcuts (8.3% proxy concentration). Accuracy tells you *how well*. Specification analysis tells you *why, how reliably, and what could go wrong*.

**13. Proxy concentration as a general audit method** — the construct vs proxy classification of top features is not specific to this project. Any classification model can be audited by extracting top features and asking: does this feature measure the construct, or does it correlate with the construct for a reason you don't want? `four_nations` at 8/10 proxy features is the clearest example — the model classifies by geography rather than devolved policy content. High performance with proxy features means the model works but is fragile: it breaks when the correlation stops holding (e.g. a Welsh policy article that doesn't mention Wales). This mirrors Obermeyer et al. (2019) and Zech et al. (2018) in medical imaging. For the SST paper: proxy concentration is a general method that can be proposed as a standard audit step for any classification pipeline.

**11. Normative divergence** — where Claude zero-shot disagrees with fine-tuned DistilBERT, the direction of disagreement matters. Claude is systematically more likely to assign articles to `policy_practice_research` (classifying by document type) while the trained models follow the curator's labelling (classifying by newsletter section relevance). This asymmetry is Normative Divergence — the LLM's world knowledge encodes different assumptions about what belongs in a category than the labelled training data does. The disagreement is structurally patterned by what each model treats as the authoritative definition of the category — not random noise.

---

### SHAP changed the production model — interpretability isn't optional (2026-04-05)

The most consequential decision in this project came from SHAP analysis, not from accuracy metrics. The ST + metadata model (0.765) looked like the obvious production choice. SHAP revealed it classifies by source type rather than content for 4 of 6 categories. Proxy concentration averaged 27.6%, with two categories above 40%. Metadata-only scored 0.316 (near random) — confirming the embeddings do the real work and metadata is a shortcut LogReg prefers, not a genuine dependency.

Bootstrap CIs overlap (0.696–0.823 vs 0.678–0.812) — the +1.5 F1 difference isn't statistically significant. We chose the lower-scoring model because it does what we actually want: classify by content. "I chose a lower-scoring model because SHAP showed the higher-scoring one was taking shortcuts" — that's the strongest single decision in the project for the assessment.

**Lesson:** accuracy alone is insufficient for model selection. Without SHAP, we would have shipped a model that classifies articles by who published them rather than what they say. Interpretability isn't a nice-to-have — it's how you catch specification shortcuts.

---

### Global vs individual SHAP tells different stories (2026-04-05)

Individual article SHAP showed `what_matters_ed` as diffuse and unclassifiable (0.45 confidence, competing signals, no distinctive vocabulary). The global averaged SHAP revealed a coherent poverty/welfare theme — "Poorer", "poverty", "households", "hungry", "eligible", "absences". Individual articles use different poverty vocabulary but the concept is consistent.

**Lesson:** the level of analysis (individual vs aggregate) is itself a specification choice that changes what you find. SpecCheck should report both — article-level for debugging, category-level for specification auditing.

---

### Real-world data humbles you (2026-04-05)

Val set: 0.750 macro F1, 91.6% top-2. Real data: 0.527 macro (0.630 weighted), 87.4% top-2. The gap isn't model failure — it's a data source mismatch. The model was trained on curated newsletter articles (editorially balanced, clearly categorised) and deployed on unfiltered media source articles (46% political news, ambiguous, not pre-selected for category clarity).

Embedding drift confirmed the content is semantically familiar (0.590 vs 0.594). The lower confidence (0.48 vs 0.59) is honest uncertainty on harder articles, not unfamiliar content. The model understands the text; it's just less sure which category to pick.

**Lesson:** always validate on real deployment data, not just held-out training data. The val set was a stratified sample of the same curated distribution — it told us how well the model handles easy, clearly-categorised articles. The real test is unfiltered source feeds where articles are ambiguous and the distribution doesn't match training.

---

### Top-2 is compensation, and that's honest (2026-04-05)

The top-2 system (87.4%) compensates for top-1 weakness (weighted F1 0.630). This is a deliberate design choice — the SHAP misclassification analysis showed every wrong prediction is a multi-label article. But it's worth being explicit: the model's actual classification ability is 0.630, not 87.4%. Top-2 is a UX layer on top of a model that struggles with 3 of 5 active categories on real data.

The path to improving top-1 (not just top-2): retrain on curator-labelled source feed articles, add research sources to the pipeline, class-specific confidence thresholds, active learning on low-confidence articles.

---

### The curators are the specification (2026-04-06)

After building the dashboard and showing it real articles, the most important realisation: the model surfaces options, but the curator makes the editorial call. The "correct" classification depends on how many articles are in each section that week, what was covered last week, what's timely, what the programme directors care about. These are editorial decisions no model can learn from data alone.

This is why top-2 is the right design — not because the model is weak, but because classification for a newsletter isn't a pure prediction task. It's a recommendation task where the final decision involves context the model can't see. The model handles the 80% that's obvious; the curator handles the 20% that requires judgement.

For the SST framework: the curator's editorial process is itself a specification. Different curators would produce different newsletters from the same classified articles. The "ground truth" isn't fixed — it's a function of the curator specification applied that week.
