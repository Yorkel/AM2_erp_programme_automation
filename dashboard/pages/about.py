"""
About + Instructions — combined into one page.

Replaces the previous two-page structure (about.py + instructions.py).
The Instructions page module still exists as a thin redirect for back-compat.
"""

import streamlit as st

from dashboard.config import CATEGORY_LABELS, CATEGORY_ORDER


def render():
    st.title("About this dashboard")

    st.warning(
        "⚠ **Content currently out of date — requires update as of 18 May 2026.** "
        "Some descriptions below may not reflect recent changes to the pipeline or filters."
    )

    st.markdown(
        "This dashboard supports the curation of the ESRC Education Research "
        "Programme's weekly newsletter. A classification model reads each scraped "
        "article and suggests the two most likely newsletter categories so curators "
        "can review and confirm rather than sort from scratch."
    )

    # ── How it works ────────────────────────────────────────────────────────
    st.subheader("How it works")
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("**1. Collect**")
            st.markdown(
                "Articles are pulled twice-weekly from 100+ source feeds and "
                "classified by the model. Curators can also manually add articles "
                "the pipeline missed."
            )
        with st.container(border=True):
            st.markdown("**3. Organise**")
            st.markdown(
                "Accepted articles are grouped by category. Select your top picks "
                "(2–4 per section) and move articles between categories if needed."
            )
    with col2:
        with st.container(border=True):
            st.markdown("**2. Review**")
            st.markdown(
                "Each article shows two category suggestions with confidence scores. "
                "Accept the correct one, pick a different category manually, or reject."
            )
        with st.container(border=True):
            st.markdown("**4. Publish**")
            st.markdown(
                "Generate AI summaries for each picked article (one click), edit if "
                "needed, and download the newsletter draft as plain text."
            )

    # ── Categories ──────────────────────────────────────────────────────────
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
                st.caption(category_descriptions.get(key, ""))

    # ── Weekly workflow ─────────────────────────────────────────────────────
    st.subheader("Weekly workflow")
    st.markdown("""
**Step 1 — Review Articles.** Open the **Review Articles** page and select the current week. For each article you have four options:

- **Category 1** (blue) accepts the model's top suggestion
- **Category 2** accepts the second suggestion
- **Manual selection** lets you pick any of the six sections from a dropdown
- **Reject** removes the article from the newsletter

The correct section appears in the model's top two suggestions about **87%** of the time, so most articles only need a single click.

**Step 2 — Add any missing articles.** Use the **Add Article** page if the pipeline missed something (e.g. an article shared by a colleague).

**Step 3 — Organise.** The **Organise** page shows shortlisted articles grouped by selected category. Pick your top 2–4 per section. You can move an article to a different section.

**Step 4 — Newsletter Draft.** Click **Generate summary** on each article for a Claude-written 1–2 sentence summary (you can edit it). Download the full draft as plain text.

**Step 5 — Feedback.** Use the **Feedback** page to flag problem categories, suggest missing sources, or share other observations. Your input refines the model.

**Reviewing offline.** Several pages have a download button so you can export articles as Excel and review them outside the dashboard.
""")

    # ── Tips ────────────────────────────────────────────────────────────────
    st.subheader("Tips")
    st.markdown("""
- **Low confidence scores** (below 40%) usually mean the article fits two sections equally well. Check both suggestions before deciding.
- **You can change your mind.** Click a different button on the same article to update the decision. The latest click wins.
- **Decisions persist.** All accept/reject/manual choices are saved to Supabase and survive page reloads / new sessions.
- **Check the Sources page** to see the full source roster and suggest new ones.
""")

    st.markdown("")
    st.caption("Predictions come from the v1_2026-05-16 classifier (sentence-transformer + sklearn). Real-world top-2 accuracy: ~87%.")
