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
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv


DEFAULT_MODEL = "claude-haiku-4-5"
DEFAULT_MAX_TOKENS = 200
DEFAULT_TEMPERATURE = 0.4   # slight variation but mostly deterministic
TRAIN_CSV = Path("data/modelling/train.csv")
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

You will be given example summaries from past issues to anchor on, then asked \
to summarise a new article. Match their style: descriptive, close to source, no commentary."""


def _load_few_shot_examples(n: int = N_FEW_SHOT_EXAMPLES, seed: int | None = None) -> list[dict]:
    """Pull N random examples from train.csv to use as few-shot anchors.

    Re-sampled per run by default so summaries don't drift to favouring one
    style. Pass a `seed` for reproducible prompts.
    """
    if not TRAIN_CSV.exists():
        raise RuntimeError(f"{TRAIN_CSV} not found — required for few-shot anchoring")

    df = pd.read_csv(TRAIN_CSV)
    df = df.dropna(subset=["text"])
    # Pick reasonably-long examples (avoid one-liners)
    df = df[df["text"].str.split().str.len() >= 20]
    if len(df) < n:
        raise RuntimeError(f"need at least {n} eligible rows in train.csv, got {len(df)}")

    rng = random.Random(seed) if seed is not None else random
    sampled = df.sample(n=n, random_state=rng.randint(0, 2**31))
    return [
        {
            "text": str(row["text"]).strip(),
            "category": str(row.get("target", "")),
        }
        for _, row in sampled.iterrows()
    ]


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
        f"Example {i+1} (category: {ex['category']}):\n{ex['text']}"
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
        from anthropic import Anthropic
        client = Anthropic()   # picks up ANTHROPIC_API_KEY from env

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
    return response.content[0].text.strip()


def summarise_batch(items: list[dict], *, model: str = DEFAULT_MODEL,
                    seed: int | None = None,
                    on_progress=None) -> list[dict]:
    """Summarise a batch of articles.

    `items` is a list of dicts with keys: url, title, text_clean (or text), category.
    Returns the same dicts with a `summary` key added.

    Reuses the same client + few-shot examples across the batch so prompt
    caching kicks in from the 2nd article onwards.
    """
    from anthropic import Anthropic
    client = Anthropic()
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
