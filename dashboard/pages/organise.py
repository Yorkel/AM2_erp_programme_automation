from io import BytesIO
from datetime import datetime

import streamlit as st
import pandas as pd

from ..config import CATEGORY_LABELS, CATEGORY_ORDER, SOURCE_LABELS
from ..data import get_accepted_articles


def render(df):
    st.title("Organise Newsletter")
    st.markdown("Shortlisted articles grouped by selected newsletter category for further review. Select up to **3 per category** for the newsletter. Use **Move to** to reassign an article to a different category.")

    if "newsletter_picks" not in st.session_state:
        st.session_state.newsletter_picks = set()
    if "category_overrides" not in st.session_state:
        st.session_state.category_overrides = {}

    accepted = get_accepted_articles(df)

    if not accepted:
        st.warning("No accepted articles yet. Go to **Review Articles** and accept some articles first.")
        return

    n_picked = len(st.session_state.newsletter_picks)
    st.info(f"**{len(accepted)} accepted articles** | **{n_picked} selected for newsletter**")

    for cat_key in CATEGORY_ORDER:
        cat_label = CATEGORY_LABELS[cat_key]
        cat_articles = [a for a in accepted if a.get("curator_label") == cat_key]

        if not cat_articles:
            continue

        n_selected = sum(1 for a in cat_articles if a.get("url") in st.session_state.newsletter_picks)
        st.subheader(f"{cat_label} ({len(cat_articles)} articles, {n_selected} selected)")

        for art in cat_articles:
            art_url = art.get("url", "")
            is_picked = art_url in st.session_state.newsletter_picks
            is_curator = art.get("curator_added", False)
            badge = " <span style='background:#f39c12;color:white;padding:2px 6px;border-radius:3px;font-size:10px;'>CURATOR</span>" if is_curator else ""
            pick_badge = " <span style='background:#27ae60;color:white;padding:2px 6px;border-radius:3px;font-size:10px;'>SELECTED</span>" if is_picked else ""

            with st.container(border=True):
                left, btn_col, move_col = st.columns([3, 1, 1])
                with left:
                    st.markdown(f"**Article title:** {art.get('title', 'No title')}{badge}{pick_badge}", unsafe_allow_html=True)
                    source_name = SOURCE_LABELS.get(art.get('source', ''), art.get('source', ''))
                    st.markdown(f"**Article source:** {source_name}  |  **Date:** {art.get('article_date', '')}")
                with btn_col:
                    if is_picked:
                        if st.button("Remove", key=f"unpick_{art_url}", use_container_width=True):
                            st.session_state.newsletter_picks.discard(art_url)
                            st.rerun()
                    else:
                        if n_selected >= 3:
                            st.button("Select (max 3)", key=f"pick_{art_url}", use_container_width=True, disabled=True)
                        else:
                            if st.button("Select", key=f"pick_{art_url}", use_container_width=True):
                                st.session_state.newsletter_picks.add(art_url)
                                st.rerun()
                with move_col:
                    other_cats = [k for k in CATEGORY_LABELS if k != cat_key]
                    move_to = st.selectbox(
                        "Move to",
                        [""] + other_cats,
                        format_func=lambda x: "Move to..." if x == "" else CATEGORY_LABELS.get(x, x),
                        key=f"move_{art_url}",
                        label_visibility="collapsed",
                    )
                    if move_to:
                        st.session_state.category_overrides[art_url] = move_to
                        st.rerun()

    # Export
    st.markdown("")
    newsletter_articles = [a for a in accepted if a.get("url") in st.session_state.newsletter_picks]
    if newsletter_articles:
        st.markdown(f"**Newsletter selections: {len(newsletter_articles)} articles**")

        newsletter_df = pd.DataFrame(newsletter_articles)[["title", "curator_label", "url"]].copy()
        newsletter_df["curator_label"] = newsletter_df["curator_label"].map(lambda x: CATEGORY_LABELS.get(x, x))

        buffer_nl = BytesIO()
        newsletter_df.to_excel(buffer_nl, index=False, engine="openpyxl")
        buffer_nl.seek(0)

        st.download_button(
            "Download newsletter selections",
            buffer_nl,
            file_name=f"newsletter_selections_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
