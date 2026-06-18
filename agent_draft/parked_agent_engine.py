"""
Newsletter-assembly agent engine (used by dashboard/pages/assemble.py).

Wraps the proven trial logic from agent_draft/:
  - build a candidate pool for a week = manual Excel submissions + non-rejected
    dashboard (scraped) items,
  - a three-voice categorisation panel (Claude + GPT-4o + the deployed classifier);
    >=2 agree -> assign, 3-way split -> flag for the curator,
  - a house-style draft grouped by section.

Heavy work (API calls) runs on demand from the page, behind a spinner. No state
is written back to Supabase; the curator stays the decider.
"""
from __future__ import annotations
import os, re, io, json
from collections import Counter
from pathlib import Path

import pandas as pd

SECTIONS = [
    "Update from PI / Programme",
    "Teacher recruitment, retention & development",
    "EdTech",
    "Political environment and key organisations",
    "Four Nations",
    "Research – Practice – Policy",
    "What matters in education?",
]
# classifier (6 classes) -> display section
_CLF_MAP = {
    "edtech": "EdTech",
    "four_nations": "Four Nations",
    "policy_practice_research": "Research – Practice – Policy",
    "political_environment_key_organisations": "Political environment and key organisations",
    "teacher_rrd": "Teacher recruitment, retention & development",
    "what_matters_ed": "What matters in education?",
}


def _norm(t: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", " ".join(str(t).lower().split()))[:80]


def _ensure_keys() -> None:
    """Populate env from a local .env if the keys aren't already set (dev convenience)."""
    need = [k for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "SUPABASE_URL") if not os.environ.get(k)]
    if not need:
        return
    keys = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "SUPABASE_URL",
            "SUPABASE_SERVICE_KEY", "SUPABASE_ANON_KEY")
    # 1) local .env
    env = Path(__file__).resolve().parent.parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            for k in keys:
                if line.startswith(k) and not os.environ.get(k):
                    os.environ[k] = line.split("=", 1)[1].strip().strip('"').strip("'")
    # 2) Streamlit host secrets (Streamlit Cloud etc.)
    try:
        import streamlit as st
        for k in keys:
            if not os.environ.get(k) and k in st.secrets:
                os.environ[k] = str(st.secrets[k])
    except Exception:
        pass


def available() -> dict:
    """Which voices can run right now (so the page can warn rather than crash)."""
    _ensure_keys()
    return {
        "claude": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "gpt": bool(os.environ.get("OPENAI_API_KEY")),
        "supabase": bool(os.environ.get("SUPABASE_URL")),
    }


def build_pool(excel_bytes: bytes | None, win_a: str, win_b: str) -> list[dict]:
    """Merge non-rejected dashboard items + manual Excel submissions for the week."""
    _ensure_keys()
    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"],
                        os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_ANON_KEY"))
    dash = pd.DataFrame(sb.table("v_dashboard").select(
        "title,url,article_date,summary,top1,composite_score,source,text_clean").execute().data)
    dash["article_date"] = pd.to_datetime(dash["article_date"], errors="coerce")
    dash = dash[(dash["article_date"] >= win_a) & (dash["article_date"] <= win_b + " 23:59:59")]
    rejects = {r["url"] for r in sb.table("curator_decisions").select("url,action").eq("action", "reject").execute().data}
    dash = dash[~dash["url"].isin(rejects)]

    pool, seen = [], set()
    if excel_bytes:
        m = pd.read_excel(io.BytesIO(excel_bytes), sheet_name="Sheet1").dropna(how="all")
        m["Completion time"] = pd.to_datetime(m.get("Completion time"), errors="coerce")
        m = m[m["Title"].notna() & (m["Title"].astype(str).str.strip().str.lower() != "end")]
        m = m[(m["Completion time"] >= win_a) & (m["Completion time"] <= win_b + " 23:59:59")]
        for _, r in m.iterrows():
            k = _norm(r["Title"])
            if k in seen:
                continue
            seen.add(k)
            pool.append({"id": str(len(pool)), "origin": "manual", "title": str(r["Title"]),
                         "source": "" if pd.isna(r.get("Organisation")) else str(r["Organisation"]),
                         "description": "" if pd.isna(r.get("Short description")) else str(r["Short description"])[:280],
                         "url": "" if pd.isna(r.get("Link (website address / URL)")) else str(r["Link (website address / URL)"]),
                         "suggested": None if pd.isna(r.get("Which section of the newsletter is this for?")) else str(r["Which section of the newsletter is this for?"])})
    for _, r in dash.iterrows():
        k = _norm(r["title"])
        if k in seen:
            continue
        seen.add(k)
        pool.append({"id": str(len(pool)), "origin": "dashboard",
                     "title": str(r["title"]),
                     "source": "" if pd.isna(r["source"]) else str(r["source"]),
                     "description": ("" if pd.isna(r["summary"]) else str(r["summary"]))[:280],
                     "url": "" if pd.isna(r["url"]) else str(r["url"]),
                     "suggested": None if pd.isna(r["top1"]) else str(r["top1"]),
                     "_text": "" if pd.isna(r["text_clean"]) else str(r["text_clean"])})
    return pool


def fill_summaries(pool: list[dict]) -> int:
    """Generate a summary (in-house voice) for any pooled item missing one.
    Most items already have a summary, so this usually touches only a few.
    Returns how many were generated."""
    try:
        from src.inference.summarise import summarise_article
        from anthropic import Anthropic
    except Exception:
        return 0
    client = Anthropic(max_retries=3)
    made = 0
    for it in pool:
        desc = (it.get("description") or "").strip()
        if desc and desc.lower() != "summary unavailable":
            continue
        text = it.get("_text") or desc or it["title"]
        try:
            s = summarise_article(title=it["title"], text=text,
                                  category=it.get("suggested"), few_shot=[], client=client)
            if s and s.strip().lower() != "summary unavailable":
                it["description"] = s.strip()[:300]
                made += 1
        except Exception:
            continue
    return made


def _llm_sections(pool: list[dict]) -> tuple[dict, dict]:
    """Claude + GPT-4o each assign a section to every item."""
    task = (f"Assign each item to exactly ONE of these education-newsletter sections: {SECTIONS}.\n"
            f"Return ONLY a JSON array of objects with keys \"id\" and \"section\".\n"
            f"Items: {json.dumps([{'id': p['id'], 'title': p['title'], 'description': p['description']} for p in pool], ensure_ascii=False)}")

    def _parse(t):
        return {o["id"]: o["section"] for o in json.loads(re.search(r"\[.*\]", t, re.S).group(0))}

    import anthropic
    cla_resp = anthropic.Anthropic().messages.create(
        model="claude-opus-4-8", max_tokens=3000, messages=[{"role": "user", "content": task}])
    claude = _parse("".join(b.text for b in cla_resp.content if b.type == "text"))

    gpt = {}
    if os.environ.get("OPENAI_API_KEY"):
        from openai import OpenAI
        gpt = _parse(OpenAI().chat.completions.create(
            model="gpt-4o", messages=[{"role": "user", "content": task}]).choices[0].message.content)
    return claude, gpt


def _clf_sections(pool: list[dict]) -> dict:
    """Your deployed classifier votes a section for each item."""
    import joblib
    from sentence_transformers import SentenceTransformer
    root = Path(__file__).resolve().parent.parent
    st = SentenceTransformer("all-MiniLM-L6-v2")
    clf = joblib.load(root / "models" / "sbert_classifier_no_meta.joblib")
    texts = [(p["title"] + ". " + p["description"]).strip() for p in pool]
    preds = clf.predict(st.encode(texts, show_progress_bar=False))
    return {pool[i]["id"]: _CLF_MAP.get(preds[i], preds[i]) for i in range(len(pool))}


def run_panel(pool: list[dict]) -> list[dict]:
    """Panel vote. 3 voices where available (Claude + GPT-4o + classifier), else 2.
    >=2 agree -> assign; otherwise flag for the curator."""
    claude, gpt = _llm_sections(pool)
    try:
        clf = _clf_sections(pool)  # needs sentence-transformers + sklearn; absent on the slim dashboard
    except Exception:
        clf = {}
    out = []
    for p in pool:
        i = p["id"]
        votes = {"Claude": claude.get(i, "?")}
        if gpt:
            votes["GPT-4o"] = gpt.get(i, "?")
        if clf:
            votes["Classifier"] = clf.get(i, "?")
        cast = [v for v in votes.values() if v != "?"]
        tally = Counter(cast)
        top, n = tally.most_common(1)[0]
        agreed = n >= 2
        out.append({**p, "votes": votes,
                    "section": top if agreed else None,
                    "flag": not agreed,
                    "agreement": f"{n}/{len(cast)}"})
    return out


def generate_draft(items: list[dict]) -> str:
    """House-style draft of the given (curator-approved) items, grouped by section."""
    import anthropic
    payload = [{"section": it.get("section") or it["votes"]["Claude"], "title": it["title"],
                "source": it.get("source", ""), "description": it["description"]} for it in items]
    prompt = (f"Assemble the ESRC Education Research Programme newsletter from these items.\n"
              f"Group by section in this order: {SECTIONS}. Within each section keep the given items.\n"
              f"Format each item as **Source - Headline** then one or two factual sentences. "
              f"Do not reword beyond tightening. No em dashes. Return markdown only.\n"
              f"Items: {json.dumps(payload, ensure_ascii=False)}")
    r = anthropic.Anthropic().messages.create(
        model="claude-opus-4-8", max_tokens=4000, messages=[{"role": "user", "content": prompt}])
    return "".join(b.text for b in r.content if b.type == "text")
