"""
ESRC ERP Newsletter Curator Dashboard
"""

# Streamlit Cloud runs `streamlit run dashboard/app.py` which sets sys.path[0]
# to dashboard/, not the repo root. Without the next 3 lines, every
# `from dashboard.<…> import` raises ModuleNotFoundError.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd

from dashboard.config import NAVY, TEAL
from dashboard.styles import get_css
from dashboard.data import load_classified_articles, init_session_state
from dashboard.pages import overview, about, add_article, review, organise, draft, sources, feedback


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

    PRIMARY = ["Overview", "Review Articles", "Organise", "Newsletter Draft", "Add Article"]
    SECONDARY = ["Sources", "Feedback", "About"]

    if "current_page" not in st.session_state:
        st.session_state.current_page = "Overview"
    cur = st.session_state.current_page

    primary_idx = PRIMARY.index(cur) if cur in PRIMARY else None
    primary_choice = st.sidebar.radio("Navigate", PRIMARY, index=primary_idx)
    if primary_choice and primary_choice != cur:
        st.session_state.current_page = primary_choice
        st.rerun()

    st.sidebar.markdown("---")
    secondary_idx = SECONDARY.index(cur) if cur in SECONDARY else None
    secondary_choice = st.sidebar.radio(
        "More", SECONDARY, index=secondary_idx, label_visibility="collapsed",
    )
    if secondary_choice and secondary_choice != cur:
        st.session_state.current_page = secondary_choice
        st.rerun()

    # ── Curator login (write access) ─────────────────────────────────────────
    # Read-only browsing is open; mutating buttons (Accept/Reject/etc.) are
    # disabled unless the curator authenticates with the password stored in
    # Streamlit secrets as CURATOR_PASSWORD.
    st.sidebar.markdown("---")
    if st.session_state.get("authenticated"):
        st.sidebar.success("Curator mode ✓")
        if st.sidebar.button("Log out", use_container_width=True, key="_logout_btn"):
            st.session_state.authenticated = False
            st.rerun()
    else:
        st.sidebar.caption("Read-only. Enter password to enable editing.")
        pwd = st.sidebar.text_input(
            "Curator password", type="password", key="_curator_pw",
            label_visibility="collapsed", placeholder="Curator password",
        )
        if pwd:
            try:
                expected = st.secrets["CURATOR_PASSWORD"]
            except (KeyError, FileNotFoundError):
                expected = None
            if expected and pwd == expected:
                st.session_state.authenticated = True
                st.rerun()
            elif pwd:
                st.sidebar.error("Wrong password")

    page = st.session_state.current_page

    df = load_classified_articles()

    if df.empty and page not in ["About", "Sources"]:
        st.error("No classified articles found in Supabase. Run the inference pipeline (s07 → classify_via_api → s10) to populate `classify_newsletter`.")
        st.stop()

    if "article_date" in df.columns:
        df["article_date"] = pd.to_datetime(df["article_date"], errors="coerce").dt.strftime("%d-%m-%Y")

    init_session_state()

    if page == "Overview":
        overview.render(df)
    elif page == "About":
        about.render()
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


main()
