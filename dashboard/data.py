"""
Data loading and session state helpers.
"""

import json
import streamlit as st
import pandas as pd
from .config import DATA_DIR


@st.cache_data(ttl=300)
def load_classified_articles():
    """Load classified articles from local CSV."""
    csv_path = DATA_DIR / "classified_articles.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        if "week_number" not in df.columns or df["week_number"].isna().all():
            df["week_number"] = pd.to_datetime(df["article_date"], errors="coerce").dt.isocalendar().week
        return df
    return pd.DataFrame()


def init_session_state():
    """Initialise curator decisions and manually added articles."""
    if "decisions" not in st.session_state:
        decisions_path = DATA_DIR / "curator_decisions.json"
        if decisions_path.exists():
            with open(decisions_path) as f:
                st.session_state.decisions = json.load(f)
        else:
            st.session_state.decisions = {}

    if "curator_articles" not in st.session_state:
        curator_csv = DATA_DIR / "curator_added_articles.csv"
        if curator_csv.exists():
            st.session_state.curator_articles = pd.read_csv(curator_csv).to_dict("records")
        else:
            st.session_state.curator_articles = []


def save_decisions():
    """Persist decisions to local JSON file."""
    with open(DATA_DIR / "curator_decisions.json", "w") as f:
        json.dump(st.session_state.decisions, f)


def get_accepted_articles(df):
    """Build list of accepted articles from decisions + curator-added articles."""
    accepted = []
    for url, dec in st.session_state.decisions.items():
        if dec["action"] == "reject":
            continue
        match = df[df["url"] == url]
        if len(match) > 0:
            row = match.iloc[0].to_dict()
        else:
            row = {"url": url, "title": "Unknown"}
        row["curator_label"] = dec["label"]
        if url in st.session_state.get("category_overrides", {}):
            row["curator_label"] = st.session_state.category_overrides[url]
        accepted.append(row)

    for art in st.session_state.curator_articles:
        art_copy = art.copy()
        art_copy["curator_label"] = art["top1"]
        art_copy["curator_added"] = True
        if art.get("url") in st.session_state.get("category_overrides", {}):
            art_copy["curator_label"] = st.session_state.category_overrides[art["url"]]
        accepted.append(art_copy)

    return accepted
