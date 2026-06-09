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


# ── Null-safe text cleaning ──────────────────────────────────────────────────
def clean_text(v):
    """Coerce a possibly-null value to a clean display string.

    pandas NaN is a *truthy* float, so the usual `x or ''` guard lets it slip
    through and renders the literal string 'nan' in the UI / Excel. This is the
    single shared cleaner for the whole dashboard (Triage, Categorise, Draft,
    export). Returns '' for None / NaN / NaT / the strings 'nan'/'none'/'nat'.
    Lists/tuples (e.g. topic_tags) are returned unchanged so callers can iterate.
    """
    if isinstance(v, (list, tuple)):
        return v
    if v is None:
        return ""
    if isinstance(v, float) and pd.isna(v):
        return ""
    s = str(v).strip()
    return "" if s.lower() in {"nan", "none", "nat"} else s


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

@st.cache_data(ttl=60)
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


# ── Weekly reset (archive + week boundary) ────────────────────────────────────
@st.cache_data(ttl=60)
def get_week_boundary() -> str | None:
    """ISO timestamp of the most recent 'Start a new week' reset, or None if
    never reset. Decisions made before this are archived and hidden from the
    Categorise + Draft pages (see get_kept_articles / get_accepted_articles)."""
    client = get_client()
    try:
        resp = (
            client.table("curator_resets")
            .select("reset_at").order("reset_at", desc=True).limit(1).execute()
        )
    except Exception:
        # Table not created yet (migration 015 not run) — treat as "no boundary
        # set" so Categorise/Draft show everything instead of crashing. Once the
        # migration is applied this path stops being hit.
        return None
    rows = resp.data or []
    return rows[0]["reset_at"] if rows else None


def _before_boundary(decided_at, boundary) -> bool:
    """True if a decision's decided_at falls strictly before the week boundary
    (so it belongs to a previous, archived week). Parses both to UTC datetimes
    rather than comparing ISO strings, which is fragile across tz/microsecond
    formatting. A row with no parseable decided_at is treated as current."""
    if not boundary:
        return False
    b = pd.to_datetime(boundary, utc=True, errors="coerce")
    d = pd.to_datetime(decided_at, utc=True, errors="coerce")
    return bool(pd.notna(b) and pd.notna(d) and d < b)


def archive_and_reset_week(week_label: str) -> dict:
    """Snapshot this week's curator decisions into curator_decisions_archive,
    then record a new week boundary. NON-DESTRUCTIVE: curator_decisions is left
    intact, so kept/rejected articles keep their status (they won't reappear in
    Review) and pending articles are untouched. The new boundary just hides this
    week's work from Categorise + Draft. Returns {'archived': n}."""
    client = get_client()
    boundary = get_week_boundary()
    q = client.table("curator_decisions").select("*")
    if boundary:
        q = q.gte("decided_at", boundary)
    rows = q.execute().data or []
    if rows:
        client.table("curator_decisions_archive").insert(
            [{"week_label": week_label, "url": r.get("url"), "decision": r} for r in rows]
        ).execute()
    client.table("curator_resets").insert(
        {"week_label": week_label, "n_archived": len(rows)}
    ).execute()
    # Bust caches so the pages reflect the new boundary immediately.
    load_decisions.clear()
    get_week_boundary.clear()
    return {"archived": len(rows)}


# ── Writes ───────────────────────────────────────────────────────────────────

def record_decision(url: str, action: str, label: str) -> None:
    """Upsert a curator decision on the given URL.

    `action` ∈ {keep, reject, accept_top1, accept_top2, manual,
    save_for_later, summary_only}. Page 1 (Review) uses keep/reject;
    Page 2 (Organise) upgrades keep → accept_top1/top2/manual once a
    category is assigned.
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


def fetch_article_text(url: str) -> str:
    """Pull full article body text from `articles.text` for one URL.

    `v_dashboard` only exposes `text_clean` (a truncated 80-word snippet that
    often starts with nav cruft). The on-demand Generate-Summary buttons on
    Triage and Draft need the full body to produce a good summary, so this
    helper fetches it directly from `articles` on click.
    """
    if not url:
        return ""
    client = get_client()
    resp = client.table("articles").select("text").eq("url", url).limit(1).execute()
    rows = resp.data or []
    return (rows[0].get("text") if rows else "") or ""


def is_authenticated() -> bool:
    """True if the curator has entered the correct password this session.
    Read-only browsing is allowed without auth; mutating buttons are gated
    on this flag (see app.py's curator login widget in the sidebar)."""
    import streamlit as st
    return bool(st.session_state.get("authenticated", False))


def delete_decision(url: str) -> None:
    """Remove the curator_decisions row for `url` entirely. The article
    returns to Pending status in Review and disappears from Organise/Draft.
    Used by Organise's 'Send back to Review' button when the curator wants
    to reconsider an accept decision from scratch."""
    client = get_client()
    client.table("curator_decisions").delete().eq("url", url).execute()
    load_decisions.clear()


def set_newsletter_pick(url: str, selected: bool) -> None:
    """Persist a 'shortlist for newsletter' click on an already-accepted article.

    Uses UPDATE (not upsert) because Organise only shows articles with an
    existing decision row — and upsert would fail the NOT NULL on `action`
    if it ever hit the insert path.
    """
    client = get_client()
    client.table("curator_decisions").update(
        {"selected_for_newsletter": selected}
    ).eq("url", url).execute()
    load_decisions.clear()


def set_category_override(url: str, override: str | None) -> None:
    """Persist a 'move to <category>' override on an already-accepted article."""
    client = get_client()
    client.table("curator_decisions").update(
        {"newsletter_category_override": override}
    ).eq("url", url).execute()
    load_decisions.clear()


def add_curator_article(
    *, url: str, title: str, article_date_iso: str, source: str,
    text_clean: str, top1: str, top2: str,
) -> None:
    """Persist a curator-added article so its URL exists in `articles`.

    Without this, accepting / rejecting / saving a manually-added article
    would fail the curator_decisions → articles FK. We also write a row to
    classify_newsletter using the curator's two suggested categories with
    fake 1.0 / 0.0 confidences, so v_dashboard renders the article with the
    same shape as a scraped+classified one.

    Idempotent on URL: re-submitting the same URL is a no-op rather than
    an error (uses upsert with on_conflict=url).
    """
    client = get_client()

    client.table("articles").upsert({
        "url": url,
        "title": title,
        "article_date": article_date_iso,
        "source": source or "manually added",
        "source_type": "manually added",
        "text_clean": text_clean or title,
        "text": text_clean or None,
        "country": "eng",
        "dataset_type": "inference",
        "classification_status": "classified",
    }, on_conflict="url").execute()

    client.table("classify_newsletter").upsert({
        "url": url,
        "top1": top1,
        "top1_confidence": 1.0,
        "top2": top2,
        "top2_confidence": 0.0,
        "confidence_gap": 1.0,
    }, on_conflict="url").execute()

    load_classified_articles.clear()


def record_feedback(suggestions: str) -> None:
    """Append a free-text feedback row to curator_feedback (table from migration 008).
    Anonymous — no curator identity is recorded, per the Page 3 feedback-box spec.
    """
    if not suggestions or not suggestions.strip():
        return
    client = get_client()
    client.table("curator_feedback").insert({
        "suggestions": suggestions.strip(),
    }).execute()


def record_summary(url: str, summary: str) -> None:
    """Persist a generated LLM summary onto a curator_decisions row.

    Safe to call before any keep/reject — Page 1 (Review) lets the curator
    Generate Summary on a pending article. If no row exists yet, we insert
    a placeholder with action='summary_only' so the NOT NULL constraint on
    `action` is satisfied. Any subsequent keep/reject via record_decision()
    overwrites the placeholder.
    """
    client = get_client()
    existing = client.table("curator_decisions").select("action").eq("url", url).limit(1).execute()
    if not existing.data:
        client.table("curator_decisions").insert({
            "url": url,
            "action": "summary_only",
        }).execute()
    client.table("curator_decisions").update(
        {
            "summary": summary,
            "summary_generated_at": "now()",
        }
    ).eq("url", url).execute()
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


def get_kept_articles(df: pd.DataFrame) -> list[dict]:
    """Return articles the curator has kept on Page 1 (action='keep') or
    already categorised (action ∈ {accept_top1, accept_top2, manual}).

    Used by Page 2 (Select Categories). Excludes rejected and save_for_later.
    Each row carries `action` and `curator_label` so the page can render the
    correct status badge.
    """
    decisions = load_decisions()
    boundary = get_week_boundary()
    KEPT_ACTIONS = {"keep", "accept_top1", "accept_top2", "manual"}
    out: list[dict] = []
    for url, dec in decisions.items():
        if dec.get("action") not in KEPT_ACTIONS:
            continue
        if _before_boundary(dec.get("decided_at"), boundary):
            continue  # archived in a previous week
        match = df[df["url"] == url] if (not df.empty and "url" in df.columns) else pd.DataFrame()
        row = match.iloc[0].to_dict() if len(match) else {"url": url, "title": "Unknown"}
        row["action"] = dec.get("action")
        row["curator_label"] = dec.get("label") or None
        # Curator edit > pre-generated articles.summary (from v_dashboard)
        row["summary"] = dec.get("summary") or row.get("summary")
        out.append(row)
    return out


def get_accepted_articles(df: pd.DataFrame) -> list[dict]:
    """Join `v_dashboard` rows with current curator_decisions; return only
    articles the curator has actually accepted (top1, top2, or manual).

    Used by the Organise and Draft pages. Excludes:
      - rejected articles
      - save-for-later articles (curator hasn't decided yet)
      - rows that exist only because of a summary (no action set)
    Curator-added rows (session-only for now) are appended on top.
    """
    decisions = load_decisions()
    boundary = get_week_boundary()
    accepted: list[dict] = []

    ACCEPT_ACTIONS = {"accept_top1", "accept_top2", "manual"}
    for url, dec in decisions.items():
        if dec.get("action") not in ACCEPT_ACTIONS:
            continue
        if _before_boundary(dec.get("decided_at"), boundary):
            continue  # archived in a previous week
        match = df[df["url"] == url] if (not df.empty and "url" in df.columns) else pd.DataFrame()
        row = match.iloc[0].to_dict() if len(match) else {"url": url, "title": "Unknown"}
        row["curator_label"] = dec.get("label") or row.get("top1")
        if url in st.session_state.get("category_overrides", {}):
            row["curator_label"] = st.session_state.category_overrides[url]
        # Summary precedence: curator's edit > pre-generated (articles.summary
        # from v_dashboard). Without the fallback to row.get("summary"),
        # Draft page would show empty for articles the curator never edited
        # even after the pre-gen backfill.
        row["summary"] = dec.get("summary") or row.get("summary")
        accepted.append(row)

    for art in st.session_state.get("curator_articles", []):
        art_copy = dict(art)
        art_copy["curator_label"] = art.get("top1")
        art_copy["curator_added"] = True
        if art.get("url") in st.session_state.get("category_overrides", {}):
            art_copy["curator_label"] = st.session_state.category_overrides[art["url"]]
        accepted.append(art_copy)

    return accepted
