# AM2 reflection questions

Prep for the ~90-minute open-book discussion (15–20 questions). Answer in **STAR, first person, active
voice, past tense** ("I developed…"). Each question has an evidence pointer (doc / notebook) so you can
rehearse with the receipts to hand.

## Evaluation & critical thinking
1. How did you know your model was actually good, and what did you *not* know until you built the held-out
   test? — `evaluation_findings.md` (held-out 0.725 vs val 0.750); NB11.
2. Walk through the train/serve skew bug — how you caught it and what it changed (0.670 → 0.725). —
   `evaluation_findings.md` skew section; `project_eval_skew_2026_06_12` memory.
3. Why report bootstrap CIs and McNemar rather than a single F1? What did McNemar let you conclude? —
   `evaluation_findings.md` (CI [0.644, 0.796]; McNemar p=0.79 → no-meta tie); NB11 Part B.

## The taxonomy / the core finding
4. Why is the editorial "triangle" hard, and how did you prove it's a *label* problem not a *model*
   problem (three methods)? — `embeddings_and_llm_post_model.md` §1; NB11 confusion matrix + NB13.
5. Why does four_nations score best yet have no content cluster? What does that say about the taxonomy? —
   `embeddings_and_llm_post_model.md` §2 (geographic cross-cut / facet); NB13.
6. You found `what_matters_ed` is really two themes — what would you do, given the curator owns the
   labels? — `embeddings_and_llm_post_model.md` §3 (umbrella; blind LLM naming).

## Model choices & trade-offs
7. Justify shipping the *lower*-F1 no-meta model. What did SHAP show, and what did McNemar add? —
   `model_redesign_and_retraining.md` §2.4; NB09 SHAP (27.6% proxy); NB11 McNemar.
8. Trained model vs LLM — when is each right? What did NB14 actually show, including the reliability
   issues? — `embeddings_and_llm_post_model.md` §5 / §5a; NB14 (Claude 0.634 vs prod 0.725; brittleness).
9. Why title + description and not full article text? — `model_redesign_and_retraining.md` §2.3 / §6.2
   (curator-description vs scraped-snippet skew).

## Monitoring, drift & decisions
10. Distinguish data, concept and model drift — which can you even measure without labels, and how? —
    `monitoring_redesign_2026_06_11.md` drift-synthesis (§9).
11. How did you separate *composition* drift (new sources) from genuine drift? — same doc, the cohort
    trick; the "75% → 27% decisive" crux.
12. What would trigger a retrain, and why is the current answer "no"? — same doc, §12 retrain-trigger
    (98/500 decisions, 3.7/4 weeks, conf 0.445).

## Bias, fairness & ethics
13. Name the three *different* kinds of bias here and which one you actually fixed. —
    `monitoring_redesign_2026_06_11.md` "Bias & fairness" (algorithmic / representation / label-design).
14. The model mirrors a corpus that's 40% Schools Week and ~0% Wales — is that the model's problem?
    What's the mitigation? — same doc (representation bias → curation + source-roster review).

## Stakeholders & collaboration
15. The categories overlap and you couldn't change them — how did you engineer *around* a fixed
    stakeholder taxonomy? — `embeddings_and_llm_post_model.md` §4 (decouple internal/external; top-2;
    human-in-loop).
16. Give an example of curator feedback that changed the system. — curator-feedback memories (Gemma:
    Four Nations, category-on-Draft, triage bug); Four Nations fix end-to-end.

## Engineering & CPD
17. What in your architecture makes this reproducible and rollback-able? — `model_loader.py` +
    `models/runs/active.txt` + `MODEL_LIFECYCLE.md`; staged pipeline.
18. What would you do differently if starting again? — `model_redesign_and_retraining.md` §6.7
    (EDA the inputs first; held-out from day one; run-and-interpret rather than trust a number).
19. What surprised you most, and how did you respond? — the skew bug; LLM brittleness (NB14 artefacts);
    class-size ≠ performance (`embeddings_and_llm_post_model.md` §1).

---
Related: `evaluation_findings.md`, `embeddings_and_llm_post_model.md`, `monitoring_redesign_2026_06_11.md`,
`model_redesign_and_retraining.md`, `am2_writeup_plan.md`, `am2_portfolio_tracker.md`.
