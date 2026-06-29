"""
summarise.py
Generate 1-2 sentence editorial summaries of accepted newsletter articles
using Claude. Called by the dashboard when the curator clicks "Generate
Summary" on an accepted article (or in batch when assembling the draft).

NOT part of the cron pipeline — we only want to pay for summaries of articles
the curator has actually selected, not all 854/week.

Behaviour:
  - Reads 5 random anchor examples from data/modelling/train.csv to teach
    Claude the in-house editorial voice (few-shot, refreshed per run).
  - Calls Claude Haiku 4.5 with prompt caching: the system prompt + few-shot
    examples are cached, so each subsequent article costs ~$0.0003 instead
    of ~$0.0008.
  - Returns the generated summary as a plain string.
  - Has --dry-run mode that prints estimated cost without calling the API.

Cost reference (Haiku 4.5):
  Input $0.80 / output $4.00 per million tokens
  With caching: cached input is 90% off after the first call
  → ~$0.0003-$0.0008 per article = ~$0.04 per typical 50-item newsletter

Env:
  ANTHROPIC_API_KEY — required (already in .env)
"""

from __future__ import annotations

import argparse
import os
import random
import re
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv


DEFAULT_MODEL = "claude-haiku-4-5"
DEFAULT_MAX_TOKENS = 200
DEFAULT_TEMPERATURE = 0.4   # slight variation but mostly deterministic
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
# Few-shot anchor source: the cleaned newsletter archive, where `description`
# is the curator's editorial prose summary as published. NOT train.csv —
# that has article body text, which is the wrong style to anchor on.
# CSV is gitignored — only used when running locally. Streamlit Cloud falls
# back to BUNDLED_FEW_SHOT below.
FEW_SHOT_CSV = _PROJECT_ROOT / "data" / "interim" / "newsletters_cleaned.csv"

# Fixed bundle of curator-published summaries — drawn from newsletters_cleaned.csv
# (one or two per theme). Used as fallback when the CSV isn't available on
# Streamlit Cloud / GH Actions. Regenerate periodically as the curator's style
# evolves; ~10 examples is enough to anchor without bloating the prompt.
BUNDLED_FEW_SHOT: tuple[dict, ...] = (
    {"title": "Welsh government - Further support for teachers to boost roll out the new curriculum",
     "summary": "The Welsh government will introduce simplified, easy-to-access support to help schools plan their curriculum, deliver for learners and provide consistency across Wales. This will include updated processes, frameworks, toolkits and templates, and sharing of exemplars.",
     "category": "4 Nations"},
    {"title": "Belfast Telegraph - Third of children in NI have too few places to play, survey reveals",
     "summary": "Survey carried out by PlayBoard NI, the lead organisation for the development and promotion of play.",
     "category": "4 Nations & key organisations"},
    {"title": "Scottish Government - New approaches to help eradicate child poverty",
     "summary": "The Child Poverty Practice Accelerator Fund (CPAF) will provide grants towards local projects that test and evaluate new approaches which target at least one of the three drivers of child poverty reduction.",
     "category": "4 Nations & key organisations"},
    {"title": "Call for evidence on AI in schools",
     "summary": "Education secretary Gillian Keegan has launched a call for evidence on using artificial intelligence (AI) like ChatGPT in schools \"to get the best\" out of the new technology.",
     "category": "Calls for evidence"},
    {"title": "Ofqual and DfE studying 'feasibility' of 'fully digital' exams",
     "summary": "Some exam boards are already piloting on-screen assessment, but research by AQA last year found teachers' biggest barrier to digital exams was a lack of infrastructure.",
     "category": "DfE"},
    {"title": "Reject fewer teacher applicants, DfE tells trainers",
     "summary": "Susan Acland-Hood, the DfE's permanent secretary, told providers a 7 per cent jump in applicants this year had not led to an equivalent rise in offers for courses.",
     "category": "DfE"},
    {"title": "EEF blog: Bringing together policy, practice, and evidence",
     "summary": "Harry Madgwick, Research and Policy Manager at the EEF, explains how the Department for Education's recent 'Call for Evidence' is a promising example of bringing together the different 'worlds' of education.",
     "category": "EEF"},
    {"title": "Tech4Teachers White paper",
     "summary": "The digital poverty alliance have published suggestions on improving access and digital skills for teachers: challenges and opportunities.",
     "category": "EdTech"},
    {"title": "The Guardian - New UK bill could force social media firms to make content less addictive for under 16s",
     "summary": "The safer phones bill could ban companies from applying algorithms for young 'doomscrolling' teens.",
     "category": "EdTech"},
    {"title": "Education priorities in the next general election",
     "summary": "The Education Policy Institute, funded by the Nuffield Foundation, is providing a summary of the best evidence on current education challenges and effective policy interventions in order to assist political parties in drawing up their manifesto pledges on education.",
     "category": "Education, Policy & Practice"},
)
N_FEW_SHOT_EXAMPLES = 5
TEXT_TRUNCATE_WORDS = 500   # cap article content to avoid wasting tokens

# Pricing (USD per million tokens) — used by the dry-run cost estimate.
# Update these when Anthropic changes pricing.
PRICE_INPUT_USD_PER_M = 0.80
PRICE_OUTPUT_USD_PER_M = 4.00
PRICE_CACHED_INPUT_USD_PER_M = 0.08   # 90% off cached input


# ─── Prompt construction ─────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are writing 1-2 sentence summaries of articles for the ESRC \
Education Research Programme newsletter, a weekly bulletin sent to academics, \
policymakers, and education-sector practitioners in the UK.

The curators have a strict editorial principle: **summarise the article using \
its own language. Do NOT add framing, opinion, interpretation, policy context, \
or anything not stated in the article itself.**

Concrete rules:
- 1-2 sentences. Concise. Use the article's own phrasing wherever possible.
- Paraphrase or near-quote — do not interpret. If the article doesn't say \
"welcomes", don't say "welcomes". If it doesn't explain why, don't explain why.
- Do NOT add words like "could", "may", "is expected to" unless the article uses them.
- Do NOT add editorial verbs like "argues", "warns", "calls for", "highlights" \
unless they appear in the article.
- Lead with what the article literally states the news/finding/announcement is.
- UK English spelling. Use the article's own terminology.
- No headlines, no titles, no markdown, no quotation marks. Plain summary text only.

CRITICAL behavioural rules:
- NEVER write meta-text like "I'd be happy to help", "the article content \
appears to be incomplete", "could you share more", "I cannot provide…". \
No apology, no commentary, no request for more content.
- If the body text is missing or too sparse to faithfully summarise (e.g. you \
have only the title with no further substance), output EXACTLY this string \
and nothing else: Summary unavailable
- Do NOT hallucinate. Do NOT extrapolate. Do NOT invent facts, names, \
findings, or context that aren't in the supplied text. If you are tempted to \
write something the article doesn't actually say, write "Summary unavailable" \
instead.
- Output ONLY the summary text (or "Summary unavailable"). No preamble.

You will be given example summaries from past issues to anchor on, then asked \
to summarise a new article. Match their style: descriptive, close to source, no commentary."""


def _load_few_shot_examples(n: int = N_FEW_SHOT_EXAMPLES, seed: int | None = None) -> list[dict]:
    """Return N few-shot examples of curator-style summaries.

    Prefers the full CSV (gives stylistic variety per call) when available;
    falls back to BUNDLED_FEW_SHOT when the CSV is gitignored away — that's
    the Streamlit Cloud / GH Actions path.
    """
    if FEW_SHOT_CSV.exists():
        df = pd.read_csv(FEW_SHOT_CSV)
        df = df.dropna(subset=["title", "description"])
        df = df[df["description"].str.split().str.len() >= 10]
        if len(df) >= n:
            rng = random.Random(seed) if seed is not None else random
            sampled = df.sample(n=n, random_state=rng.randint(0, 2**31))
            return [
                {
                    "title": str(row["title"]).strip(),
                    "summary": str(row["description"]).strip(),
                    "category": str(row.get("theme", "")),
                }
                for _, row in sampled.iterrows()
            ]

    # Fallback — fixed bundle. Sampled deterministically so output is stable.
    rng = random.Random(seed) if seed is not None else random.Random(0)
    return rng.sample(list(BUNDLED_FEW_SHOT), min(n, len(BUNDLED_FEW_SHOT)))


def _build_user_prompt(title: str, body: str, category: str | None) -> str:
    """User-message portion: the article to summarise."""
    body_truncated = " ".join((body or "").split()[:TEXT_TRUNCATE_WORDS])
    parts = []
    if title:
        parts.append(f"Title: {title}")
    if category:
        parts.append(f"Newsletter category: {category}")
    if body_truncated:
        parts.append(f"Article content (first {TEXT_TRUNCATE_WORDS} words):\n{body_truncated}")
    parts.append(
        "\nWrite a 1-2 sentence editorial summary in the style of the examples above. "
        "Output ONLY the summary text — no preamble, no quotes, no markdown."
    )
    return "\n\n".join(parts)


def _build_messages(article_title: str, article_body: str, article_category: str | None,
                    few_shot: list[dict]) -> tuple[list[dict], list[dict]]:
    """Return (system_messages, user_messages) ready for client.messages.create.
    System portion is shaped for prompt-caching (single cached block)."""
    # The system block contains the instructions + the few-shot examples.
    # Marked cache_control so the second-onwards call within the 5-min window
    # gets the 90% input discount on this block.
    examples_text = "\n\n".join(
        f"Example {i+1} (category: {ex.get('category', '')}):\n"
        f"Article title: {ex['title']}\n"
        f"Curator summary: {ex['summary']}"
        for i, ex in enumerate(few_shot)
    )
    system = [
        {
            "type": "text",
            "text": SYSTEM_PROMPT + "\n\n--- Example summaries from past issues ---\n\n" + examples_text,
            "cache_control": {"type": "ephemeral"},
        }
    ]
    user = [
        {"role": "user", "content": _build_user_prompt(article_title, article_body, article_category)}
    ]
    return system, user


# ─── Summarisation entry points ──────────────────────────────────────────────

def summarise_article(*, title: str, text: str, category: str | None = None,
                      few_shot: list[dict] | None = None,
                      model: str = DEFAULT_MODEL,
                      client=None) -> str:
    """Generate one summary. Reuses `few_shot` and `client` across calls if
    passed (saves the train.csv reload + the SDK init)."""
    if client is None:
        from src.inference.anthropic_client import make_anthropic_client
        client = make_anthropic_client(5)   # IPv4-forced; picks up ANTHROPIC_API_KEY

    if few_shot is None:
        few_shot = _load_few_shot_examples()

    system, messages = _build_messages(title, text, category, few_shot)
    response = client.messages.create(
        model=model,
        max_tokens=DEFAULT_MAX_TOKENS,
        temperature=DEFAULT_TEMPERATURE,
        system=system,
        messages=messages,
    )
    result = response.content[0].text.strip()
    # Final-belts-and-braces guard: if Claude still returned an empty or
    # obviously meta-response despite the no-refusal system prompt, fall
    # back to a clean placeholder rather than leaking model meta-text into
    # the dashboard.
    if not result or _looks_like_refusal(result):
        return "Summary unavailable"
    return result


_TOPIC_SENTENCE_SYSTEM = (
    "You pick ONE sentence from a news/research article for an education "
    "newsletter — the sentence that best captures what the article is about "
    "(what happened / what the research shows).\n"
    "Rules:\n"
    "- Copy an existing sentence EXACTLY (verbatim). Do NOT write, paraphrase, "
    "shorten, or combine sentences.\n"
    "- It may be the opening sentence or a later one — whichever best conveys "
    "the point. Skip only pure navigation/boilerplate or datelines.\n"
    "- The sentence must stand on its own and be a real, full sentence.\n"
    "- If no single sentence does this well, reply with exactly: NONE\n"
    "- Output only the sentence (or NONE), nothing else."
)


def _normalise_for_match(s: str) -> str:
    """Lowercase + strip punctuation + collapse whitespace, for checking whether
    an extracted sentence really appears in the body (tolerates quote/spacing
    differences from HTML extraction)."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower())).strip()


def extract_topic_sentence(*, title: str, text: str,
                           model: str = DEFAULT_MODEL, client=None) -> str:
    """Best-effort extractive key sentence, copied VERBATIM from the article
    body. **Falls back to the article TITLE** when there's no real body, when
    the model can't find a genuine sentence, or when what it returns isn't
    actually in the text — so the curator never sees a fabricated line or a bare
    "Summary unavailable". Curator feedback (Gemma, 2026-06): prefer the
    article's own words; defer to the title when there's nothing to extract."""
    title_fallback = re.sub(r"\s+", " ", (title or "").strip()) or "Summary unavailable"
    body = (text or "").strip()
    if len(body) < 200:        # no real article body to quote — use the title
        return title_fallback
    if client is None:
        from src.inference.anthropic_client import make_anthropic_client
        client = make_anthropic_client(5)   # IPv4-forced; picks up ANTHROPIC_API_KEY

    user = (
        f"TITLE: {title}\n\nARTICLE:\n{body[:6000]}\n\n"
        "Return the single best sentence (verbatim), or NONE."
    )
    resp = client.messages.create(
        model=model,
        max_tokens=200,
        temperature=0,   # deterministic extraction
        system=_TOPIC_SENTENCE_SYSTEM,
        messages=[{"role": "user", "content": user}],
    )
    result = resp.content[0].text.strip()
    if not result or result.strip().upper() == "NONE" or _looks_like_refusal(result):
        return title_fallback
    # Verbatim guard: the sentence must actually appear in the body, else the
    # model paraphrased or invented it — fall back to the real title.
    if _normalise_for_match(result) not in _normalise_for_match(body):
        return title_fallback
    return result


def _looks_like_refusal(s: str) -> bool:
    """True if the model returned a meta/refusal response rather than a summary."""
    if not s:
        return True
    head = s.lower()[:80]
    return any(p in head for p in (
        "i cannot", "i can't", "i'd be happy", "i don't have", "i would need",
        "i am unable", "i'm unable", "could you provide", "could you share",
        "the article content", "the article appears", "please share",
        "please provide", "i appreciate the request",
    ))


# ─── Enrichment: geographic_focus + topic_tags ───────────────────────────────

_ENRICH_SYSTEM = """You tag UK education-newsletter articles. The newsletter covers \
UK schools, FE, and pre-HE education (NOT higher education).

For each article, return STRICT JSON with these two fields and no commentary:

- "geographic_focus": exactly one of "England", "Scotland", "Wales", \
"Northern Ireland", "UK-wide", "International".
- "topic_tags": list of EXACTLY 3 lowercase, hyphen-separated tags. Examples: \
"send", "teacher-pay", "ai-in-classrooms", "raac", "child-poverty", \
"ofsted-inspections", "school-funding", "mental-health", "exam-results". \
Pick tags that are specific enough to be filter-useful but standardised \
(reuse common tags rather than inventing new ones). Always return exactly 3.

Output ONLY the JSON object. No markdown fences, no preamble."""


def tag_article(*, title: str, text: str, model: str = DEFAULT_MODEL,
                client=None) -> dict:
    """Return {"geographic_focus": str, "topic_tags": list[str]} for one article.

    Separate from `summarise_article` so the curator-voice summary stays
    style-anchored on few-shot examples while tagging gets a tight structured
    prompt. Cheap — ~$0.0005 per call with prompt caching.

    On parse failure returns {"geographic_focus": "", "topic_tags": []} rather
    than raising — the scrape pipeline shouldn't break on a single bad article.
    """
    import json
    if client is None:
        from src.inference.anthropic_client import make_anthropic_client
        client = make_anthropic_client(5)

    body_truncated = " ".join((text or "").split()[:TEXT_TRUNCATE_WORDS])
    user_prompt = f"TITLE: {title}\n\nTEXT: {body_truncated}"

    try:
        resp = client.messages.create(
            model=model,
            max_tokens=200,
            temperature=0.0,  # determinism — same article → same tags
            system=[{
                "type": "text",
                "text": _ENRICH_SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = resp.content[0].text.strip()
        # Strip code fences if Claude added them despite the instruction
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        parsed = json.loads(raw)
        return {
            "geographic_focus": (parsed.get("geographic_focus") or "").strip(),
            "topic_tags": [
                t.strip().lower() for t in (parsed.get("topic_tags") or [])
                if isinstance(t, str) and t.strip()
            ][:3],
        }
    except Exception as e:
        import sys
        print(f"  tag_article failed: {type(e).__name__}: {e}", file=sys.stderr)
        return {"geographic_focus": "", "topic_tags": []}


def summarise_batch(items: list[dict], *, model: str = DEFAULT_MODEL,
                    seed: int | None = None,
                    on_progress=None) -> list[dict]:
    """Summarise a batch of articles.

    `items` is a list of dicts with keys: url, title, text_clean (or text), category.
    Returns the same dicts with a `summary` key added.

    Reuses the same client + few-shot examples across the batch so prompt
    caching kicks in from the 2nd article onwards.
    """
    from src.inference.anthropic_client import make_anthropic_client
    client = make_anthropic_client()
    few_shot = _load_few_shot_examples(seed=seed)

    out = []
    for i, item in enumerate(items, 1):
        title = item.get("title") or ""
        body = item.get("text_clean") or item.get("text") or ""
        category = item.get("category") or item.get("top1") or ""
        summary = summarise_article(
            title=title, text=body, category=category,
            few_shot=few_shot, model=model, client=client,
        )
        out.append({**item, "summary": summary})
        if on_progress:
            on_progress(i, len(items), item, summary)
    return out


# ─── Cost estimation ─────────────────────────────────────────────────────────

def estimate_cost(items: list[dict], model: str = DEFAULT_MODEL) -> dict:
    """Approximate input/output token counts and dollar cost for a batch.
    Uses word-count × 1.3 as a rough token estimate (overestimate is fine).
    """
    few_shot = _load_few_shot_examples()
    sys_text = SYSTEM_PROMPT + " ".join(ex["text"] for ex in few_shot)
    sys_tokens = int(len(sys_text.split()) * 1.3)

    per_article_input = 0
    per_article_output = DEFAULT_MAX_TOKENS  # upper bound, summaries usually shorter
    for item in items:
        body = item.get("text_clean") or item.get("text") or ""
        body_words = min(TEXT_TRUNCATE_WORDS, len(body.split()))
        title_words = len((item.get("title") or "").split())
        per_article_input += int((body_words + title_words + 50) * 1.3)  # +50 for prompt scaffolding

    # First call pays full input price for system; subsequent calls pay cached price
    n = max(len(items), 1)
    cached_input = sys_tokens * (n - 1)
    fresh_input = sys_tokens + per_article_input

    cost_fresh = fresh_input  / 1_000_000 * PRICE_INPUT_USD_PER_M
    cost_cached = cached_input / 1_000_000 * PRICE_CACHED_INPUT_USD_PER_M
    cost_output = per_article_output * n / 1_000_000 * PRICE_OUTPUT_USD_PER_M
    total = cost_fresh + cost_cached + cost_output

    return {
        "n_articles": n,
        "system_tokens": sys_tokens,
        "fresh_input_tokens": fresh_input,
        "cached_input_tokens": cached_input,
        "output_tokens_max": per_article_output * n,
        "cost_usd_max": round(total, 4),
        "cost_per_article_usd_max": round(total / n, 6),
        "model": model,
    }


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main() -> int:
    """Standalone CLI mode. Reads a CSV of accepted articles and writes summaries
    to a new CSV. NOT part of the cron pipeline — invoked by the dashboard or
    manually for testing.

    Usage:
      python -m src.inference.summarise --input <csv> --dry-run
      python -m src.inference.summarise --input <csv> --output <csv>
    """
    load_dotenv()

    parser = argparse.ArgumentParser(description="LLM summarise accepted newsletter articles.")
    parser.add_argument("--input", type=Path, required=True,
                        help="CSV of accepted articles (must have title + text_clean cols)")
    parser.add_argument("--output", type=Path,
                        help="Where to write the summaries (CSV). Default: <input>.summarised.csv")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--seed", type=int, default=None,
                        help="Seed for few-shot example sampling (reproducibility)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Estimate cost without calling Claude. Print and exit.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only summarise the first N rows (testing)")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"  ERROR: {args.input} not found")
        return 1

    df = pd.read_csv(args.input)
    if args.limit:
        df = df.head(args.limit)
    items = df.to_dict(orient="records")
    print(f"  Loaded {len(items)} accepted articles from {args.input}")

    est = estimate_cost(items, model=args.model)
    print(f"\n  Estimated cost ({args.model}):")
    for k, v in est.items():
        print(f"    {k}: {v}")

    if args.dry_run:
        print(f"\n  --dry-run: not calling the API. Done.")
        return 0

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("  ERROR: ANTHROPIC_API_KEY not set in .env")
        return 1

    def _progress(i, n, item, summary):
        title = (item.get("title") or "")[:60]
        print(f"  [{i}/{n}] {title}")
        print(f"           → {summary[:120]}{'…' if len(summary) > 120 else ''}")

    out_items = summarise_batch(items, model=args.model, seed=args.seed, on_progress=_progress)

    output = args.output or args.input.with_suffix(".summarised.csv")
    pd.DataFrame(out_items).to_csv(output, index=False)
    print(f"\n  Wrote {len(out_items)} summaries → {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
