import streamlit as st


def render():
    st.title("How to Use This Dashboard")

    st.markdown("Follow these steps each week to review, organise and compile the newsletter.")

    st.subheader("Weekly workflow")

    st.markdown("""
**Step 1: Review Articles**

Go to the **Review Articles** page and select the current week. For each article you have four options:

- **Category 1** (blue button) accepts the model's top suggestion
- **Category 2** (orange button) accepts the second suggestion
- **Manual selection** lets you pick any of the six sections from a dropdown
- **Reject** removes the article from the newsletter

The correct section appears in the model's top two suggestions about **90%** of the time, so most articles only need a single click.

You can review articles across multiple weeks. All accepted articles flow into the Organise page together.

**Step 2: Add any missing articles**

Go to **Add Article** to manually add articles the pipeline missed, for example from sources not yet in the automated feed or articles shared by colleagues. These appear in Review with a "MANUALLY ADDED" badge.

**Step 3: Organise**

The **Organise** page shows your shortlisted articles grouped into their selected newsletter categories for further review. Here you can:

- Select your top picks (aim for 2 to 4 per section)
- Move articles between sections if needed

**Step 4: Newsletter Draft**

The **Newsletter Draft** page generates a structured draft grouped by section. Write descriptions for each article and download as plain text for the final email.

**Step 5: Feedback**

Use the **Feedback** page to let us know how the tool is performing. Flag problem categories, suggest missing sources, or share any other observations. Your feedback directly improves the model.

**Prefer to review offline?**

Several pages include a download button so you can export articles as an Excel file and review them outside the dashboard. You can download the week's articles from the Review Articles page, your decisions from the Organise page, and the final draft from the Newsletter Draft page.
""")

    st.subheader("Tips")

    st.markdown("""
- **Low confidence scores** (below 40%) usually mean the article fits two sections equally well. Check both suggestions before deciding.
- **The model over-predicts "Teacher recruitment, retention & development"**. If you see an article about a government announcement that mentions teachers, it may belong in "Political environment" instead. This is a known issue we are working on.
- **You can change your mind.** Click a different button on the same article to update your decision.
- **Check the Sources page** to see which feeds are automated and which are under review for inclusion.
""")

    st.markdown("")
    st.markdown("Please use the **Feedback** page for suggestions and ways to improve the tool.")
