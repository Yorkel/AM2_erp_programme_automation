import streamlit as st
from ..config import CATEGORY_LABELS, CATEGORY_ORDER


def render():
    st.title("ESRC Education Research Programme Newsletter")
    st.markdown("This dashboard supports the curation of the programme's weekly newsletter. It uses a classification model to automatically read each article and suggest the top two most likely newsletter categories, so curators can quickly review and confirm rather than sorting from scratch.")

    st.markdown("")

    st.subheader("How it works")
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("**1. Collect**")
            st.markdown("Articles are pulled weekly from source feeds and classified by the model. Curators can also manually add articles the pipeline missed.")
        with st.container(border=True):
            st.markdown("**3. Organise**")
            st.markdown("Accepted articles are grouped by category. Select the top articles for the newsletter and move articles between categories if needed.")
    with col2:
        with st.container(border=True):
            st.markdown("**2. Review**")
            st.markdown("Each article receives two category suggestions with confidence scores. Accept the correct category or reject irrelevant items.")
        with st.container(border=True):
            st.markdown("**4. Publish**")
            st.markdown("Write descriptions for selected articles and download the newsletter draft as plain text.")

    st.markdown("")

    st.subheader("Newsletter categories")
    category_descriptions = {
        "teacher_rrd": "Teacher recruitment, retention, development, training, pay, workload, or the teaching profession.",
        "edtech": "Educational technology, AI in education, digital tools for learning, and technology policy in schools.",
        "political_environment_key_organisations": "News and announcements from key political and policy organisations (DfE, Ofsted, parliamentary committees, think tanks).",
        "four_nations": "Education in Scotland, Wales, or Northern Ireland, or devolved education policy.",
        "policy_practice_research": "Research reports, academic studies, evidence reviews, and practice-focused publications about education.",
        "what_matters_ed": "Broader education issues that matter to children and families: SEND, attendance, mental health, disadvantage, pupil welfare, poverty.",
    }

    cols = st.columns(3)
    for i, key in enumerate(CATEGORY_ORDER):
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"**{CATEGORY_LABELS[key]}**")
                st.caption(category_descriptions[key])

    st.markdown("")

    st.subheader("Dashboard pages")
    pages_info = [
        ("Instructions", "Step-by-step guide on how to use the dashboard."),
        ("Add Article", "Manually add articles the pipeline missed, with your own category suggestions."),
        ("Review Articles", "Review each article's two suggested categories. Accept the correct one or reject irrelevant items."),
        ("Organise", "Shortlisted articles grouped by selected newsletter category for further review."),
        ("Newsletter Draft", "Preview the final newsletter. Write descriptions and download as plain text."),
        ("Sources", "All sources monitored for the newsletter, with links and automation status."),
        ("Feedback", "Rate classification accuracy, flag problem categories, suggest missing sources."),
    ]
    for name, desc in pages_info:
        st.markdown(f"**{name}:** {desc}")

    st.markdown("")
    st.caption("The classification model reads article content and suggests the two most likely categories. The correct category appears in the top two suggestions about 90% of the time.")
