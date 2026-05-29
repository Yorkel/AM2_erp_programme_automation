"""
Page 1 — Review (triage).

Curator quickly keeps or rejects each article from the selected week, and
optionally generates a summary. NO category assignment here — kept articles
flow to Page 2 (Organise) where the category is set.

Action values written to curator_decisions:
  - "keep"          curator wants this in the newsletter (no category yet)
  - "reject"        curator does not want this
  - "summary_only"  placeholder if Generate Summary clicked before keep/reject
"""

from datetime import date, timedelta

import streamlit as st
import pandas as pd

from dashboard.config import SOURCE_LABELS
from dashboard.data import (
    fetch_article_text, is_authenticated, load_decisions,
    record_decision, record_summary,
)
from src.inference.summarise import summarise_article


def _tuesday_on_or_before(d: date) -> date:
    """Most recent Tuesday on or before `d` — anchors a scrape-week (Tue→Mon)."""
    return d - timedelta(days=(d.weekday() - 1) % 7)


def _ordinal(n: int) -> str:
    """1 -> '1st', 2 -> '2nd', 11 -> '11th', etc."""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _format_week_label(wk_start: date, wk_end: date) -> str:
    """e.g. 'Tuesday 19th May - Monday 25th May 2026' (year only on the end
    date to keep the label readable). If the week spans years, show both."""
    start = f"Tuesday {_ordinal(wk_start.day)} {wk_start:%B}"
    if wk_start.year != wk_end.year:
        start = f"{start} {wk_start.year}"
    end = f"Monday {_ordinal(wk_end.day)} {wk_end:%B} {wk_end.year}"
    return f"{start} - {end}"


def _week_options(df: pd.DataFrame) -> list[tuple[str, date, date]]:
    """Build every completed Tue→Mon week back to the earliest article we have.
    A week is 'completed' only once its Monday end has passed (so the
    in-progress week isn't shown until the following Tuesday).
    Newest first."""
    if "_article_date" not in df.columns:
        return []
    dates = df["_article_date"].dropna()
    if dates.empty:
        return []
    earliest = _tuesday_on_or_before(dates.min())
    # Latest completed week ends on the most recent Monday < today.
    today = date.today()
    days_since_mon = (today.weekday() - 0) % 7  # Mon=0
    last_completed_end = today - timedelta(days=days_since_mon + 1) if days_since_mon == 0 else today - timedelta(days=days_since_mon)
    # If today is Mon, the week ending yesterday hasn't quite finished — so
    # only show weeks ending strictly before today.
    if last_completed_end >= today:
        last_completed_end = today - timedelta(days=1)
    anchor = _tuesday_on_or_before(last_completed_end)
    out: list[tuple[str, date, date]] = []
    cur = anchor
    while cur >= earliest:
        wk_end = cur + timedelta(days=6)
        out.append((_format_week_label(cur, wk_end), cur, wk_end))
        cur = cur - timedelta(days=7)
    return out


def _status_for(url: str, decisions: dict) -> str:
    dec = decisions.get(url)
    if not dec:
        return "Pending"
    action = dec.get("action")
    if action == "reject":
        return "Rejected"
    if action == "keep":
        return "Kept"
    if action in ("accept_top1", "accept_top2", "manual"):
        return "Categorised"
    # summary_only or unknown — show as pending in this view
    return "Pending"


_STATUS_COLOUR = {
    "Pending": "#888",
    "Kept": "#1e8449",
    "Rejected": "#c0392b",
    "Categorised": "#2980b9",
}

_TAG_STYLE = (
    "background:#eef;color:#333;padding:1px 6px;border-radius:8px;"
    "font-size:10px;border:1px solid #ccd;margin-right:3px;"
)


def _badges_html(geo: str | None, topics: list[str] | None) -> str:
    """Return an HTML snippet for the 'Key tags:' row — geographic_focus +
    up to 3 topic_tags. All badges share one neutral style (country isn't
    coloured differently from topics). Empty string if nothing to render."""
    parts = []
    if geo:
        parts.append(f"<span style='{_TAG_STYLE}'>{geo}</span>")
    for t in (topics or [])[:3]:
        parts.append(f"<span style='{_TAG_STYLE}'>{t}</span>")
    if not parts:
        return ""
    return (
        "<p style='margin:2px 0;font-size:11px;color:#555;'>"
        "<b>Key tags:</b> " + "".join(parts) + "</p>"
    )


def render(df):
    st.title("Step 1: Triage")

    # Targeted button colours: the Keep button uses a marker div + sibling-selector
    # so it can be green (positive action) without recolouring every secondary button.
    # Reject stays neutral grey (Streamlit's default secondary).
    st.markdown("""
    <style>
    /* Keep button = green. The .keep-btn-marker div is placed immediately
       before the st.button("Keep") call; the adjacent-sibling selector then
       targets the button's element-container. The marker's wrapper is
       collapsed to 0 height so Keep stays aligned with Reject. */
    .element-container:has(.keep-btn-marker) {
        display: none;
    }
    .element-container:has(.keep-btn-marker) + div [data-testid="stButton"] button {
        background-color: #2ecc71 !important;
        border-color: #27ae60 !important;
        color: white !important;
    }
    .element-container:has(.keep-btn-marker) + div [data-testid="stButton"] button:hover {
        background-color: #27ae60 !important;
        border-color: #229954 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Normalise article_date. Scraped rows = ISO; curator-added = DD-MM-YYYY;
    # dayfirst=True handles both.
    df = df.copy()
    df["_article_date"] = pd.to_datetime(
        df["article_date"], errors="coerce", dayfirst=True
    ).dt.date

    # ── Week selector ───────────────────────────────────────────────────────
    weeks = _week_options(df)
    selected_label = st.selectbox(
        "Week", [w[0] for w in weeks], index=0,
        help="Articles are scraped once a week (Tuesday morning). Each week runs Tue–Mon.",
    )
    week_start, week_end = next(
        (s, e) for (lbl, s, e) in weeks if lbl == selected_label
    )

    filtered = df[
        (df["_article_date"] >= week_start) & (df["_article_date"] <= week_end)
    ].copy()

    # Default behaviour: show only Pending articles, newest first. The filter
    # and sort selectboxes used to live here but Gemma asked them removed —
    # in practice she always used the defaults anyway.
    decisions = load_decisions()
    filtered = filtered[filtered["url"].apply(
        lambda u: _status_for(u, decisions) == "Pending"
    )].copy()
    filtered = filtered.sort_values("_article_date", ascending=False, na_position="last")

    st.info(f"{len(filtered)} pending article(s)")

    # ── Article cards ───────────────────────────────────────────────────────
    for idx, row in filtered.iterrows():
        _render_triage_card(row.to_dict())


@st.fragment
def _render_triage_card(row: dict):
    """Render one article card. Wrapped in @st.fragment so clicks
    (Keep, Reject, Generate Summary) only rerun this single card — not
    the whole 100-card list. Fetches own decisions for fresh state."""
    decisions = load_decisions()
    auth = is_authenticated()
    url = row.get("url") or ""
    title = row.get("title", "No title") or "No title"
    source_name = SOURCE_LABELS.get(row.get("source", ""), row.get("source", "") or "")
    article_date = row.get("article_date", "") or ""
    status = _status_for(url, decisions)
    current_summary = (
        (decisions.get(url) or {}).get("summary")
        or row.get("summary")
        or ""
    )

    st.markdown(
        "<div style='border-top:3px solid #1d3461;margin:20px 0;'></div>",
        unsafe_allow_html=True,
    )
    st.markdown(f"### {title}")

    with st.container(border=True):
        # Status badge sits inline with title area on the right; URL + tags
        # take up the rest. Tags go ABOVE source (matches Select Categories).
        colour = _STATUS_COLOUR.get(status, "#888")

        # Key tags row — directly under title, before source/date
        badges = _badges_html(row.get("geographic_focus"), row.get("topic_tags"))
        if badges:
            st.markdown(badges, unsafe_allow_html=True)

        # Source · Date
        st.markdown(
            f"<p style='color:#666;font-size:14px;margin:2px 0;'>"
            f"<b>Source:</b> {source_name} &nbsp;&nbsp; <b>Date:</b> {article_date}</p>",
            unsafe_allow_html=True,
        )

        # URL (full-width, no per-card Status badge — filter already gates view)
        if url:
            st.markdown(
                f"<p style='font-size:12px;margin:0;overflow-wrap:anywhere;'>"
                f"<b>URL:</b> <a href='{url}' target='_blank'>{url}</a></p>",
                unsafe_allow_html=True,
            )

        with st.expander("📋 Show summary", expanded=False):
            if current_summary:
                st.markdown(
                    f"<div style='background:#f8f4ea;border-left:3px solid #f39c12;"
                    f"padding:8px 12px;'>{current_summary}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div style='background:#f5f5f5;border-left:3px solid #aaa;"
                    "padding:8px 12px;color:#666;font-style:italic;'>"
                    "Summary unavailable</div>",
                    unsafe_allow_html=True,
                )
                if st.button(
                    "✎ Generate summary", key=f"gen_{url}",
                    type="primary", use_container_width=True, disabled=not auth,
                ):
                    with st.spinner("Summarising via Claude…"):
                        # Fetch full body from articles.text. NEVER fall back
                        # to text_clean — its first-80-words truncation often
                        # contains nav cruft ("HOME > Blog >") which produces
                        # bad summaries. If text is empty, summarise_article
                        # honestly returns "Summary unavailable".
                        body = fetch_article_text(url)
                        new_summary = summarise_article(
                            title=title, text=body, category=row.get("top1"),
                        )
                    record_summary(url, new_summary)
                    st.rerun()

        col_keep, col_reject = st.columns(2)
        with col_keep:
            st.markdown('<div class="keep-btn-marker"></div>', unsafe_allow_html=True)
            if st.button(
                "✓ Keep", key=f"keep_{url}",
                type="secondary", use_container_width=True, disabled=not auth,
            ):
                record_decision(url, "keep", "")
                st.rerun()
        with col_reject:
            if st.button(
                "✕ Reject", key=f"reject_{url}",
                type="secondary", use_container_width=True, disabled=not auth,
            ):
                record_decision(url, "reject", "")
                st.rerun()
