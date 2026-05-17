import streamlit as st
from ..config import CATEGORY_LABELS


def render():
    st.title("Add Article")
    st.markdown("Articles from 5 automated sources (Schools Week, DfE, EPI, FFT Education Datalab, FED) are scraped, classified and loaded into the **Review Articles** page each week. Use this page to manually add any additional articles the pipeline may have missed, for example from sources not yet in the feed, or articles shared directly by colleagues. Added articles will appear on the Review page with a **MANUALLY ADDED** badge. See the **Sources** page for the full list.")

    with st.form("add_article_form", clear_on_submit=True):
        title = st.text_input("Article title *")
        source = st.text_input("Source (e.g. Schools Week, GOV.UK, TES)")
        date = st.date_input("Publication date")
        url = st.text_input("Link (URL)")
        description = st.text_area("Short description", max_chars=500)

        st.markdown("**Suggest two categories:**")
        cat_options = list(CATEGORY_LABELS.keys())
        cat_format = lambda x: CATEGORY_LABELS.get(x, x)
        col1, col2 = st.columns(2)
        with col1:
            cat1 = st.selectbox("Category 1", cat_options, format_func=cat_format, key="add_cat1")
        with col2:
            cat2 = st.selectbox("Category 2", cat_options, format_func=cat_format, key="add_cat2", index=1)

        submitted = st.form_submit_button("Add article", use_container_width=True)

        if submitted:
            if not title:
                st.error("Title is required.")
            else:
                article = {
                    "title": title,
                    "source": source,
                    "article_date": date.strftime("%d-%m-%Y"),
                    "url": url,
                    "text_clean": description,
                    "text_preview": description[:100] if description else "",
                    "top1": cat1,
                    "top1_confidence": 1.0,
                    "top2": cat2,
                    "top2_confidence": 0.0,
                    "confidence_gap": 1.0,
                    "week_number": None,
                    "curator_added": True,
                }
                st.session_state.curator_articles.append(article)
                st.success(f"Added: **{title}** \u2192 {CATEGORY_LABELS[cat1]} / {CATEGORY_LABELS[cat2]}")

    if st.session_state.curator_articles:
        st.subheader(f"Curator-added articles ({len(st.session_state.curator_articles)})")
        for i, art in enumerate(st.session_state.curator_articles):
            st.markdown(f"**{art['title']}** \u00b7 {art['source']} \u00b7 {art['article_date']} \u2192 {CATEGORY_LABELS.get(art['top1'], art['top1'])}")
