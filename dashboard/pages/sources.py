"""
Sources page — displays the current scraping roster (from data/sources_master.csv)
and provides a form for curators to suggest new sources.
"""

from datetime import datetime
from pathlib import Path

import streamlit as st
import pandas as pd

from dashboard.data import get_client


SOURCES_CSV = Path("data/sources_master.csv")

COVERAGE_LABELS = {
    "gov_uk": "UK Government",
    "four_nations_scotland": "Scotland",
    "four_nations_wales": "Wales",
    "four_nations_ni": "Northern Ireland",
    "research": "Research & Think Tanks",
    "sector_body": "Sector Bodies",
    "media": "Media",
    "edtech": "EdTech",
    "internal_ucl": "UCL / IOE",
    "tbd": "Uncategorised",
}

STATUS_LABEL = {
    "live": ("Live", "#27ae60"),
    "disabled_keyword_filter": ("Disabled (filter)", "#7f8c8d"),
    "disabled_alt_ingestion": ("Pending alt ingestion", "#e67e22"),
    "disabled_out_of_scope": ("Out of scope", "#95a5a6"),
}


@st.cache_data(ttl=600)
def _load_sources() -> pd.DataFrame:
    if not SOURCES_CSV.exists():
        return pd.DataFrame()
    df = pd.read_csv(SOURCES_CSV)
    if "pipeline_status" not in df.columns:
        df["pipeline_status"] = "live"
    return df


def _save_suggestion(name: str, url: str, coverage_hint: str, notes: str) -> bool:
    try:
        client = get_client()
        client.table("source_suggestions").insert({
            "source_name": name,
            "url": url or None,
            "coverage_hint": coverage_hint or None,
            "notes": notes or None,
        }).execute()
        return True
    except Exception as e:
        st.error(f"Could not save suggestion: {e}")
        return False


def render():
    st.title("Sources")
    st.markdown(
        "Sources monitored for the newsletter. Each one is scraped twice weekly "
        "(Tue and Thu) and runs through the classifier before reaching the Review page."
    )

    df = _load_sources()
    if df.empty:
        st.warning("`data/sources_master.csv` not found.")
        return

    # ── Headline metrics ─────────────────────────────────────────────────────
    live_count = (df["pipeline_status"] == "live").sum()
    disabled_count = len(df) - live_count
    coverage_count = df["coverage"].nunique() if "coverage" in df.columns else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total sources", len(df))
    col2.metric("Live", int(live_count))
    col3.metric("Coverage areas", int(coverage_count))

    # ── Group by coverage ─────────────────────────────────────────────────────
    st.subheader("Live sources by coverage area")
    live = df[df["pipeline_status"] == "live"].copy()
    for coverage_key, group in live.groupby("coverage"):
        label = COVERAGE_LABELS.get(coverage_key, coverage_key or "Uncategorised")
        with st.expander(f"{label} ({len(group)})"):
            for _, row in group.sort_values("source").iterrows():
                source_name = row.get("source") or row.get("id")
                url = row.get("url") or ""
                source_type = row.get("source_type") or ""
                if url and isinstance(url, str) and url.startswith("http"):
                    st.markdown(
                        f"- [{source_name}]({url}) &middot; <em style='color:#666;'>{source_type}</em>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(f"- {source_name} &middot; <em style='color:#666;'>{source_type}</em>",
                                unsafe_allow_html=True)

    # ── Deferred ─────────────────────────────────────────────────────────────
    deferred = df[df["pipeline_status"] != "live"]
    if len(deferred):
        st.subheader(f"Deferred ({len(deferred)})")
        st.caption("Sources currently not in the pipeline. See `docs/decisions/disabled_sources.md` for the rationale per source.")
        for _, row in deferred.sort_values(["pipeline_status", "source"]).iterrows():
            status_label, color = STATUS_LABEL.get(row["pipeline_status"], (row["pipeline_status"], "#7f8c8d"))
            badge = f"<span style='background:{color};color:white;padding:2px 8px;border-radius:4px;font-size:0.8em;'>{status_label}</span>"
            st.markdown(f"- {row.get('source', row['id'])} {badge}", unsafe_allow_html=True)

    # ── Suggest a source ────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Suggest a source")
    st.caption("Spot a missing source? Suggest it here. We'll review and add it to the roster if it fits the newsletter scope.")

    with st.form("suggest_source", clear_on_submit=True):
        source_name = st.text_input("Source name *", placeholder="e.g. Times Educational Supplement")
        source_url = st.text_input("URL", placeholder="e.g. https://www.tes.com/")
        coverage_hint = st.selectbox(
            "Coverage area (best guess)",
            options=["", *COVERAGE_LABELS.keys()],
            format_func=lambda x: COVERAGE_LABELS.get(x, "— choose —" if x == "" else x),
        )
        notes = st.text_area(
            "Why this source?",
            placeholder="e.g. publishes weekly analysis of school workforce data, often cited by DfE",
            height=100,
        )
        submitted = st.form_submit_button("Suggest source", use_container_width=True)

        if submitted:
            if not source_name:
                st.error("Source name is required.")
            elif _save_suggestion(source_name, source_url, coverage_hint, notes):
                st.success(f"Thanks — '{source_name}' added to the suggestions queue.")
