"""
Page 4 — Sources.

A reference view: every source that actually has articles in the dashboard,
with how many have been scraped OVERALL and THIS WEEK. This is the empirical
"what's feeding the dashboard" list — a source counts if its articles show up,
regardless of whether it's a direct scrape, a Google Alert, or a newsletter.

"This week" = the current Mon–Sun calendar week (matches the rest of the UI).
"""

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from dashboard.config import SOURCE_LABELS


def render(df):
    st.title("Sources")
    st.caption(
        "Every source with articles in the dashboard, and how many have been "
        "scraped overall and this week. A source appears here if its articles "
        "show up — whether via direct scrape, Google Alert, or newsletter."
    )

    if df is None or df.empty or "source" not in df.columns:
        st.info("No articles yet.")
        return

    d = df.copy()
    d["_date"] = pd.to_datetime(d.get("article_date"), errors="coerce", dayfirst=True)
    d["source"] = d["source"].fillna("").replace("", "(unknown)")

    today = date.today()
    week_start = pd.Timestamp(today - timedelta(days=today.weekday()))  # Monday

    rows = []
    for src, g in d.groupby("source"):
        # NaT >= Timestamp evaluates False, so this is safe for missing dates.
        this_week = int((g["_date"] >= week_start).sum())
        rows.append({
            "Source": SOURCE_LABELS.get(src, src),
            "Overall": len(g),
            "This week": this_week,
        })

    table = pd.DataFrame(rows).sort_values(
        ["This week", "Overall"], ascending=False
    ).reset_index(drop=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Sources", len(table))
    c2.metric("Articles overall", int(table["Overall"].sum()))
    c3.metric("Articles this week", int(table["This week"].sum()))

    st.dataframe(table, use_container_width=True, hide_index=True)
