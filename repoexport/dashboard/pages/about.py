"""
About page — describe what this newsletter is, who it's for, and how to use it.

TEMPLATE: replace the placeholder copy below with your topic-specific blurb,
contact details, and (optional) link to a project page or GitHub repo.
"""

import streamlit as st


def render():
    st.title("About")

    st.markdown(
        """
        ## What this is

        A weekly newsletter pipeline for **[YOUR TOPIC HERE]**.
        Articles are scraped from a curated list of sources, then triaged by
        curators in this dashboard before being published.

        ## How to use this dashboard

        - **Overview** — high-level pipeline metrics (article volume, sources, trends).
        - **Review Articles** — accept, reject, or save articles for the next newsletter.
        - **Organise** — group accepted articles into newsletter sections.
        - **Newsletter Draft** — preview and export the final newsletter.
        - **Add Article** — manually add an article you've found yourself.
        - **Feedback** — submit feedback or suggest new sources.

        ## Contact

        TODO — add a contact email or Slack channel.
        """
    )
