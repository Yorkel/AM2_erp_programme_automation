"""
Overview / landing page — at-a-glance summary of the most recent scrape week.

Shows: article count, source count, top topics, and rough yield (% with
predictions above a confidence threshold). All from the v_dashboard view.
"""

from datetime import datetime
from collections import Counter

import streamlit as st
import pandas as pd

from dashboard.config import CATEGORY_LABELS, CATEGORY_ORDER
from dashboard.data import load_decisions


def _latest_week(df: pd.DataFrame) -> int | None:
    if df.empty or "week_number" not in df.columns:
        return None
    weeks = df["week_number"].dropna()
    if weeks.empty:
        return None
    return int(weeks.max())


def render(df: pd.DataFrame):
    st.title("Overview")
    st.markdown("At-a-glance summary of this week's scrape. Use the sidebar to dig in.")

    if df.empty:
        st.warning("No classified articles in Supabase yet. Run the inference pipeline to populate.")
        return

    latest = _latest_week(df)
    if latest is None:
        st.warning("Articles in the database have no `week_number` set — overview can't compute.")
        return

    this_week = df[df["week_number"] == latest].copy()
    prev_week = df[df["week_number"] == (latest - 1)].copy() if (df["week_number"] == (latest - 1)).any() else pd.DataFrame()

    # ── Headline metrics ─────────────────────────────────────────────────────
    st.subheader(f"Week {latest}")

    n_articles = len(this_week)
    n_sources = this_week["source"].nunique() if "source" in this_week.columns else 0
    decisions = load_decisions()
    n_reviewed = sum(1 for url in this_week.get("url", []) if url in decisions)

    mean_top1 = (
        this_week["top1_confidence"].mean()
        if "top1_confidence" in this_week.columns and not this_week.empty
        else None
    )
    mean_top2_combined = (
        (this_week["top1_confidence"] + this_week["top2_confidence"]).mean()
        if {"top1_confidence", "top2_confidence"}.issubset(this_week.columns)
           and not this_week.empty
        else None
    )

    delta_articles = n_articles - len(prev_week) if not prev_week.empty else None
    delta_sources = n_sources - prev_week["source"].nunique() if not prev_week.empty and "source" in prev_week.columns else None

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Articles scraped", n_articles, delta=delta_articles if delta_articles is not None else None)
    col2.metric("Sources contributing", n_sources, delta=delta_sources if delta_sources is not None else None)
    col3.metric("Reviewed so far", f"{n_reviewed} / {n_articles}")
    if mean_top1 is not None:
        col4.metric("Mean top-1 confidence", f"{mean_top1:.0%}",
                    help="Average model confidence in its best-guess category.")
    if mean_top2_combined is not None:
        col5.metric("Mean top-2 confidence", f"{mean_top2_combined:.0%}",
                    help="Average combined probability that the correct category is one of the top two predictions.")

    st.markdown("")

    # ── Top topics (categories) this week ────────────────────────────────────
    if "top1" in this_week.columns and not this_week.empty:
        st.subheader("Predicted categories this week")
        cat_counts = this_week["top1"].value_counts()
        if not prev_week.empty and "top1" in prev_week.columns:
            prev_cat_counts = prev_week["top1"].value_counts()
        else:
            prev_cat_counts = pd.Series(dtype=int)

        cols = st.columns(3)
        for i, key in enumerate(CATEGORY_ORDER):
            with cols[i % 3]:
                count = int(cat_counts.get(key, 0))
                prev = int(prev_cat_counts.get(key, 0))
                delta = count - prev if not prev_cat_counts.empty else None
                with st.container(border=True):
                    st.markdown(f"**{CATEGORY_LABELS.get(key, key)}**")
                    st.metric(label="", value=count, delta=delta, label_visibility="collapsed")

    st.markdown("")

    # ── Top contributing sources this week ────────────────────────────────────
    if "source" in this_week.columns and not this_week.empty:
        st.subheader("Top contributing sources")
        src_counts = this_week["source"].value_counts().head(10)
        for source_name, count in src_counts.items():
            st.markdown(f"- **{source_name}** &middot; {count} article{'s' if count != 1 else ''}",
                        unsafe_allow_html=True)

    # ── Quick links ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.caption(
        f"Last refresh: {datetime.now().strftime('%Y-%m-%d %H:%M')} &middot; "
        f"Predictions from model v1_2026-05-16. Go to **Review Articles** to start "
        f"the weekly review.",
    )
