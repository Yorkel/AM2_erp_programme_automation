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
from dashboard.pages import about, triage, draft


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

    NAV = [
        "Triage", "Newsletter Draft", "About",
    ]

    if "current_page" not in st.session_state:
        st.session_state.current_page = "Triage"
    cur = st.session_state.current_page

    nav_idx = NAV.index(cur) if cur in NAV else 0
    choice = st.sidebar.radio("Navigate", NAV, index=nav_idx, label_visibility="collapsed")
    if choice and choice != cur:
        st.session_state.current_page = choice
        st.rerun()

    # ── Curator login (write access) ─────────────────────────────────────────
    # Read-only browsing is open; mutating buttons (Accept/Reject/etc.) are
    # disabled unless the curator authenticates with the password stored in
    # Streamlit secrets as CURATOR_PASSWORD.
    st.sidebar.markdown("---")
    if st.session_state.get("authenticated"):
        # Dark green background + white text — high contrast and works with
        # the sidebar's `color: white !important` default rule.
        st.sidebar.markdown(
            "<div style='background:#1e7e34;border:1px solid #28a745;border-radius:5px;"
            "padding:10px 14px;font-weight:700;text-align:center;"
            "margin-bottom:8px;'>🔓 Curator mode</div>",
            unsafe_allow_html=True,
        )
        if st.sidebar.button("Log out", use_container_width=True, key="_logout_btn"):
            st.session_state.authenticated = False
            st.rerun()
    else:
        st.sidebar.markdown("### 🔒 Curator login")
        st.sidebar.caption("Read-only — log in to edit.")
        with st.sidebar.form("_login_form", clear_on_submit=False):
            pwd = st.text_input(
                "Password", type="password", key="_curator_pw",
                label_visibility="collapsed", placeholder="Password",
            )
            submit = st.form_submit_button(
                "Log in", use_container_width=True, type="primary",
            )
        if submit:
            try:
                expected = st.secrets["CURATOR_PASSWORD"]
            except (KeyError, FileNotFoundError):
                expected = None
            if expected and pwd == expected:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.sidebar.error("Wrong password" if pwd else "Enter a password")

    page = st.session_state.current_page

    df = load_classified_articles()

    if df.empty and page != "About":
        st.error("No classified articles found in Supabase. Run the inference pipeline (s07 → classify_via_api → s10) to populate `classify_newsletter`.")
        st.stop()

    if "article_date" in df.columns:
        df["article_date"] = pd.to_datetime(df["article_date"], errors="coerce").dt.strftime("%d-%m-%Y")

    init_session_state()

    if page == "About":
        about.render()
    elif page == "Triage":
        triage.render(df)
    elif page == "Newsletter Draft":
        draft.render(df)


main()
