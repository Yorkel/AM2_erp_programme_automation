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

from dashboard.config import MS_FORM_URL, SOURCE_LABELS
from dashboard.data import (
    is_authenticated, load_decisions, record_decision, record_summary,
)
from src.inference.summarise import summarise_article


N_WEEKS = 8  # how many recent weeks to surface in the selector


def _tuesday_on_or_before(d: date) -> date:
    """Most recent Tuesday on or before `d` — anchors a scrape-week (Tue→Mon)."""
    return d - timedelta(days=(d.weekday() - 1) % 7)


def _week_options(df: pd.DataFrame, n: int = N_WEEKS) -> list[tuple[str, date, date]]:
    """Build N most recent Tue→Mon weeks as (label, start, end). Newest first."""
    dates = df["_article_date"].dropna() if "_article_date" in df.columns else pd.Series([], dtype=object)
    anchor = _tuesday_on_or_before(dates.max() if not dates.empty else date.today())
    out: list[tuple[str, date, date]] = []
    for i in range(n):
        wk_start = anchor - timedelta(days=7 * i)
        wk_end = wk_start + timedelta(days=6)
        out.append((f"Week of {wk_start:%d %b %Y}", wk_start, wk_end))
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


def render(df):
    st.title("Triage")
    st.markdown(
        "Quickly **keep** or **reject** each article from this week's pull. "
        "Kept articles move to **Select Categories** for category assignment, "
        "then to **Newsletter Draft**."
    )

    # Targeted button colours: the Keep button uses a marker div + sibling-selector
    # so it can be green (positive action) without recolouring every secondary button.
    # Reject stays neutral grey (Streamlit's default secondary).
    st.markdown("""
    <style>
    /* Keep button = green. The .keep-btn-marker div is placed immediately
       before the st.button("Keep") call; the adjacent-sibling selector then
       targets the button's element-container. */
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

    # ── Add Article: external link to MS Form ──────────────────────────────
    st.link_button(
        "➕  Add article via form  ↗",
        MS_FORM_URL,
        help="Opens the ERP newsletter-suggestions Microsoft Form in a new tab.",
    )

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

    # ── Filters ─────────────────────────────────────────────────────────────
    decisions = load_decisions()
    STATUS_OPTIONS = ["Pending", "All", "Kept", "Rejected", "Categorised"]
    col_status, col_sort = st.columns(2)
    with col_status:
        status_filter = st.selectbox("Show", STATUS_OPTIONS, index=0)
    with col_sort:
        sort_by = st.selectbox(
            "Order by", ["Date (newest first)", "Date (oldest first)", "Source"]
        )

    if status_filter != "All":
        filtered = filtered[filtered["url"].apply(
            lambda u: _status_for(u, decisions) == status_filter
        )].copy()

    if sort_by == "Date (newest first)":
        filtered = filtered.sort_values("_article_date", ascending=False, na_position="last")
    elif sort_by == "Date (oldest first)":
        filtered = filtered.sort_values("_article_date", ascending=True, na_position="last")
    else:
        filtered = filtered.sort_values("source", ascending=True, na_position="last")

    st.info(f"**{selected_label}** — {len(filtered)} article(s) shown ({status_filter})")

    # ── Article cards ───────────────────────────────────────────────────────
    auth = is_authenticated()
    for idx, row in filtered.iterrows():
        url = row.get("url") or str(idx)
        title = row.get("title", "No title")
        source_name = SOURCE_LABELS.get(row.get("source", ""), row.get("source", ""))
        article_date = row.get("article_date", "")
        status = _status_for(url, decisions)
        current_summary = (decisions.get(url) or {}).get("summary") or ""

        st.markdown(
            "<div style='border-top:3px solid #1d3461;margin:20px 0;'></div>",
            unsafe_allow_html=True,
        )
        st.markdown(f"### {title}")

        with st.container(border=True):
            # Source · Date
            st.markdown(
                f"<p style='color:#666;font-size:15px;margin-bottom:4px;'>"
                f"<b>Source:</b> {source_name}  &middot;  <b>Date:</b> {article_date}</p>",
                unsafe_allow_html=True,
            )

            # URL (full, clickable) + Status (same line, status right-aligned)
            colour = _STATUS_COLOUR.get(status, "#888")
            col_url, col_status = st.columns([4, 1])
            with col_url:
                if url:
                    st.markdown(
                        f"<p style='font-size:13px;margin:0;overflow-wrap:anywhere;'>"
                        f"<b>URL:</b> <a href='{url}' target='_blank'>{url}</a></p>",
                        unsafe_allow_html=True,
                    )
            with col_status:
                st.markdown(
                    f"<p style='text-align:right;color:{colour};font-weight:600;margin:0;'>"
                    f"Status: {status}</p>",
                    unsafe_allow_html=True,
                )

            # Generate summary (orange — primary action, top of action area)
            if st.button(
                "✎ Generate summary", key=f"gen_{url}",
                type="primary", use_container_width=True, disabled=not auth,
            ):
                with st.spinner("Summarising via Claude…"):
                    new_summary = summarise_article(
                        title=title,
                        text=row.get("text_clean", "") or "",
                        category=row.get("top1"),
                    )
                record_summary(url, new_summary)
                st.rerun()

            # Summary text — appears between Generate button and Keep/Reject
            if current_summary:
                st.markdown(
                    f"<div style='background:#f8f4ea;border-left:3px solid #f39c12;"
                    f"padding:8px 12px;margin:8px 0;'>"
                    f"<b>Summary:</b> {current_summary}</div>",
                    unsafe_allow_html=True,
                )

            # Keep / Reject — secondary actions below the summary.
            # Keep is styled green via the .keep-btn-marker → CSS sibling rule
            # injected above.
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
