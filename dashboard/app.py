"""
ESRC ERP Newsletter Curator Dashboard
"""

# Streamlit Cloud runs `streamlit run dashboard/app.py` which sets sys.path[0]
# to dashboard/, not the repo root. Without the next 3 lines, every
# `from dashboard.<…> import` raises ModuleNotFoundError.
import sys
import base64
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd

from dashboard.config import NAVY, TEAL
from dashboard.styles import get_css
from dashboard.data import load_classified_articles, init_session_state, record_feedback
from dashboard.pages import triage, select_categories, draft


def main():
    st.set_page_config(
        page_title="ESRC ERP Newsletter",
        page_icon="\U0001f4f0",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.markdown(get_css(), unsafe_allow_html=True)

    # Hide the sidebar entirely (the toggle chevron + the panel itself).
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] { display: none !important; }
    div[data-testid="collapsedControl"] { display: none !important; }
    /* Pull main content flush with the viewport top so the grey header bar
       hugs the top of the window with no Streamlit whitespace above it. */
    .block-container { padding-top: 1rem !important; }
    /* Hide Streamlit's "Press ↵ to submit" helper text under text inputs. */
    [data-testid="InputInstructions"] { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

    # ── ESRC navy header bar with embedded logo ──────────────────────────────
    _logo_path = Path(__file__).parent / "erp_logo.png"
    if _logo_path.exists():
        logo_b64 = base64.b64encode(_logo_path.read_bytes()).decode()
        st.markdown(f"""
        <div style='background:{NAVY};
                    padding:18px 28px;margin:-1rem -2rem 20px -2rem;
                    display:flex;align-items:center;border-bottom:1px solid #0a142b;'>
            <img src='data:image/png;base64,{logo_b64}' style='height:80px;'/>
        </div>
        """, unsafe_allow_html=True)

    # Internal page keys (drive dispatch below) → curator-facing step labels.
    NAV = [
        "Triage", "Select Categories", "Newsletter Draft",
    ]
    NAV_LABELS = {
        "Triage": "Step 1: Triage",
        "Select Categories": "Step 2: Categorise",
        "Newsletter Draft": "Step 3: Draft Newsletter",
    }

    if "current_page" not in st.session_state:
        st.session_state.current_page = "Triage"
    cur = st.session_state.current_page

    # Make the step buttons larger + bolder so the workflow order reads clearly.
    st.markdown("""
    <style>
    [data-testid="stSegmentedControl"] button {
        font-size: 15px !important;
        font-weight: 600 !important;
        padding: 8px 22px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Top row: page nav on the left, login popover on the right ────────────
    col_nav, col_login = st.columns([5, 1])
    with col_nav:
        # Button-like segmented control reading "Step 1 / 2 / 3" so the curator
        # sees the workflow order at a glance.
        choice = st.segmented_control(
            "Navigate", NAV,
            format_func=lambda x: NAV_LABELS.get(x, x),
            default=cur if cur in NAV else NAV[0],
            label_visibility="collapsed",
            key="_top_nav_seg",
        )
        if choice and choice != cur:
            st.session_state.current_page = choice
            st.rerun()
    with col_login:
        if st.session_state.get("authenticated"):
            with st.popover("🔓 Curator", use_container_width=True):
                if st.button("Log out", use_container_width=True, key="_logout_btn"):
                    st.session_state.authenticated = False
                    st.rerun()
        else:
            with st.popover("🔒 Log in", use_container_width=True):
                with st.form("_login_form", clear_on_submit=False):
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
                        st.error("Wrong password" if pwd else "Enter a password")

    st.markdown("---")

    page = st.session_state.current_page

    df = load_classified_articles()

    if df.empty:
        st.error("No classified articles found in Supabase. Run the inference pipeline (s07 → classify_via_api → s10) to populate `classify_newsletter`.")
        st.stop()

    if "article_date" in df.columns:
        df["article_date"] = pd.to_datetime(df["article_date"], errors="coerce").dt.strftime("%d-%m-%Y")

    init_session_state()

    if page == "Triage":
        triage.render(df)
    elif page == "Select Categories":
        select_categories.render(df)
    elif page == "Newsletter Draft":
        draft.render(df)

    # ── Feedback on dashboard (every page) ──────────────────────────────────
    auth = bool(st.session_state.get("authenticated"))
    st.markdown("---")
    st.markdown("### 💬 Feedback on dashboard design & functionality")
    feedback_text = st.text_area(
        "Feedback",
        key="_feedback_box",
        height=110,
        placeholder="e.g. \"The Triage page is too slow\" / \"I can't find X\" / \"Why does the source filter not include Y?\"",
        label_visibility="collapsed",
        disabled=not auth,
    )
    if st.button("Send feedback", key="_feedback_submit", disabled=not auth, type="primary"):
        if feedback_text and feedback_text.strip():
            record_feedback(feedback_text.strip())
            st.session_state["_feedback_box"] = ""
            st.success("Feedback sent. Thank you.")
            st.rerun()
        else:
            st.warning("Feedback is empty.")


main()
