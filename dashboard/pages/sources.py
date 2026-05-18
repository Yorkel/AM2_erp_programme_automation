"""
Sources page — placeholder while the source roster + suggestion form is rebuilt.
Previous version read from data/sources_master.csv (gitignored, so missing on
Streamlit Cloud) — page now temporarily shows a coming-soon notice.
"""

import streamlit as st


def render():
    st.title("Sources")
    st.info(
        "Coming soon — the source roster and 'suggest a new source' form are "
        "being rebuilt. In the meantime, the current list of monitored sources "
        "lives in `src/scraping/sources.yml` in the repo."
    )
