"""
Instructions page — merged into About 2026-05-17. Kept as a redirect for any
hardcoded nav links that still reference it.
"""

import streamlit as st

from dashboard.pages import about


def render():
    # Forward to the combined About page
    about.render()
