# Paper: outstanding work

Companion to `manuscript.md`. Status of what is left.

## Sections
- **§2 Background** — NOT written. Needs the verified lit search (8 themes listed in the manuscript §2 stub). The one genuinely-new block. Also resolves the four `[CITE]` placeholders in §1.
- **§9 Conclusion** — NOT written. Short, write after §8 is final.
- **§1, §3, §4, §5, §6, §7, §8** — drafted (in manuscript).

## Values to confirm (from notebooks)
- Blind-naming cluster count: inferred `k = 10` (NB13) — confirm.
- Few-shot count: `2 examples per category` (NB14) — confirm.
- Exact Claude model id (NB14 shows both `claude-sonnet-4-6` and `claude-sonnet-4-20250514`) — state the one used.
- `max_tokens`: 256 vs 150 — confirm the reported run.
- The two sub-themes General interest splits into (NB13 blind naming).
- Triangle error count (24 of 41) and per-category LLM figures (triangle 0.39 vs 0.58) — confirm against NB14.
- Class sizes (Region ~165 smallest, Political context ~315 largest).

## Reviewer responses (paperreview.ai, accept-contingent)
Done (in manuscript): Region facet-vs-topic reframe; qualitative inter-curator disagreement; clustering hyperparameters stated.
Still to do:
- **Sensitivity analysis** over k, embedding model, clustering algorithm (UMAP+HDBSCAN). Medium effort, new NB13 runs. Highest-value robustness ask.
- **LLM control variance**: 2+ prompts and a second model, with error bars. New NB14 runs.
- **Rubric for blind LLM naming** + agreement across 2-3 LLMs/prompts.
- **Remedy ablation** (split General interest, multi-label triangle, Region as metadata, show gains). The big stretch; reviewer frames as "would be very strong", not required for acceptance.

## Draft-internal fixes (cross-check, 2026-06-14)
Note: `manuscript.md` already has the 3 fixes (Region reframe, hyperparameters, inter-curator). The docx uploaded to paperreview is the PRE-fix version, so some items below are docx-only.
1. `[CITE]` placeholders + §2 stub — OPEN (the lit search).
2. Duplicate §3 stub — N/A in manuscript.md (docx-only).
3. Leftover scaffold bullets — docx-only; §9 still to write.
4. **McNemar + ECE promised in §4.1 but not reported in §5** — OPEN. Decide: report ECE (~0.168, underconfident) in §5; tie McNemar to the model-vs-LLM comparison in §5.4 or drop it from §4.1. Do not fabricate a result.
5. Abstract vs §5.1 Region contradiction — RESOLVED (§5.1 reframed; abstract now says facet-not-topic).
6. Abstract "disagrees about as often" overstated the 9-pt gap — FIXED 2026-06-14 (now "does not outperform ... and fails on the same categories").
7. Few-shot count + exact Claude version — OPEN (in confirms above).
Verify: inter-curator re-filing — VERIFIED 2026-06-14 (`newsletter_curation_process_march2026.md:100`, `process_curators_follow.md:85-87`; direct Gemma quote; tightened to Policy↔Political context). k=10 blind-naming — still to verify.

## Cross-cutting
- **References** — fall out of §2.
- **Figures** — clean up confusion matrix (NB11) and embedding-separability plot (NB13) to publication quality.
- **Employer / funder sign-off** — GATING before posting the preprint.

## Venue / sequence
- arXiv (cs.CY + cs.LG) first → ACM FAccT.
- Sequence: clear permissions → arXiv → FAccT.
