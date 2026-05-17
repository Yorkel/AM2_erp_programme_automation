from datetime import datetime

import streamlit as st

from ..config import CATEGORY_LABELS, CATEGORY_ORDER, SOURCE_LABELS
from ..data import get_accepted_articles


def render(df):
    st.title("Newsletter Draft")
    st.markdown("Preview and download the newsletter as plain text. Edit descriptions inline before downloading.")

    accepted = get_accepted_articles(df)
    picks = st.session_state.get("newsletter_picks", set())
    newsletter_articles = [a for a in accepted if a.get("url") in picks]

    if not newsletter_articles:
        st.warning("No articles selected for the newsletter. Go to **Organise** and select articles first.")
        return

    today = datetime.now()
    newsletter_date = today.strftime("%d %B %Y")

    if "draft_descriptions" not in st.session_state:
        st.session_state.draft_descriptions = {}

    # Header
    st.markdown(f"""
    <div style="background:#0f1e3d;color:white;padding:20px;border-radius:8px;text-align:center;margin-bottom:20px;">
        <div style="font-size:18px;font-weight:700;">ESRC Education Research Programme</div>
        <div style="font-size:14px;color:#8fa8c8;margin-top:4px;">ERP Newsletter</div>
        <div style="font-size:14px;color:#8fa8c8;">{newsletter_date}</div>
    </div>
    """, unsafe_allow_html=True)

    plain_text = f"ERP Newsletter\n{newsletter_date}\n\n"

    for cat_key in CATEGORY_ORDER:
        cat_articles = [a for a in newsletter_articles if a.get("curator_label") == cat_key]
        if not cat_articles:
            continue

        cat_label = CATEGORY_LABELS[cat_key]

        st.markdown(
            f"<div style='background:#1d3461;padding:10px 16px;border-radius:4px;margin:16px 0 8px 0;'>"
            f"<span style='color:#c8d8ec;font-size:15px;font-weight:600;'>{cat_label}</span></div>",
            unsafe_allow_html=True,
        )
        plain_text += f"\n{cat_label}\n\n"

        for art in cat_articles:
            art_url = art.get("url", "")
            title = art.get("title", "No title")
            source_name = SOURCE_LABELS.get(art.get("source", ""), art.get("source", ""))

            desc_key = f"desc_{art_url}"
            if desc_key not in st.session_state.draft_descriptions:
                st.session_state.draft_descriptions[desc_key] = ""

            with st.container(border=True):
                st.markdown(f"**{source_name} - {title}**")
                edited_desc = st.text_area(
                    "Description",
                    value=st.session_state.draft_descriptions[desc_key],
                    key=desc_key,
                    height=80,
                    label_visibility="collapsed",
                )
                st.session_state.draft_descriptions[desc_key] = edited_desc
                if art_url:
                    st.markdown(f"[Here]({art_url})")

            plain_text += f"{source_name} - {title}\n"
            plain_text += f"{st.session_state.draft_descriptions[desc_key]}\n"
            if art_url:
                plain_text += f"Here: {art_url}\n"
            plain_text += "\n"

    plain_text += "\n---\n"
    plain_text += "You have indicated that you are happy to receive news and updates from the ESRC Education Research Programme. "
    plain_text += "To unsubscribe, please email nina.charalambous.15@ucl.ac.uk with the word UNSUBSCRIBE in the title of the email.\n"
    plain_text += "Do you find this newsletter useful? Are you happy with its frequency? Which section do you find most useful? "
    plain_text += "Any pressing topics we haven't covered? Any good sources of information you think we're missing? "
    plain_text += "How could we improve? We advocate for listening to different stakeholders and so we want your views too!\n"

    st.markdown("")

    st.download_button(
        "Download newsletter draft (plain text)",
        plain_text,
        file_name=f"newsletter_draft_{today.strftime('%Y%m%d')}.txt",
        mime="text/plain",
        use_container_width=True,
    )
