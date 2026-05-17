from datetime import datetime

import streamlit as st
import pandas as pd

from ..config import CATEGORY_LABELS, CATEGORY_ORDER, DATA_DIR


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
            feedback_entry = {
                "timestamp": datetime.now().isoformat(),
                "accuracy_rating": accuracy_rating,
                "problem_categories": ", ".join(problem_cats) if problem_cats else "",
                "missing_sources": missing_sources,
                "suggestions": suggestions,
            }
            feedback_path = DATA_DIR / "curator_feedback.csv"
            feedback_df = pd.DataFrame([feedback_entry])
            if feedback_path.exists():
                existing = pd.read_csv(feedback_path)
                feedback_df = pd.concat([existing, feedback_df], ignore_index=True)
            feedback_df.to_csv(feedback_path, index=False)
            st.success("Thank you! Your feedback has been saved.")
