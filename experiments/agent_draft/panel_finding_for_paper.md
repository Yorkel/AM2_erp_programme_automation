# Cross-model section-assignment panel: a live construct-validity probe

**Status:** factual results note for the "Deciding What to Measure" construct-validity paper. Numbers from a 4-week trial on the ESRC ERP newsletter (June 2026). Small sample, illustrative not definitive.

## Setup
A three-voice "panel" assigns each candidate newsletter item to one of the editorial sections:
1. Claude Opus 4.8 (Anthropic),
2. GPT-4o (OpenAI),
3. the deployed classifier (frozen all-MiniLM-L6-v2 embeddings + logistic regression, trained on the curators' own labels).

Candidate pools are the real weekly inputs: manual form submissions plus dashboard-scraped items that survived curator rejection. Majority vote (>=2 agree) assigns; a three-way split is flagged for the curator.

## Finding 1 — model diversity exposes label under-determination
Same-model panel (one model, two prompt framings): **93%** agreement.
Cross-lab panel (Claude vs GPT-4o, identical task): **55%** agreement (16 of 29 items, issue #115).

Two independent frontier models from different labs agree on only ~55% of section assignments. The drop from 93% to 55% is the signal: the disagreement is about the **construct (the categories), not model noise**.

## Finding 2 — disagreements concentrate on the contested editorial boundaries
Cross-model disagreements are not uniform. They cluster on the overlapping editorial sections:
Political environment <-> Research-Practice-Policy, EdTech <-> What matters, EdTech <-> Political.
The concrete categories (Four Nations, Teacher recruitment, the PI update) are assigned consistently.

## Finding 3 — three-voice flags predict curator difficulty (issue #116)
The three items the panel flagged as three-way splits for issue #116 were exactly the three the curators treated as borderline, per the curator's own editing email:

| Panel flag (#116) | What the curator did |
|---|---|
| "Every child to get access to enriching activities" | kept, but filed under the contested Political section |
| "More than 500k pupils with EHCP" | cut from the issue |
| "Grammar schools are inclusive, says Ofsted" | held over to the next issue ("Keep") |

The machine's "I am not sure about these" landed on the humans' "where does this go / do we even run it".

## Finding 4 — panel/curator categorisation gaps fall on boundaries the curator herself moves
Scored against the published #116, the panel's majority section matched the curator on 8 of 17 reachable items. Every mismatch is a contested-boundary case, and several are items the curator explicitly **moved between sections** in her editing pass:
- National Literacy Trust reading survey -> moved to Political (panel: What matters)
- EEF generative-AI research -> moved to EdTech
- Six Camps of Metascience -> moved to Research-Practice-Policy
- ASCL Cymru ITE incentives -> Four Nations by the curator (panel: Teacher recruitment) — the nation-facet vs topic tension

So "categorisation error" is the wrong frame: the panel disagrees with the curator on precisely the items the curator treats as movable.

## Cross-week stability (4 weeks)
| Issue | Pool | Unanimous 3/3 | Majority 2/3 | 3-way flag |
|---|---|---|---|---|
| #113 | 96 | 29 | 53 | 14 |
| #114 | 45 | 19 | 25 | 1 |
| #115 | 29 | 12 | 16 | 1 |
| #116 | 34 | 9 | 22 | 3 |

Flags scale with pool noise (the pre-refresh #113 week, with a much broader scrape, produced more). For normal weeks the curator reviews 1–3 items.

## Stakeholder corroboration
The curator who lays up the issue, unprompted: "When there is a lot of input it takes time for me to work out what to include. So it really helps when you highlight priority items." The panel operationalises exactly this: auto-assign the clear majority, surface only the contested few.

## Caveats
- 4 weeks, ~30–96 items each; illustrative.
- Single curator as "truth"; the argument is precisely that this truth is one defensible operationalisation among several.
- The classifier has 6 classes (no PI/Programme), so it never votes that section.
