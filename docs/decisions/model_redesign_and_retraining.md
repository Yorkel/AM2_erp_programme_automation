# Model redesign & retraining — "if I were starting again"

A technical plan capturing what a better design would look like and how a v2 retrain should
go, grounded in evidence from the held-out test (NB11), SHAP (NB09), model comparison (NB08),
the Claude classifiers (NB06), and the embedding separability check (NB13).

This is an engineering plan, not the AM2 write-up. It records *what* and *why*; the first-person
reflection belongs in the portfolio.

---

## 0. The evidence we're reasoning from

| Source | Finding |
|---|---|
| NB11 held-out (issues 105–114, n≈116) | macro F1 **0.725** (skew-corrected; was 0.670 title-only) vs val 0.750; weighted 0.705 vs real-world 0.630; top-2 0.879; bootstrap CI [0.644, 0.796] |
| NB11 confusion matrix (skew-corrected) | clean: `four_nations` 0.90, `teacher_rrd` 0.89, `edtech` 0.82. Muddle: `what_matters_ed` 0.65, `policy_practice_research` 0.59, `political_environment_key_organisations` 0.50 |
| NB08 | already named the **"triangle"**: policy ↔ political ↔ what_matters; trained models struggle, Claude does better because the prompt gives boundary rules |
| NB09 SHAP | `policy_practice_research` is the most diffuse class in embedding space (no strong content signal); `teacher_rrd` the most localised |
| NB06 | Claude zero-shot and few-shot already implemented & evaluated on val (Claude ≈ 0.717, no training data) |

The held-out test **reproduced the triangle on unseen, post-cutoff data** — it is a robust,
content-level finding, not a quirk of the validation split.

---

## 1. BUG TO FIX FIRST — held-out eval has train/serve skew

**The model trains on `text_clean` = title + description** (NB04/05: `encode(train_df["text_clean"])`;
`s02b_scrape.py` builds `text` = "title + snippet … to match what the model was trained on").

**But `11_evaluation` encodes `test_df['title']` (title only)** with a comment that wrongly claims
"matches training." So the held-out **0.670 was measured on impoverished, title-only input the
model was never trained for** — the score is artificially depressed, and the depression should fall
hardest on exactly the editorial classes that need body text to disambiguate.

**Action:** in NB11, build `text_clean` for the held-out set the same way training did (title +
description) and re-encode. **DONE 2026-06-12:** re-run gives held-out macro F1 **0.725** (was 0.670
title-only), confirming the fix raised the number and the val→held-out gap is small (0.725 vs 0.750),
i.e. the model generalises and was barely overfit. **Quote 0.725 with its CI [0.644, 0.796], not
0.670.** This is itself a strong AM2 story (a skew bug caught by questioning a surprising number).

---

## 2. What I'd do differently — by leverage

### 2.1 Methodology (cheap, highest credibility)
- **Carve out a held-out test set before any tuning.** v1's 0.750 was measured on the val set that
  also drove 7+ design decisions (model switch, thresholds) — it was overfit-to. A locked test set
  from day one would have shown the honest number all along. Make held-out + bootstrap CIs +
  per-class-with-support the default, not a retrofit.
- **Inter-annotator agreement (IAA) study on the triangle.** If two humans only agree ~70% on
  policy vs political, then ~0.67 model F1 *is the human ceiling* — which reframes "underperformance"
  as "intrinsically fuzzy task." Best single piece of evaluative evidence we can add, and cheap.

### 2.2 Label taxonomy (where the real ceiling is)
The triangle is the dominant error source (≈24 of ~41 held-out errors). **Constraint:** the six
categories are **fixed by the curator** — they map to the newsletter's editorial sections, so they
are a stakeholder requirement, not a free engineering choice. "Merge the classes" is largely off the
table. The realistic levers all work *within* the fixed taxonomy:
- **Merge** the three editorial classes into one or two broader ones — *only if the curator agrees;*
  otherwise treat as constrained.
- **Hierarchical**: first split concrete vs editorial (the model is strong at this), then a second
  model only inside the editorial branch.
- **Multi-label**: an item genuinely can be both policy and political; single-label forces a
  coin-flip the data doesn't support.
- **Abstain option**: route low-confidence items to a human instead of guessing.
- **Annotation guideline** with explicit boundary rules + worked examples for the triangle —
  cheapest data-quality win; NB06 shows Claude improves precisely *because* it has such rules.

NB13 (embedding separability) tells us which of these is justified: if the triangle overlaps under
both MiniLM and a stronger MPNet embedder, the ceiling is the labels and no bigger model will fix it.

### 2.3 Input features — the snippet-not-full-article choice was correct
- **Title + description is already the input** (this was my earlier mistake — corrected).
- **More body text is low-value and risky here.** The model trained on title + short *curator
  description*; at inference there is no curator description, so `s02b_scrape.py` deliberately
  scrapes only an ~80-word snippet to match that short-text distribution. Scraping the *full* article
  would reintroduce skew the other way (train short, infer long). Using rich body text would require
  re-scraping full bodies for **all** 104 historical newsletters *and* changing inference to match —
  large effort, paywall losses, and only safe if both ends stay consistent. The practical input
  ceiling is title + description; leverage is in §2.2/§2.5, not more scraping.

### 2.4 Metadata — a deliberate choice, not an oversight
**The `no_meta` variant was chosen on purpose.** SHAP (NB09) showed the with-metadata model
classified by **source-type proxy** (proxy concentration 27.6%) instead of content. We traded
+1.5 val F1 (0.765 → 0.750) for a model that classifies by **content**, robust to new sources —
the right call for a pipeline that keeps adding sources. Any v2 that re-introduces metadata must
re-audit proxy concentration; don't silently undo this.

### 2.5 Architecture options (cheap → expensive)
- **Fine-tune the transformer end-to-end** — see §3.
- **Stronger / domain embedder** (e.g. MPNet) — only if NB13 shows it actually separates the triangle.
- **LLM few-shot (Claude) for the editorial cluster only** — see §4. Hybrid routing: cheap model for
  the easy concrete classes, LLM for the hard triangle. Plays to each tool's strength, cost-aware.

---

## 3. "Fine-tune the transformer end-to-end" — what it means

Today the model is **frozen**: the sentence-transformer (MiniLM) was trained by someone else on
general text; we never change its weights. We just take its fixed 384-dim output and train a small
LogReg on top. The transformer has **no idea** what "policy_practice_research" means in *our* sense
— it only knows generic sentence meaning, and LogReg has to separate our classes inside a space it
can't reshape.

**End-to-end fine-tuning** means unfreezing the transformer and continuing to train *its* weights on
our labelled newsletters, so the representation itself bends toward *our* category boundaries — it
can learn to push policy and political apart in a way the frozen model never could.

- **Upside:** can lift exactly the fuzzy classes a frozen embedder can't separate.
- **Risk:** ~1,400 labelled items is small for fine-tuning a full transformer → real overfitting
  risk; needs the held-out set (§2.1) to validate, and probably regularisation / small LR / early
  stopping. NB05 (`05_transformer.ipynb`, DistilBERT) is the starting point — it was considered
  (`distilbert_finetuned` is in the v1 alternatives) but not shipped.

---

## 4. "Can we test the LLM few-shot classifier?" — mostly already done

**Yes, and most of it exists.** `06_claude_api.ipynb` already implements and evaluates:
- zero-shot, few-shot, and few-shot+metadata Claude classifiers,
- on the val set, scoring **≈0.717 with no training data** — and NB08 shows Claude handles the
  triangle better because the prompt spells out the boundary ("emphasis on the research itself, not
  the organisation").

**What's missing for an apples-to-apples comparison:**
1. Run the NB06 few-shot classifier on the **held-out set (issues 105–114)**, same items as NB11,
   so we compare Claude vs the production model on identical unseen data.
2. Check current model IDs before quoting — NB06 currently pins `claude-sonnet-4-20250514`; confirm
   the latest Sonnet/Haiku ID and pricing via the claude-api reference before any cost claim.
3. Try the **hybrid**: production model for concrete classes (it's already strong + cheap), Claude
   only for items it routes into the triangle. Measure accuracy *and* cost per item.

This is the highest-value experiment to run next, because it directly tests the §2.2 hypothesis
(the triangle is a labels-and-rules problem, and an LLM with explicit rules is the right tool).

---

## 5. Priorities (small data, human-in-the-loop tool)

| # | Change | Why it's top | Cost |
|---|---|---|---|
| 0 | ~~Fix the NB11 title-only skew bug & re-run held-out~~ **DONE** | held-out corrected 0.670 → **0.725**; quote with CI | done |
| 1 | **Held-out test carved out first (as a standing practice)** | Methodology/credibility fix; honest numbers from day one | ~free |
| 2 | **IAA study on the triangle** | Proves whether 0.67 is the human ceiling — best evaluative evidence | low |
| 3 | **Mitigate the taxonomy** (multi-label / abstain / top-2 / LLM rules) *within* the curator's fixed 6 classes | Addresses the actual ceiling; categories can't simply be merged | low–med |
| 4 | **Run Claude few-shot on the held-out set + hybrid routing** | Right tool for small-data fuzzy classes; infra already in NB06 | med |
| 5 | **Fine-tune end-to-end (DistilBERT)** | Can reshape the space; but overfitting risk at n≈1,400 | med–high |
| — | ~~More body text in the input~~ | **Dropped** — snippet matches training by design; full body reintroduces skew + needs full re-scrape | n/a |

**One-line takeaway:** the model was never the main bottleneck — the **evaluation skew**, the
**label design**, and the **absence of a held-out test** were. v1's headline choices (no-meta,
content-driven) were sound and evidence-backed; v2's gains are in data/labels/eval, not raw model size.

---

## 6. Challenges, decisions & restrictions — reflection record

Structured for the portfolio (challenge → decision/constraint → impact → what I'd do differently).
These are analysis notes; the first-person STAR prose is written separately.

### 6.1 Evaluation skew — title-only vs title+description (a bug I caught)
- **Challenge:** the held-out macro-F1 came back at 0.670, below val 0.750. Questioning *why* led to
  the input, not the model.
- **Root cause:** `11_evaluation` encoded `df['title']` (title only) in all three parts (held-out,
  calibration, fairness), while the model was trained on `text_clean` = title + description.
- **Impact:** the 0.670 (and the recomputed val numbers in Parts B/C) were **under-estimates** —
  the model was judged on input it never saw. After the fix, held-out macro F1 = **0.725**; the
  classes that gained most were exactly the description-dependent ones (`teacher_rrd` 0.74→0.89,
  `policy_practice_research` 0.46→0.59), while `four_nations` was unchanged (0.90, lexical).
- **What I'd do differently:** **EDA the inputs before trusting the metric.** A surprising score is a
  signal to inspect what the pipeline feeds the model. Fixed and re-run 2026-06-12 (0.670 → 0.725).

### 6.2 Production skew — curator description vs scraped snippet (a design tension, not a bug)
- **Challenge:** real-world weighted F1 (0.63) sits below val (0.75).
- **Constraint:** training data carries clean, human-written **curator descriptions**; live articles
  have **none**, so `s02b_scrape.py` substitutes a crude ~80-word scraped snippet (first paragraphs,
  paywall → title fallback). The snippet is a **lossy proxy** for the description.
- **Decision made (sound):** cap inference text to a short snippet so it matches the *length* of the
  training descriptions — avoids train-short/infer-long skew. Correct given the training data.
- **Impact:** an inherent train/serve quality gap that partly explains the val→real-world drop.
- **What I'd do differently (primary reflection): train on the full article text, at both ends.**
  Train on scraped full bodies *and* serve on scraped full bodies — one consistent, content-rich
  input. This removes Skew 2 entirely (no description-vs-snippet mismatch) and gives the editorial
  classes the context they need to be separated. It is the change I'd make if starting again.
  - *Honest trade-offs:* needs re-scraping full bodies for all 104 historical newsletters (link rot +
    paywalls → incomplete coverage); full text is noisier (nav, related-articles, comments) so the
    extraction must be good; embeddings truncate long text (~256–512 tokens) so "full" really means
    "first few hundred tokens." Worth **testing**, not assuming — compare full-text vs current on the
    held-out set.
  - *Cheaper interim test:* train a variant on the ~80-word **snippet** (matching today's serving) vs
    the description-trained model. Description-vs-snippet was a default, never an experiment.

### 6.3 Label taxonomy — fixed by the curator (a restriction, not a free choice)
- **Challenge:** three editorial classes (`policy_practice_research`,
  `political_environment_key_organisations`, `what_matters_ed`) form a confusion "triangle"
  (≈24 of ~41 held-out errors); concrete classes (edtech, four_nations, teacher_rrd) are clean.
- **Restriction:** the six categories are the **curator's editorial sections** — non-negotiable.
  I could not simply merge the overlapping ones.
- **Impact:** there is a real performance ceiling set by the label design, which the model cannot
  cross because the boundary lives in the curator's editorial judgement, not the text.
- **What I'd do differently:** run the embedding-separability check (now NB13) **on day one** — not to
  redesign the taxonomy (couldn't), but to *know the ceiling early*, set stakeholder expectations, and
  choose mitigations that work within the fixed labels: top-2 surfacing, abstain/route-to-human,
  internal multi-label, and an LLM with explicit boundary rules (NB06 shows Claude does better on the
  triangle precisely because the prompt disambiguates).

### 6.4 No held-out test set until late (methodology gap)
- **Challenge:** the val set was used for the SHAP-driven model switch + 5+ other decisions, so 0.750
  could not be trusted as a generalisation estimate until a held-out set existed. (The held-out
  test since confirmed generalisation: 0.725 vs val 0.750, so the overfitting was in fact minor — but
  we could not have known that without building the held-out set.)
- **Impact:** the headline number quoted for months was optimistic; the true (skew-corrected) held-out
  number is the honest one.
- **What I'd do differently:** carve out a temporal held-out set **before any tuning** and make
  held-out + bootstrap CIs + per-class-with-support the default reporting, from the start.

### 6.5 Metadata removal — a deliberate, evidence-backed decision (recorded so it isn't undone)
- **Decision:** ship the `no_meta` variant. SHAP (NB09) showed the with-metadata model classified by
  **source-type proxy** (27.6% proxy concentration) rather than content.
- **Trade:** −1.5 val F1 (0.765 → 0.750) for content-based classification that is robust to new sources.
- **Impact:** the right call for a pipeline that keeps adding sources; McNemar (NB11 Part B) tests
  whether that 1.5pt gap is even significant (likely not).
- **Restriction for v2:** any re-introduction of metadata must re-audit proxy concentration first.

### 6.6 Other restrictions shaping the design
- **Small data** (~1,400 labelled items) → caps fine-tuning; favours frozen-embedder + LogReg and/or
  LLM few-shot.
- **Link rot / paywalls** → historical full-text backfill is incomplete and unreliable.
- **Free-tier infra** (Render 512MB, GitHub Actions cron) → batch sizes and scheduling constrained.
- **Human-in-the-loop by design** → top-2/top-3 accuracy matters more than top-1; the tool degrades
  far less than the raw macro-F1 implies (held-out top-2 = 0.879).

### 6.7 "What I'd do differently", in order
1. EDA the model inputs before trusting any metric (would have caught 6.1 immediately).
2. Carve out a held-out test set before tuning (6.4).
3. Run embedding-separability early to know the taxonomy ceiling (6.3).
4. Test description-vs-snippet training to address production skew (6.2).
5. Bring in an LLM with explicit boundary rules for the editorial triangle (NB06 → held-out).
