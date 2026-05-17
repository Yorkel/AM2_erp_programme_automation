"""
Data loading and Supabase persistence helpers for the curator dashboard.

Replaces the old CSV / local-JSON model. Reads articles + predictions from the
Supabase `v_dashboard` view (joins articles + classify_newsletter on URL).
Writes curator decisions and summaries to the `curator_decisions` table.

The only session-state we still own here is the curator-added rows
(`st.session_state.curator_articles`) and the in-page UI category overrides
(`st.session_state.category_overrides`) — those are managed in their page
modules, not here.
"""

from __future__ import annotations

import os

import streamlit as st
import pandas as pd
from supabase import create_client


# ── Client ────────────────────────────────────────────────────────────────────

@st.cache_resource
def get_client():
    """Single cached Supabase client per Streamlit process."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_ANON_KEY (or SERVICE_KEY) must be set"
        )
    return create_client(url, key)


# ── Reads ────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_classified_articles(min_week: int | None = None) -> pd.DataFrame:
    """Pull article + prediction rows from the `v_dashboard` view.

    `min_week` lets a page narrow to recent weeks; pass None to fetch all.
    """
    client = get_client()
    q = client.table("v_dashboard").select("*")
    if min_week is not None:
        q = q.gte("week_number", min_week)
    resp = q.execute()
    df = pd.DataFrame(resp.data or [])
    if df.empty:
        return df
    # Ensure week_number is integer (Supabase may return as int or float depending)
    if "week_number" in df.columns:
        df["week_number"] = pd.to_numeric(df["week_number"], errors="coerce").astype("Int64")
    return df


@st.cache_data(ttl=60)
def load_decisions() -> dict[str, dict]:
    """Return {url: {action, label, summary, summary_generated_at, decided_at, notes}}.

    Fresher cache than articles (60s) so accept/reject updates show quickly.
    """
    client = get_client()
    resp = client.table("curator_decisions").select("*").execute()
    return {row["url"]: row for row in (resp.data or [])}


# ── Writes ───────────────────────────────────────────────────────────────────

def record_decision(url: str, action: str, label: str) -> None:
    """Upsert a curator decision on the given URL.

    `action` ∈ {accept_top1, accept_top2, manual, reject}.
    Invalidates the decisions cache so the next render picks it up.
    """
    client = get_client()
    client.table("curator_decisions").upsert(
        {
            "url": url,
            "action": action,
            "label": label,
            "decided_at": "now()",
        },
        on_conflict="url",
    ).execute()
    load_decisions.clear()


def record_summary(url: str, summary: str) -> None:
    """Persist a generated LLM summary onto the existing curator_decisions row.

    Same row as the decision (on_conflict=url). If the row doesn't exist yet
    (i.e. summary generated before accept — unusual), the upsert creates it
    with action/label NULL — but typically `record_decision` runs first.
    """
    client = get_client()
    client.table("curator_decisions").upsert(
        {
            "url": url,
            "summary": summary,
            "summary_generated_at": "now()",
        },
        on_conflict="url",
    ).execute()
    load_decisions.clear()


# ── Helpers used by pages ─────────────────────────────────────────────────────

def init_session_state() -> None:
    """Lazy-initialise the UI-only state the pages depend on.

    Decisions and summaries no longer live in session_state — they're in
    Supabase. Only purely-UI ephemeral state remains here.
    """
    if "curator_articles" not in st.session_state:
        st.session_state.curator_articles = []
    if "category_overrides" not in st.session_state:
        st.session_state.category_overrides = {}
    if "newsletter_picks" not in st.session_state:
        st.session_state.newsletter_picks = set()
    if "draft_descriptions" not in st.session_state:
        st.session_state.draft_descriptions = {}


def get_accepted_articles(df: pd.DataFrame) -> list[dict]:
    """Join `v_dashboard` rows with current curator_decisions; return non-rejected.

    Used by the Organise and Draft pages. Curator-added rows (session-only for
    now) are appended on top.
    """
    decisions = load_decisions()
    accepted: list[dict] = []

    for url, dec in decisions.items():
        if dec.get("action") == "reject":
            continue
        if not dec.get("action"):
            # row exists with only a summary — no decision yet; skip
            continue
        match = df[df["url"] == url] if not df.empty else pd.DataFrame()
        row = match.iloc[0].to_dict() if len(match) else {"url": url, "title": "Unknown"}
        row["curator_label"] = dec.get("label") or row.get("top1")
        if url in st.session_state.get("category_overrides", {}):
            row["curator_label"] = st.session_state.category_overrides[url]
        # Carry the summary along for the Draft page
        row["summary"] = dec.get("summary")
        accepted.append(row)

    for art in st.session_state.get("curator_articles", []):
        art_copy = dict(art)
        art_copy["curator_label"] = art.get("top1")
        art_copy["curator_added"] = True
        if art.get("url") in st.session_state.get("category_overrides", {}):
            art_copy["curator_label"] = st.session_state.category_overrides[art["url"]]
        accepted.append(art_copy)

    return accepted
