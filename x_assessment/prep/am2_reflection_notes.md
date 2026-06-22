# AM2 reflection notes — distinction angles (raw material)

Running capture of first-person reflection **angles + evidence** for the
professional discussion. This is raw material for Louise to write the STAR notes
from, **not** drafted prose. Cross-references to memory notes where the angle is
already recorded.

---

## Automation vs the manual process — partial adoption
**Criteria:** K30 / S33 / S34 (integrate AI into processes), S27 (stakeholder
strategy), Distinction S9/K14 + "what I'd do differently".

**What the automation does:** item selection, categorisation into the 6
newsletter sections, extractive topic sentence, abstractive summary, and an Excel
export. **Residual human work:** editorial judgement (e.g. Gemma cutting "too much
DfE self-promotion"), ordering within a section, PI updates, gap-filling,
proofing, and final formatting into the mailing template.

**The tension (the honest reflection):** adoption is *partial*. The automation was
bolted onto the existing manual workflow (Emma W emails + manual XLS curation +
Nina's Tuesday layout) as a **feeder**, rather than the production process being
redesigned around the automation. The optimised "engine" is being used to turn a
manual hand-crank.

**Sharpest concrete evidence — the template → Excel reversal:** the dashboard
originally produced a newsletter-style **template** (the more-automated,
closer-to-finished output). At Gemma's request this was changed to an **Excel
export matching the MS Form exactly** so it cut-and-pastes into the existing
manual flow. The more-automated output was *deliberately downgraded* to fit the
legacy manual step. (Logged in `deployment_challenges.md`, "Excel = exact MS-Form
format".)

**Adoption-curve evidence (value recognised even within partial adoption):** for
issue #115 Gemma used **two dashboard items as late PEKO replacements** and said
the dashboard is *"picking up stuff that Emma W doesn't see"*. (Logged in
`deployment_challenges.md`, 2026-06-09 thread.)

**Suggested angle for the write-up:** "I optimised for the curators' trust and
workflow continuity over end-to-end efficiency. With no constraint I'd redesign
the production process *around* the automation — auto-generating the laid-up draft
— rather than feeding a manual layout/curation step. The trade-off was deliberate:
partial adoption that earns trust incrementally, evidenced by curators
increasingly relying on items the manual route misses." Note this is the *same
theme* as the taxonomy and "Story B" reflections below — automation/optimality vs
stakeholder constraint.

**Professional handling note (for me, Louise):** the frustration is valid and
belongs *here*, not in a team email. The constructive move with the team is a
sincere offer to extend the automation (re-produce the laid-up draft), which makes
the "this can be automated" point as help rather than a dig. Avoid framing that
targets Nina's layout role.

---

## Scope drift from the March 2026 consultation
**Criteria:** K30/S33/S34, S27, K19/S12/B5, Distinction S9/K14.

**Documented baseline.** In March 2026 Louise ran a structured requirements
consultation with Gemma and Nina, mapping the full manual workflow end to end
(monitoring, filtering, section assignment, dedup, descriptions, send) and what
should stay manual (PI updates, editorial judgement, sign-off). Saved as
`docs/newsletter_curation_process_march2026.md`. The brief was explicit: **speed
up curation, reduce the ~7.5 hrs/week, NOT full automation.**

**Scope drift.** The deployed system has drifted from that agreed scope: instead
of reducing the weekly time pressure, the automation has been bolted onto the
manual process as a feeder, adding back-and-forth (version passing, the
template→Excel downgrade) rather than removing it. The intentionally-manual parts
(editorial judgement, sign-off) were always agreed and are fine; the drift is that
the *mechanical* assembly/layout the tool was built to absorb has stayed manual
too.

**Evidence the consultation supports Louise's position:** she delivered to the
agreed scope; the drift is in how the tool is being *used*, not in what was built.
Gemma's March note ("I'd always want to maintain control over what gets
published") confirms the manual editorial boundary was agreed up front, so the
realignment ask is narrow and well-founded, not a demand to automate everything.

**Also strong requirements-gathering evidence (K30/S33/S34, S27):** the March
consultation itself (structured Q&A, time-cost quantified at ~7.5 hrs, source/slant
nuance captured) is good P1-brief material independent of the scope-drift point.
Gemma's "single summary sentence from the text, don't write it in our own words"
directly seeded the later extractive topic-sentence feature.

## Live operation — fragile dependencies + silent failure (2026-06-16 + 2026-06-22)
**Criteria:** K11/S22/S24 (deploy + monitor), S32 (operate in production),
Distinction "what I'd do differently" + resilience/operational judgement.
**Full write-ups:** [incident_2026_06_16_pipeline_failure.md](../../docs/decisions/incident_2026_06_16_pipeline_failure.md),
[incident_2026_06_22_classifier_cold_start.md](../../docs/decisions/incident_2026_06_22_classifier_cold_start.md).

- **Two incidents, one week, same theme:** both were transient *infrastructure*
  faults, not application logic — 06-16 the GitHub runner could not reach Claude;
  06-22 the runner could not reach the HuggingFace classifier Space (free-tier
  cold-start, 60s probe timed out 3x at 04:54; the Space answered in 0.6s hours
  later). The pattern is **fragile free-tier dependencies + silent failure +
  no proactive monitoring**.
- **The honest gap (strong "differently" material):** after 06-16 I (a) fixed the
  NaN symptom with a shared `clean_text` guard but **missed one call site** (the
  Draft text-box seed), which is the exact line that crashed on 06-22, and (b) did
  not add any monitoring — so the second failure was found by a *curator*, not by
  me. Operational lesson: alerting + self-healing matter as much as model quality.
- **Recovery evidence (no data loss):** ran the summary sweep from the dev
  container (84 summaries / 57 tags / 57 topic sentences, 0 failures); 174 curator
  decisions including 65 made that morning were untouched, because curator state
  (`curator_decisions`) and enrichment (`articles`) are separate tables.
- **Concrete prevention proposed:** raise HF probe tolerance + pre-warm the Space;
  make the `continue-on-error` summary sweep loud; daily health-check that
  self-heals before curators see it; dashboard status banner instead of a stack
  trace.

## Cross-references (already in memory)
- **Taxonomy overlap insight** — the weakest classes (policy_practice_research ↔
  political_environment) reflect the newsletter's own overlapping editorial
  categories, not a model failure: "uncertain where a human would also be
  uncertain." (memory: project-state-2026-06-09)
- **Two "differently" stories** — (A) refine THIS classifier (multi-label, merge
  confused classes, annotation guideline, calibrate); (B) build a newsletter from
  scratch with no constraint (taxonomy derived from data, multi-label native,
  reserve a held-out test set on day one). (memory: project-state-2026-06-09)
