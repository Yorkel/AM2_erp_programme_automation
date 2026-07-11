"""
ESRC ERP Newsletter Curator Dashboard
"""

# Streamlit Cloud runs `streamlit run dashboard/app.py` which sets sys.path[0]
# to dashboard/, not the repo root. Without the next 3 lines, every
# `from dashboard.<…> import` raises ModuleNotFoundError.
import sys
import base64
import hmac
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd

from dashboard.config import NAVY, TEAL
from dashboard.styles import get_css
from dashboard.data import (
    generate_missing_article_summaries, load_classified_articles,
    init_session_state, record_feedback, week_processing_status,
)
from dashboard.pages import triage, select_categories, draft, sources


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
        "Triage", "Select Categories", "Newsletter Draft", "Sources",
    ]
    NAV_LABELS = {
        "Triage": "Step 1: Triage",
        "Select Categories": "Step 2: Categorise",
        "Newsletter Draft": "Step 3: Draft Newsletter",
        "Sources": "Sources",
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
                    if expected and hmac.compare_digest(str(pwd), str(expected)):
                        st.session_state.authenticated = True
                        st.rerun()
                    else:
                        st.error("Wrong password" if pwd else "Enter a password")

    st.markdown("---")

    # ── Read-only notice ─────────────────────────────────────────────────────
    # The action buttons (triage / categorise / draft) are disabled until the
    # curator logs in (top-right), but they "look ready to go" — Rachel opened the
    # dashboard and the in/out buttons did nothing without her realising why
    # (2026-06). Make the gate explicit.
    if not st.session_state.get("authenticated"):
        st.info(
            "🔒 **Read-only mode.** Log in (top-right) to triage, categorise, "
            "or edit articles — the action buttons stay disabled until you do."
        )

    # ── Pipeline status banner ───────────────────────────────────────────────
    # The dashboard only shows classified articles, so anything scraped-but-not-
    # yet-processed is invisible below. Warn the curator instead of letting it
    # look like "nothing happened this week".
    _status = week_processing_status()
    if _status and not _status.get("ok"):
        _pending = _status.get("unclassified", 0) + _status.get("blank_summary", 0)
        _blank_summaries = _status.get("blank_summary", 0)
        st.warning(
            f"⚠️ **{_pending} article(s) from this week are still being processed** "
            "(not yet categorised or summarised) and aren't shown below yet. This "
            "normally clears within a few minutes of the morning update. If it's "
            "still here later, the pipeline may need attention."
        )
        if _blank_summaries and st.session_state.get("authenticated"):
            if st.button(
                "Generate missing summaries",
                key="_generate_missing_summaries",
                type="primary",
            ):
                with st.spinner("Generating summaries..."):
                    result = generate_missing_article_summaries()
                if result.get("fail"):
                    st.error(
                        f"Generated {result.get('ok', 0)} summary/s; "
                        f"{result.get('fail', 0)} failed."
                    )
                else:
                    st.toast(f"Generated {result.get('ok', 0)} summary/s.")
                st.rerun()

    page = st.session_state.current_page

    df = load_classified_articles()

    if df.empty:
        st.error("No classified articles found in Supabase. Run the inference pipeline (s07 → classify_via_api → s10) to populate `classify_newsletter`.")
        st.stop()

    if "article_date" in df.columns:
        # article_date from Supabase is ISO (YYYY-MM-DD). Parsing ISO with
        # dayfirst=True mangles it (2026-06-11 -> 6 Nov) on recent pandas, which
        # broke the week filters. Parse ISO directly, then format for display.
        df["article_date"] = pd.to_datetime(df["article_date"], errors="coerce").dt.strftime("%d-%m-%Y")

    init_session_state()

    if page == "Triage":
        triage.render(df)
    elif page == "Select Categories":
        select_categories.render(df)
    elif page == "Newsletter Draft":
        draft.render(df)
    elif page == "Sources":
        sources.render(df)

    # ── Feedback on dashboard (every page) ──────────────────────────────────
    auth = bool(st.session_state.get("authenticated"))
    st.markdown("---")
    if page == "Sources":
        st.markdown("### 💬 Feedback on sources")
        _feedback_placeholder = ("e.g. \"We're missing source X\" / \"Source Y has "
                                 "stopped appearing\" / \"Can we add Z?\"")
    else:
        st.markdown("### 💬 Feedback on dashboard design & functionality")
        _feedback_placeholder = ("e.g. \"The Triage page is too slow\" / \"I can't "
                                 "find X\" / \"Why does the source filter not include Y?\"")
    feedback_text = st.text_area(
        "Feedback",
        key="_feedback_box",
        height=110,
        placeholder=_feedback_placeholder,
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
