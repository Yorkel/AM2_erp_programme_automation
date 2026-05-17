from datetime import datetime

import streamlit as st

from dashboard.config import CATEGORY_LABELS, CATEGORY_ORDER
from dashboard.data import get_client


def render():
    st.title("Feedback")
    st.markdown("Help us improve the newsletter classification tool. Your feedback is used to refine the model and improve the curator experience.")

    with st.form("feedback_form", clear_on_submit=True):
        st.markdown("**How accurate were this week's classifications?**")
        accuracy_rating = st.select_slider(
            "Overall accuracy",
            options=["Very poor", "Poor", "OK", "Good", "Excellent"],
            value="OK",
        )

        st.markdown("**Were any categories consistently wrong?**")
        problem_cats = st.multiselect(
            "Select any categories that had frequent errors",
            options=CATEGORY_ORDER,
            format_func=lambda x: CATEGORY_LABELS.get(x, x),
        )

        st.markdown("**Are we missing any sources?**")
        missing_sources = st.text_area(
            "List any sources you think should be included in the pipeline",
            placeholder="e.g. NFER blog, Sutton Trust reports, a specific journal...",
            height=80,
        )

        st.markdown("**Any other suggestions?**")
        suggestions = st.text_area(
            "General feedback, feature requests, or comments",
            placeholder="e.g. categories need redefining, too many irrelevant articles, confidence scores not helpful...",
            height=100,
        )

        submitted = st.form_submit_button("Submit feedback", use_container_width=True)

        if submitted:
            # Persist to Supabase `curator_feedback` table (migration 008 pending).
            # If the table doesn't exist yet, falls back to printing the message.
            try:
                client = get_client()
                client.table("curator_feedback").insert({
                    "submitted_at": datetime.now().isoformat(),
                    "accuracy_rating": accuracy_rating,
                    "problem_categories": problem_cats or [],
                    "missing_sources": missing_sources,
                    "suggestions": suggestions,
                }).execute()
                st.success("Thank you! Your feedback has been saved.")
            except Exception as e:
                st.warning(f"Feedback table not yet wired in Supabase ({e}). The text was: {suggestions[:200]}")
