# Deciding What to Measure: A Construct-Validity Protocol for Evaluating Deployed Text Classifiers

*Target venue: ACM FAccT. Status: draft. `[CITE]` = reference pending the Section 2 lit search; `[confirm]` = value to verify before submission.*

*Alternative titles: "Measuring the Right Thing: A Construct-Validity Protocol for Evaluating Deployed Text Classifiers"; "Label Problem or Model Problem? ..."*

---

## Abstract

Machine learning is increasingly used to sort text into expert-defined category schemes: taxonomies that encode contestable editorial, professional, or policy objectives rather than naturally separable structure. Such systems are typically evaluated with a single accuracy or F1 score, and weak per-class performance is read as a technical fault to be fixed by retraining. We argue that this is incomplete. A category may be hard to predict not because the model is weak, but because the label is ambiguous, cross-cutting, internally heterogeneous, or designed for human judgement. Evaluation should therefore function diagnostically: its purpose is not only to measure whether a model predicts labels correctly, but to reveal where the structure learned from data diverges from the human objectives a category was meant to serve.

We present a lightweight, model-agnostic protocol that triangulates three signals: a classifier's confusion structure, unsupervised embedding separability, and blind large-language-model cluster naming, in which an LLM names emergent groups without seeing the original taxonomy. To separate label-definition problems from model-capacity limits, we add a controlled comparison against a general-purpose LLM given the same taxonomy. We demonstrate the protocol through an anonymised education-sector classifier, though the diagnostic logic applies to any domain where machine-learned structure must be reconciled with a human category scheme.

The case shows that aggregate scores can mislead. A high-scoring category may lack a coherent topical construct because it functions as a cross-cutting facet rather than a topic; a low-scoring category may conflate two distinct themes; and others remain difficult because they encode overlapping editorial judgements by design. A general-purpose LLM, given the same taxonomy, does not outperform the deployed model (macro F1 of roughly 0.63 against 0.73) and fails on the same categories, locating the limit in the label definitions rather than in model capacity. We map each diagnosis to a concrete remedy: revise the label, re-implement the category as metadata or a filter, or retain human judgement. As AI comes to mediate consequential classification at societal scale, single-score evaluation conceals exactly these construct-validity failures; the protocol makes them visible and, with it, auditable. We offer a reusable checklist for practitioners and auditors who need to know not merely whether a classifier performs, but whether it performs the right task.

---

## 1. Introduction

Machine learning is increasingly used to sort text into category schemes designed by people: editorial sections, policy categories, clinical codes, content-moderation taxonomies. These schemes are not natural kinds. They operationalise human objectives that are professional, editorial, or political, and they are built for human purposes rather than for predictability `[CITE: text-as-data / applied ML classification]`.

Such systems are typically evaluated with a single aggregate score, accuracy or F1, and a category that scores poorly is read as a model deficiency to be fixed with more data or retraining. We argue this is incomplete. A category can be hard to predict not because the model is weak, but because the label is an invalid operationalisation of the thing it claims to capture: ambiguous, cross-cutting, internally heterogeneous, or contested by design.

Drawing on measurement theory `[CITE: construct validity / measurement foundations]`, we reframe the problem. A classifier's categories are operationalisations of latent constructs, and evaluation should test their construct validity, not only their predictive accuracy. This separates two questions that a single score conflates: whether the model predicts the labels well (a model problem), and whether the labels validly capture the construct they claim to (a construct, or label, problem). Crucially, the model and the curator are answering different questions: the curator's category encodes what the content is for, an editorial purpose, while the model can only report what is separable in the text. Where the two diverge, the model is not proposing a better taxonomy; it is reporting whether the category corresponds to separable structure, and the curator retains authority over what the category is for. The measurement-modelling view of fairness makes the same move for harm `[CITE: Jacobs and Wallach]`; we extend it from a conceptual lens into a runnable diagnostic for deployed classifiers.

We make the idea operational with a lightweight, model-agnostic protocol that brings construct-validity evidence to bear on a deployed model. It triangulates a classifier's confusion structure (discriminant evidence), unsupervised embedding separability (structural evidence), and blind large-language-model cluster naming (whether the construct is recoverable from the data), and adds a controlled comparison against a general-purpose LLM given the same taxonomy to separate a construct-validity failure from a model-capacity limit. We demonstrate the protocol on an anonymised education-sector classifier, though the logic applies wherever machine-learned structure must be reconciled with a human category scheme.

This matters beyond any single system. As AI comes to mediate consequential classification at societal scale `[CITE: AI auditing / EU AI Act]`, single-score evaluation conceals exactly where machine behaviour diverges from human intent, which is precisely what auditing these systems requires. Our contributions are: (1) a reframing of classifier evaluation as construct-validity testing; (2) a lightweight, model-agnostic protocol that operationalises it; (3) a worked case showing that aggregate scores can mislead, with one high-scoring category that has no semantic basis and one low-scoring category that conflates two constructs; and (4) a reusable checklist for practitioners and auditors. Section 2 sets out the measurement-validity background, Section 3 describes the system and its taxonomy, Section 4 presents the protocol, Section 5 the findings, Section 6 the diagnosis-to-remedy mapping, and Sections 7 and 8 the checklist and discussion.

---

## 2. Background and related work

*All citations in this section are genuine, recognisable works but their exact details (year, venue, pages) are pending final verification; see `notes.md`.*

**2.1 Construct validity and the operationalism debate.** Measurement theory has long distinguished two views of what a construct is. On one pole, a construct is defined by its formal or statistical structure: a latent variable is whatever a fitting measurement model says it is. On the other, a construct exists in theory and the world first, and statistics only test a definition that domain experts must supply (Loevinger 1957). Borsboom and colleagues (Borsboom, Mellenbergh and van Heerden 2003; Borsboom 2005) argue that the purely statistical view is a form of operationalism: fitting a model does not establish that an attribute exists, and construct definition is an ontological question that model-fitting cannot settle. This distinction is the backbone of our argument: a classifier's score reports structure, but whether a category is a valid construct is a prior, substantive question the data cannot answer on its own.

**2.2 Reflective and formative constructs.** The reflective and formative distinction makes the stakes concrete (Bollen and Lennox 1991; Edwards and Bagozzi 2000; Howell, Breivik and Wilcox 2007; Bollen and Diamantopoulos 2017). A reflective construct causes its indicators, so internal consistency genuinely tests its structure; a formative construct is composed by its indicators (as socio-economic status is composed of income, education and occupation), so its boundaries are a definitional, expert choice that data alone cannot pin down. Several of our diagnoses are, in these terms, findings that a category behaves formatively or is mis-typed: a facet that does not cohere, or an umbrella that composes two constructs as one.

**2.3 Validity as argument.** Argument-based validity (Messick 1995; Kane 2013) sits between the poles: validity is a human interpretive argument built from substantive theory, whose weakest inferential links are then stress-tested empirically. Our protocol is an instance of this stance. The curators supply the construct; the protocol supplies the empirical stress test of whether the label captures it.

**2.4 Construct before indicators.** Adcock and Collier (2001) formalise the layering our paper relies on, separating the "systematized concept" (the expert-defined meaning) from the indicators and scores that operationalise it. The point of separating the layers is precisely that the mathematics cannot generate the concept; it can only operationalise one that experts have specified.

**2.5 Measurement validity in machine learning.** Jacobs and Wallach (2021) import the substantive critique into ML, arguing that fairness constructs are too often defined by their operationalisations rather than theorised first. The same de-facto operationalism pervades benchmark evaluation, where a leaderboard metric silently becomes the definition of a contested construct such as "reasoning" or "toxicity", and it surfaces as the jingle-jangle problem: distinct labels for one construct, or one label spanning several `[CITE: benchmark construct-validity critiques]`. We extend this line from critique to a runnable diagnostic applied to a deployed classifier.

**2.6 Adjacent strands.** Our work also draws on evaluation beyond aggregate accuracy and on per-class error analysis `[CITE]`; on human label variation, where annotator disagreement is treated as signal rather than noise (Plank 2022; `[CITE: perspectivism]`); on label-error auditing of benchmark datasets `[CITE: confident learning / label errors]`; on the text-as-data tradition in computational social science, which has long insisted that automated category assignment be validated rather than trusted (Grimmer and Stewart 2013; Grimmer, Roberts and Stewart 2022; Krippendorff on content analysis); and on the emerging use and brittleness of LLMs as classifiers and judges `[CITE: LLM-as-judge]`. Our contribution sits at their intersection: we operationalise the construct-validity critique as a lightweight, model-agnostic protocol that a practitioner or auditor can run on a deployed system.

---

## 3. The system and its categories as operationalisations

**The system.** Our case is an operational text classifier deployed to support an editorial content-curation workflow in the education sector. A small team of expert curators produces a weekly publication by triaging incoming articles into a fixed set of editorial sections. The classifier suggests a section for each incoming article, and is used as decision support rather than as an autonomous labeller. It was trained on roughly 1,400 articles that curators had historically assigned and, on a leakage-free held-out set of newly published material (n = 116), reaches a macro F1 of 0.725 (95% bootstrap CI [0.644, 0.796]) with a top-two accuracy of 0.88. By conventional standards it is a competent, deployed system, which is what makes it a useful object of study: the question is not whether it works, but what its per-category performance reveals.

**The taxonomy as operationalisation.** The six categories are not natural kinds. They are editorial sections defined by the curators for a human purpose, organising a publication, and were consolidated from around sixty-eight raw thematic variants into six working sections. In measurement terms, each section is an attempt to operationalise an underlying editorial construct. For exposition we use paraphrased category names that preserve each one's semantic character:

| Placeholder name | Character of the construct |
|---|---|
| Technology | a bounded, concrete topic |
| Workforce | a bounded, concrete topic |
| Region | a geographic facet that cuts across topics |
| Policy | an editorial theme |
| Political context | an editorial theme adjacent to Policy |
| General interest | a broad catch-all section |

The curators themselves treat some of these boundaries as fluid. In their working practice, articles are routinely re-filed between adjacent editorial sections, notably between Policy and Political context, which the curators identify as the hardest section to assign; in their own words an article "sometimes gets moved between" these two sections, and allocation can depend on which sections need items in a given week rather than on content alone. This is qualitative evidence, drawn from the curation workflow rather than a formal inter-annotator study, that the contested boundaries our protocol identifies are contested for the humans too, and not an artefact of the model. We use it as corroboration rather than a measured agreement statistic, and return to the value of formal inter-annotator measurement in Section 8.

**The model.** The deployed model is deliberately lightweight: frozen sentence-transformer embeddings feed a logistic-regression classifier, taking an article's title and a short description as input and emitting a single predicted section with its top alternatives. The architecture is not the contribution here; it is a representative, well-behaved classifier of the kind a practitioner would plausibly deploy, and the protocol we present is model-agnostic.

**Human in the loop.** The system is designed so that the model assists and the curator decides. For every article the curator sees the model's top two suggested sections and makes the final assignment, so a misclassification is caught rather than published. This matters for our argument: the curators, not the model, own the constructs the categories are meant to capture. The classifier's job is to recover those editorial constructs from text, and our evaluation asks how well the constructs themselves are recoverable, not merely how often the model reproduces the curators' labels.

**Anonymisation.** The organisation, the publication, the funder and the individuals involved are not identified. Category names are paraphrased for confidentiality; the paraphrases preserve each category's semantic type (concrete topic, cross-cutting facet, adjacent editorial theme, catch-all) so that the analyses in Sections 5 and 6 remain faithful to the original taxonomy.

---

## 4. Methods: a construct-validity protocol

**4.1 Data and evaluation setup.** The classifier was trained on roughly 1,400 articles that curators had historically assigned to the six sections, drawn from past issues of the publication and consolidated from around sixty-eight raw thematic variants into the six working sections, using an 85/15 stratified train and validation split. To estimate generalisation honestly we constructed a leakage-free held-out test set from issues published after the training cutoff (n = 116), so that no held-out item could have appeared in training or in model selection. We report macro F1 as the primary metric (given class imbalance), alongside per-class precision, recall and F1, and top-one and top-two accuracy. Because the held-out set is small, we report bootstrap confidence intervals rather than point estimates, and use McNemar's test for paired comparison between models. We also assessed calibration (expected calibration error), since the deployed system surfaces a confidence score.

**4.2 Confusion structure (discriminant evidence).** The first diagnostic reads the held-out confusion matrix as discriminant-validity evidence. We ask not only how large the error is but where it concentrates: whether a particular subset of categories systematically absorbs each other's instances. Concentrated, mutual confusion among a subset of categories signals that those categories may not be discriminable from one another, a construct-validity concern, whereas diffuse error spread across all categories would point instead to a model-capacity limit.

**4.3 Embedding separability (structural evidence).** The second diagnostic asks whether the categories correspond to distinct regions of representation space, independently of the model's decisions. We embed each article with a general-purpose sentence-transformer (`all-MiniLM-L6-v2`) and assess separability three ways: k-nearest-neighbour label purity (10 neighbours, cosine distance); silhouette scores under cosine distance; and unsupervised KMeans clustering (`n_clusters = 6`, set equal to the number of editorial categories so the comparison to the taxonomy is direct; `n_init = 10`, `random_state = 42`) compared against the editorial labels via the adjusted Rand index (ARI) and normalized mutual information (NMI). We compute silhouette both across all categories and for subsets (for example the concrete topics versus the adjacent editorial themes) to localise where separability breaks down. Low purity, near-zero silhouette, and low ARI and NMI for a category indicate that its construct is not structurally present in the data, independent of the classifier. Section 8 discusses robustness to the number of clusters and the choice of embedding model.

**4.4 Blind LLM cluster naming (construct recoverability).** The third diagnostic tests whether each construct is recoverable from the data without being told the taxonomy. We cluster the embeddings (`[confirm: clustering method and number of clusters used for blind naming, and which notebook/cell]`) and present each cluster's members to a large language model that has no knowledge of the original category scheme, asking it to name the theme it sees. If the cluster count is set above the number of editorial categories, the data can express finer-grained themes than the taxonomy imposes, which is what allows the procedure to reveal a single editorial category splitting into two coherent sub-themes. If the data-driven clusters recover the editorial categories, the constructs are latent in the text. If instead the model names different groupings, for example splitting one editorial category into two coherent themes, or finding no coherent theme for a category, that is direct evidence about the taxonomy rather than about the classifier. If the data-driven clusters recover the editorial categories, the constructs are latent in the text. If instead the model names different groupings, for example splitting one editorial category into two coherent themes, or finding no coherent theme for a category, that is direct evidence about the taxonomy rather than about the classifier.

**4.5 LLM control (construct versus capacity).** The final element separates a construct-validity failure from a model-capacity limit. We give a frontier LLM (Anthropic's Claude Sonnet, `[confirm exact version]`) the same taxonomy and a few-shot prompt (`[confirm: 2 examples per category]`), and have it classify the same held-out items (`max_tokens = 256`). The logic is a control: if a model with a different architecture and inductive bias, given the same category definitions, struggles on the same categories as the deployed model, the limit lies in the labels, not in the trained model's capacity. If instead the LLM markedly outperforms on those categories, the deployed model had headroom and the problem is at least partly a model problem. We report the LLM's macro F1 against the curators' labels alongside the deployed model's, and treat convergent failure on a category as evidence for a construct problem.

---

## 5. Findings: the protocol in action

On the held-out set the classifier reaches a macro F1 of 0.725 (top-two accuracy 0.88), a figure that, taken alone, reads as a uniformly competent system. The per-category breakdown tells a different story:

| Category | Held-out F1 | Character |
|---|---|---|
| Region | 0.90 | geographic facet |
| Workforce | 0.89 | concrete topic |
| Technology | 0.82 | concrete topic |
| General interest | 0.65 | catch-all |
| Policy | 0.59 | editorial theme |
| Political context | 0.50 | editorial theme |

Performance ranges from 0.90 to 0.50. The protocol shows these gaps are not all the same kind of thing: the high score reflects a category with no semantic basis, and the low scores reflect categories whose constructs the data does not support, not a model that needs more training. Category size does not predict performance: the best category (Region) is the smallest in the training data and the worst (Political context) is the largest, which already rules out "more data" as the remedy. `[confirm sizes: Region ~165, Political context ~315]`

**5.1 Region: a high score without a topical construct.** Region scores highest (F1 0.90), which under a score-led reading would mark it as the model's most reliable category. The structural diagnostic complicates this: Region has essentially no embedding cluster, with near-zero silhouette, and it does not emerge as a group under unsupervised clustering. The reconciliation is that Region is a geographic facet that cuts across all topics, detectable lexically (place and nation names) rather than as a content cluster. We are careful here: a cross-cutting facet is not an invalid construct, it is a legitimate one in a multi-faceted taxonomy. The narrower point is that Region is not a topical, mutually exclusive class, and its high F1 reflects a surface lexical cue rather than a learned topical construct. We adopt a simple working criterion: a category is a topic if its members form a content cluster in representation space, and a facet if it is orthogonal to that structure and cuts across topics. By this criterion Region is a facet. The remedy is therefore not to discard it but to represent it faithfully, as a facet (a metadata attribute or a parallel multi-label dimension) rather than forcing it into a single-label topical taxonomy where it competes with content categories it does not belong alongside.

**5.2 General interest: one label, two constructs.** General interest scores in the middle (F1 0.65), but its score is not the interesting fact about it. When the data-driven clusters are named without reference to the taxonomy, the items curators file under General interest do not form one theme; they split cleanly into two distinct sub-themes `[confirm: name the two sub-themes from NB13]`. General interest is a catch-all that operationalises two constructs as one. Its middling F1 is the symptom of an invalid operationalisation: the model is asked to produce a single label for what are really two things.

**5.3 The triangle: adjacent constructs that are not discriminable.** The three adjacent categories Policy, Political context and General interest account for roughly 24 of the held-out set's 41 errors `[confirm]`, and they fail together. The confusion structure shows they absorb each other's instances rather than scattering errors elsewhere (discriminant evidence). The structural diagnostic agrees: treated as a three-way problem these categories have a silhouette of 0.021, against 0.101 for the concrete categories, and unsupervised clustering recovers the editorial labels only weakly (ARI 0.21, NMI 0.27). Three independent diagnostics converge: these categories are not separable in the data. They are adjacent editorial themes that overlap by design, distinctions a human editor draws for presentational reasons that do not correspond to separable regions of meaning. This convergence of three model-side diagnostics is corroborated from the human side: the curators themselves re-file items between Policy and Political context (Section 3), so the boundary is contested for the experts, not only for the model. This is a construct problem, not a model error: no classifier trained on these labels can cleanly separate categories the data does not separate.

**5.4 The control: convergent failure locates the limit in the labels.** If the triangle's difficulty were a limitation of our specific model, a stronger model with a different inductive bias should do better. It does not. Given the same taxonomy and the same held-out items, a frontier LLM reaches a macro F1 of 0.634, below the deployed model's 0.725, and it fails on the same categories: on the editorial triangle it scores 0.39 against the deployed model's 0.58 `[confirm]`. The two models agree closely at the top-two level (both about 0.88), so both surface the right answer among their top guesses, but neither can make the single-label call the taxonomy demands. The failure is convergent: two models with different architectures, given the same category definitions, struggle on the same categories. By the protocol's logic this locates the limit in the labels, not in either model's capacity. We also note the LLM was markedly more brittle to measure, its score was sensitive to prompt format and output parsing, which is itself relevant to anyone proposing LLMs as drop-in evaluators.

---

## 6. From diagnosis to remedy

The protocol's value is not that it scores each category, but that it tells you what to do about a category, and the right action is frequently not "improve the model." Each diagnosis maps to a distinct, domain-neutral remedy:

| Diagnosis | Signal | Remedy |
|---|---|---|
| Facet, not a class | high score but no semantic cluster | re-implement as metadata, a filter, or a multi-label attribute, not a mutually exclusive class |
| Conflated constructs (umbrella) | low or middling score; data-driven clusters split it into coherent sub-themes | revise the label: split it into the constructs it conflates |
| Contested or overlapping construct | persistent mutual confusion across both models and the human-drawn boundary | retain human judgement, or allow multi-label assignment, rather than force a single label |
| Model-capacity limit | model weak on a category where a stronger model or LLM does markedly better | improve the model: features, data, architecture, or training |
| Label-definition limit | the model and an independent LLM struggle similarly on the same category | clarify the definition or change the taxonomy; more model effort will not help |

Applied to our case, the remedies are: Region should be re-implemented as a facet (a metadata attribute or a parallel multi-label dimension), not a topical class; General interest should be split into the two constructs it conflates; and the triangle (Policy, Political context, General interest), where the LLM control confirmed a label-definition limit rather than a capacity one, should be handled by retaining human judgement or allowing multi-label assignment, not by retraining. Notably, none of the case's hard categories were model-capacity limits.

This exposes why a score-led workflow gets it backwards. Such a workflow would trust Region (its highest score) and retrain the triangle (its lowest). Both moves are wrong. Region's high F1 is the least trustworthy result in the table, because the category has no topical construct and the model is merely reading surface cues. The triangle's low F1 is not a failure to engineer away but a faithful signal that the categories are not separable; a classifier that scored higher on it would either be overfitting noise or quietly resolving genuinely ambiguous cases in a way a human editor would contest. The goal of evaluation is fitness to the underlying objective, not a higher number.

---

## 7. A construct-validity checklist for practitioners and auditors

The protocol reduces to a short, lift-and-apply checklist. It is lightweight and model-agnostic: it needs only the model's predictions, a general-purpose embedding model, and access to an LLM. Before trusting a headline score, or retraining on a weak category, run these five checks.

> **A construct-validity check for a deployed classifier**
> 1. **Read the confusion structure, not just the score.** Where do errors concentrate? Do a subset of categories absorb each other's instances (discriminant evidence), or is error diffuse?
> 2. **Test separability independent of the model.** Embed the items and check k-NN purity, silhouette, and whether unsupervised clusters recover the categories (ARI, NMI). A category with no cluster has no structural construct, however well the model scores on it.
> 3. **Recover the constructs blind.** Cluster the data and have an LLM name the clusters without the taxonomy. Do the natural groupings match your categories, or split or merge them?
> 4. **Run a capacity control.** Give an independent model (an LLM) the same taxonomy and items. If it fails on the same categories, the limit is in the labels, not your model.
> 5. **Act on the diagnosis, not the score.** Map each result to its remedy: revise the label, re-implement the category, retain human judgement, or genuinely improve the model.

For an auditor, the questions this answers are: is each category a coherent construct, or a facet, an umbrella, or a contested boundary dressed as a class? Does its score reflect a learned construct or a surface cue? And would more data or a better model help, or is the ceiling in the labels? These are precisely the questions a single accuracy figure cannot answer, and they are the ones that determine whether a deployed classifier is measuring the right thing.

---

## 8. Discussion

**Societal significance.** As classification systems mediate more consequential decisions, in clinical coding, content moderation, benefits triage and education, the categories they enforce are operationalisations of contested human constructs, applied at scale. Single-score evaluation conceals where a system's behaviour diverges from the human objective its categories were meant to serve. Construct-validity evaluation makes that divergence visible, and therefore auditable, which is exactly what governance of these systems requires and what frameworks such as the EU AI Act gesture at without operationalising. The protocol is a concrete, runnable instrument for that audit.

**Generalisation: argued, not demonstrated.** We demonstrate the protocol on a single education-sector classifier. We argue the diagnostic logic is domain-general, because the protocol is model-agnostic and references nothing education-specific: any deployed classifier with an expert-defined taxonomy can be run through it. But this is one case, and we are explicit that transferability is argued, not shown across domains. The natural next step is to apply the protocol in a second, higher-stakes domain such as clinical or content-moderation taxonomies, where the cost of a category that scores well but measures the wrong thing is far greater.

**Limitations.** Beyond the single case: the production stream is unlabelled, so we evaluate against a held-out labelled set rather than live accuracy; the capacity control rests on a single LLM and prompt and was notably brittle to measure (its score moved with prompt format and output parsing), which is itself a caution for the LLM-as-judge literature; and blind cluster naming inherits the clustering's sensitivity to the number of clusters and the choice of embedding model. We did not measure formal inter-annotator agreement among the curators; our human-side evidence of contested boundaries is qualitative, drawn from the curation workflow, and a formal agreement study is a clear next step. We also do not empirically validate the proposed remedies end to end (for example by splitting General interest or re-implementing Region as metadata and re-measuring); the benefit is argued from the diagnoses rather than demonstrated. None of these undermine the core finding, which is corroborated by three independent diagnostics, but each bounds how far a single run should be trusted.

**Ethics and governance.** The framing keeps human authority over contested constructs central. The protocol does not tell domain experts what their categories should be; it tells them where their categories are not learnable, and returns the decision, revise, re-implement, or retain human judgement, to them. Model-expert disagreement is treated as information about the taxonomy, not as the model overruling the human. This is the right default for any setting where the categories encode professional or editorial judgement: the machine surfaces where the construct is weak, and the human decides what to do about it.

---

## 9. Conclusion  `[TO WRITE: short, after Section 8]`

Evaluate categories for construct validity, not just predictive performance; disagreement between model and expert is measurement evidence, not noise.

---

*Appendix: metrics detail (CIs, McNemar), anonymisation note, full hyperparameters. References: pending Section 2.*
