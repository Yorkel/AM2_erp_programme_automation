"""
Page 4 — Sources.

A coverage view of every source running through the dashboard (the web-scrape /
Google-Alert path), with how many articles were scraped OVERALL and in the LAST
COMPLETED week. Built by joining the live source roster
(`data/sources_master.csv`, excluding newsletter sources which arrive by email,
not the scraper) with actual article counts — so approved sources that produced
nothing still appear (with 0), making coverage gaps visible.

"Last week" = the most recent completed Tue→Mon scrape week (matches Triage).
"""

from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import streamlit as st

from dashboard.config import SOURCE_LABELS

_MASTER = Path(__file__).resolve().parents[2] / "data" / "sources_master.csv"


def _domain(u: str) -> str:
    try:
        return urlparse(str(u or "")).netloc.lower().replace("www.", "")
    except Exception:
        return ""


def render(df):
    st.title("Sources")

    # Scrape weeks run Tue→Mon (matches Triage). "Last week" = the most recently
    # completed one — today's week is still in progress, so step back.
    today = date.today()
    this_tue = today - timedelta(days=(today.weekday() - 1) % 7)   # most recent Tue ≤ today
    wk_start = pd.Timestamp(this_tue - timedelta(days=7))          # previous Tuesday
    wk_end_incl = this_tue - timedelta(days=1)                     # previous Monday
    wk_end = pd.Timestamp(wk_end_incl) + pd.Timedelta(days=1)      # exclusive bound
    wk_label = f"{(this_tue - timedelta(days=7)).day}–{wk_end_incl.day} {wk_end_incl:%b}"
    wk_col = f"Last week ({wk_label})"

    st.caption(
        "All sources running through the dashboard (web scrape + Google Alerts), "
        f"with articles scraped overall and in the last full week ({wk_label}). "
        "Newsletter sources arrive by email and aren't included. A source shows "
        "0 if it's approved but produced nothing that week."
    )

    if df is None or df.empty or "source" not in df.columns:
        st.info("No articles yet.")
        return

    d = df.copy()
    d["_date"] = pd.to_datetime(d.get("article_date"), errors="coerce", dayfirst=True)
    d["source"] = d["source"].fillna("").replace("", "(unknown)")

    # Article counts per raw source string (overall + last week).
    counts: dict[str, list[int]] = {}
    for src, g in d.groupby("source"):
        wk = int(((g["_date"] >= wk_start) & (g["_date"] < wk_end)).sum())
        counts[src] = [len(g), wk]

    # Live, non-newsletter roster (the dashboard-path sources).
    try:
        master = pd.read_csv(_MASTER).fillna("")
        master = master[
            (master["pipeline_status"].str.strip() == "live")
            & (master["source_type"].str.strip() != "newsletter")
        ].reset_index(drop=True)
    except Exception:
        master = pd.DataFrame()

    # Lookups: exact id/name (unambiguous) and domain (only used when unique, to
    # avoid e.g. every gov.uk source claiming a generic "gov.uk" article-source).
    exact: dict[str, int] = {}
    domain_rows: dict[str, list[int]] = {}
    for idx, r in master.iterrows():
        for k in {str(r.get("id", "")).strip().lower(), str(r.get("source", "")).strip().lower()}:
            if k:
                exact.setdefault(k, idx)
        for dk in {_domain(r.get("url", "")), _domain(r.get("rss_feed", "")), _domain(r.get("ingestion_url", ""))}:
            if dk:
                domain_rows.setdefault(dk, []).append(idx)

    # Assign each article-source to AT MOST ONE roster row (exact > unique-domain).
    tally = {idx: [0, 0] for idx in master.index}
    unclaimed: list[tuple[str, int, int]] = []
    for s, (overall, wk) in counts.items():
        sl = s.strip().lower()
        if sl in exact:
            idx = exact[sl]
        elif sl in domain_rows and len(domain_rows[sl]) == 1:
            idx = domain_rows[sl][0]
        else:
            unclaimed.append((s, overall, wk))
            continue
        tally[idx][0] += overall
        tally[idx][1] += wk

    rows = []
    for idx, r in master.iterrows():
        o, w = tally[idx]
        rows.append({"Source": r.get("source") or r.get("id"), "Overall": o, wk_col: w})
    for s, overall, wk in unclaimed:
        rows.append({"Source": SOURCE_LABELS.get(s, s), "Overall": overall, wk_col: wk})

    table = pd.DataFrame(rows).sort_values(
        ["Overall", wk_col], ascending=False
    ).reset_index(drop=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Sources", len(table))
    c2.metric("Articles overall", int(table["Overall"].sum()))
    c3.metric(f"Articles last week ({wk_label})", int(table[wk_col].sum()))

    st.dataframe(table, use_container_width=True, hide_index=True)
