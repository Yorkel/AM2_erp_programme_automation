"""
ESRC ERP Newsletter Curator Dashboard
"""

import streamlit as st
import pandas as pd
from pathlib import Path

from .config import NAVY, TEAL
from .styles import get_css
from .data import load_classified_articles, init_session_state
from .pages import about, instructions, add_article, review, organise, draft, sources, feedback


def main():
    st.set_page_config(
        page_title="ESRC ERP Newsletter",
        page_icon="\U0001f4f0",
        layout="wide",
    )

    st.markdown(get_css(), unsafe_allow_html=True)

    _logo_path = Path(__file__).parent / "erp_logo.png"
    if _logo_path.exists():
        st.sidebar.image(str(_logo_path), use_container_width=True)
    st.sidebar.title("Newsletter Curator")

    page = st.sidebar.radio(
        "Navigate",
        ["About", "Instructions", "Add Article", "Review Articles", "Organise", "Newsletter Draft", "Sources", "Feedback"],
    )

    df = load_classified_articles()

    if df.empty and page not in ["About", "Sources"]:
        st.error("No classified articles found. Place `classified_articles.csv` in `data/modelling/`.")
        st.stop()

    if "article_date" in df.columns:
        df["article_date"] = pd.to_datetime(df["article_date"], errors="coerce").dt.strftime("%d-%m-%Y")

    init_session_state()

    st.markdown(
        "<div style='background:#fff3cd;border:1px solid #ffc107;border-radius:5px;padding:12px 16px;margin-bottom:16px;font-size:13px;color:#856404;text-align:center;'>"
        "This is a prototype dashboard. The production version will be private to the programme curators.<br>"
        "<strong>Warning:</strong> Your selections are saved for this session only and will reset when the page closes. The production version will save decisions permanently.</div>",
        unsafe_allow_html=True,
    )

    if page == "About":
        about.render()
    elif page == "Instructions":
        instructions.render()
    elif page == "Add Article":
        add_article.render()
    elif page == "Review Articles":
        review.render(df)
    elif page == "Organise":
        organise.render(df)
    elif page == "Newsletter Draft":
        draft.render(df)
    elif page == "Sources":
        sources.render()
    elif page == "Feedback":
        feedback.render()
