# Source ceiling per country

How many sources you can realistically have per jurisdiction, given current feasibility.

## No hard technical limit

Supabase scales fine. The only soft cap is the weekly GitHub Actions cron budget (currently 60 minutes). Going past ~30 sources/country starts to push that window — split into staggered crons if needed.

## Methodological limit is balance

Cross-jurisdictional comparison (paper 5b) wants similar source counts per country. The binding constraint is whichever country has the fewest available sources.

## Realistic ceiling per country

| Country | Current | + Probed WP (queued) | + Top research adds | Realistic max (no Playwright) | Hard limit (with Playwright) |
|---|---|---|---|---|---|
| England | 6 | +12 | +~8 | **~22** | ~28 (UK unions: NEU, NASUWT, NAHT, ASCL rescued) |
| Scotland | 5 | +2 | +~6 | **~12** | ~15 (Education Scotland, SQA, EIS rescued) |
| Wales | 0 | 0 | +~7 | **~7** | ~11 (Children's Commissioner Wales, Bevan Foundation rescued) |
| Northern Ireland | 0 | 0 | +~9 | **~9** | ~13 (CCEA, CCMS rescued) |
| Republic of Ireland | 7 | 0 | +~9 | **~13** | ~17 (NCCA, SEC, TUI rescued) |

## Binding constraint = Wales

Wales has the fewest open-access publishers. Without Playwright, you're capped at ~7-10 per country if you want jurisdiction-balanced comparison.

## Two options

1. **Balanced ~10/country** — Wales sets the ceiling. No Playwright dependency needed. Doable for end-of-July Stage 2.
2. **Unbalanced but maximal (~15-22/country)** — England + RoI deep, Wales/NI shallow. Defensible only if the imbalance is named explicitly in the methodology section. Weakens the cross-jurisdictional comparison.

Original scope ask was ~18/country. That's only reachable with Playwright on Welsh + NI blocked sources, which is gated behind user approval (new dependency, infra cost).

## Note on what counts as a "source"

- Multi-jurisdiction bodies (e.g. INTO covering irl + ni, NASUWT covering eng + wal + sco + ni) count once per `source` row but appear in the corpus tagged to each jurisdiction they serve.
- New source-categories (union, advocacy, parliament) trigger NMF retrain per `pipeline_decisions.md` §14 — factor that into Stage 2 timeline.

---

*Generated alongside [source_expansion_research.md](source_expansion_research.md) and [wp_backfill_status.md](wp_backfill_status.md). Nothing committed, nothing scraped.*
