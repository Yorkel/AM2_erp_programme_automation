"""
AM2 Newsletter Curator Dashboard
Streamlit app for reviewing classified articles and monitoring model performance.

Run: streamlit run dashboard/app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# -----------------------------
# CONFIG
# -----------------------------
DATA_DIR = Path("data/modelling")
MODEL_DIR = Path("models")

CATEGORY_LABELS = {
    "teacher_rrd": "Teacher recruitment, retention & development",
    "edtech": "EdTech",
    "political_environment_key_organisations": "Political environment and key organisations",
    "four_nations": "Four Nations",
    "policy_practice_research": "Research – Practice – Policy",
    "what_matters_ed": "What matters in education?",
}

# Display order for the newsletter
CATEGORY_ORDER = [
    "teacher_rrd",
    "edtech",
    "political_environment_key_organisations",
    "four_nations",
    "policy_practice_research",
    "what_matters_ed",
]

CATEGORY_COLORS = {
    "edtech": "#5b9bd5",
    "four_nations": "#70ad47",
    "policy_practice_research": "#7b7fb5",
    "political_environment_key_organisations": "#4472c4",
    "teacher_rrd": "#ed7d31",
    "what_matters_ed": "#44b4a6",
}

SOURCE_LABELS = {
    "schoolsweek": "Schools Week",
    "gov": "GOV.UK",
    "fft": "FFT Education Datalab",
    "fed": "Further Education Development",
    "epi": "Education Policy Institute",
    "tes": "TES",
    "nfer": "National Foundation for Educational Research",
    "ofsted": "Ofsted",
    "sutton_trust": "Sutton Trust",
    "bbc": "BBC",
    "guardian": "The Guardian",
}

# ESRC brand colours
NAVY = "#0f1e3d"
TEAL = "#44b4a6"
LIGHT_BLUE = "#5b9bd5"
MID_BLUE = "#1d3461"


# -----------------------------
# DATA LOADING
# -----------------------------
@st.cache_data(ttl=300)
def load_classified_articles():
    """Load classified articles from local CSV or Supabase."""
    csv_path = DATA_DIR / "classified_articles.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path)
    return pd.DataFrame()


@st.cache_data
def load_monitoring_log():
    """Load monitoring log."""
    log_path = DATA_DIR / "monitoring_log.csv"
    if log_path.exists():
        return pd.read_csv(log_path)
    return pd.DataFrame()


@st.cache_data
def load_val_results():
    """Load val predictions for baseline comparison."""
    val_path = DATA_DIR / "val_predictions.csv"
    if val_path.exists():
        return pd.read_csv(val_path)
    return pd.DataFrame()


# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="ESRC ERP Newsletter",
    page_icon="📰",
    layout="wide",
)

# Custom CSS — ESRC brand colours
st.markdown(f"""
<style>
    /* Sidebar */
    [data-testid="stSidebar"] {{
        background-color: {NAVY};
    }}
    [data-testid="stSidebar"] * {{
        color: white !important;
    }}
    [data-testid="stSidebar"] .stRadio label {{
        color: #c8d8ec !important;
    }}
    [data-testid="stSidebar"] .stRadio label:hover {{
        color: {TEAL} !important;
    }}

    /* Headers */
    h1 {{
        color: {NAVY} !important;
    }}
    h2, h3 {{
        color: {MID_BLUE} !important;
    }}

    /* Primary buttons */
    .stButton > button[kind="primary"] {{
        background-color: {TEAL};
        border-color: {TEAL};
    }}
    .stButton > button[kind="primary"]:hover {{
        background-color: #389e93;
        border-color: #389e93;
    }}

    /* Info boxes */
    .stAlert {{
        background-color: #e8f4f8;
        border-left-color: {TEAL};
    }}

    /* Progress bar */
    .stProgress > div > div > div {{
        background-color: {TEAL};
    }}

    /* Dividers */
    hr {{
        border-color: #dde3ed;
    }}

    /* Hide anchor link icons on headers */
    h1 a, h2 a, h3 a {{
        display: none !important;
    }}

    /* Card containers — light background */
    [data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: #f8f9fb !important;
        border-radius: 8px !important;
    }}

    /* Download button — light orange */
    [data-testid="stDownloadButton"] button {{
        background-color: #ffecd2 !important;
        color: #856404 !important;
        border: 1px solid #f0c36d !important;
    }}
    [data-testid="stDownloadButton"] button:hover {{
        background-color: #ffe0b2 !important;
    }}

    /* All buttons — same height, larger text */
    [data-testid="stButton"] button {{
        min-height: 50px !important;
        font-size: 16px !important;
    }}

    /* Primary buttons — light blue (Category 1) */
    [data-testid="stButton"] button[kind="primary"] {{
        background-color: #d6e4f0 !important;
        border-color: #4472c4 !important;
        color: #2c5aa0 !important;
    }}
    [data-testid="stButton"] button[kind="primary"]:hover {{
        background-color: #b8cfe2 !important;
        color: #2c5aa0 !important;
    }}

    /* Secondary buttons — light red (Reject) */
    [data-testid="stButton"] button[kind="secondary"] {{
        background-color: #fadbd8 !important;
        border-color: #e74c3c !important;
        color: #c0392b !important;
    }}
    [data-testid="stButton"] button[kind="secondary"]:hover {{
        background-color: #f1948a !important;
        color: white !important;
    }}

    /* Tertiary buttons — light orange (Category 2) */
    [data-testid="stButton"] button[kind="tertiary"] {{
        background-color: #fde8d0 !important;
        border-color: #ed7d31 !important;
        color: #c46516 !important;
        border: 1px solid #ed7d31 !important;
    }}
    [data-testid="stButton"] button[kind="tertiary"]:hover {{
        background-color: #f9d4ae !important;
        color: #c46516 !important;
    }}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# SIDEBAR
# -----------------------------
_logo_path = Path(__file__).parent / "Screenshot 2026-04-05 at 21.14.48.png"
if _logo_path.exists():
    st.sidebar.image(str(_logo_path), use_container_width=True)
st.sidebar.title("Newsletter Curator")

page = st.sidebar.radio(
    "Navigate",
    ["About", "Add Article", "Review Articles", "Organise", "Newsletter Draft", "Sources", "Feedback"],
)

# Load data
df = load_classified_articles()

if df.empty and page not in ["About", "Sources"]:
    st.error("No classified articles found. Run `python src/pipeline.py --inference` first.")
    st.stop()

# Format dates as dd-mm-yyyy
if "article_date" in df.columns:
    df["article_date"] = pd.to_datetime(df["article_date"], errors="coerce").dt.strftime("%d-%m-%Y")

# -----------------------------
# SESSION STATE: track curator decisions
# -----------------------------
if "decisions" not in st.session_state:
    # Load from CSV if exists
    decisions_csv = DATA_DIR / "curator_decisions.json"
    if decisions_csv.exists():
        import json as _json
        with open(decisions_csv) as f:
            st.session_state.decisions = _json.load(f)
    else:
        st.session_state.decisions = {}
def _save_decisions():
    """Persist decisions to local JSON file."""
    import json as _json
    with open(DATA_DIR / "curator_decisions.json", "w") as f:
        _json.dump(st.session_state.decisions, f)

if "curator_articles" not in st.session_state:
    # Load from CSV if exists, otherwise empty
    curator_csv = DATA_DIR / "curator_added_articles.csv"
    if curator_csv.exists():
        st.session_state.curator_articles = pd.read_csv(curator_csv).to_dict("records")
    else:
        st.session_state.curator_articles = []


# -----------------------------
# PAGE: REVIEW ARTICLES
# -----------------------------
# Banner on every page
st.markdown(
    "<div style='background:#fff3cd;border:1px solid #ffc107;border-radius:5px;padding:12px 16px;margin-bottom:16px;font-size:13px;color:#856404;text-align:center;'>"
    "This is a prototype dashboard. The production version will be private to the programme curators.</div>",
    unsafe_allow_html=True,
)

if page == "About":
    st.title("ESRC Education Research Programme Newsletter")
    st.markdown("This dashboard supports the curation of the programme's weekly newsletter. It uses a classification model to automatically read each article and suggest the top two most likely newsletter categories, so curators can quickly review and confirm rather than sorting from scratch.")

    st.markdown("")

    # How it works
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

    # Categories
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

    # Dashboard pages
    st.subheader("Dashboard pages")
    pages_info = [
        ("Add Article", "Manually add articles the pipeline missed, with your own category suggestions."),
        ("Review Articles", "Review each article's two suggested categories. Accept the correct one or reject irrelevant items."),
        ("Organise", "Accepted articles grouped by category. Select the top articles and move between categories if needed."),
        ("Newsletter Draft", "Preview the final newsletter. Write descriptions and download as plain text."),
        ("Sources", "All sources monitored for the newsletter, with links and automation status."),
        ("Feedback", "Rate classification accuracy, flag problem categories, suggest missing sources."),
    ]
    for name, desc in pages_info:
        st.markdown(f"**{name}:** {desc}")

    st.markdown("")

    st.caption("The classification model reads article content and suggests the two most likely categories. It gets the correct category in its top two suggestions for roughly 9 out of 10 articles.")

elif page == "Review Articles":
    st.title("Review Articles")
    st.markdown("Review each article's classification. The model suggests two possible categories. **Accept** the correct one or **reject** if neither fits. Rejected articles won't appear in the newsletter draft.")

    # Week selector + article count in one card
    weeks = sorted(df["week_number"].dropna().unique().astype(int).tolist(), reverse=True)
    with st.container(border=True):
        col_week, col_count = st.columns([1, 2])
        with col_week:
            selected_week = st.selectbox("Select week", weeks, index=0)

        filtered = df[df["week_number"] == selected_week].copy()

        # Add curator-submitted articles (they appear in all weeks)
        if st.session_state.curator_articles:
            curator_df = pd.DataFrame(st.session_state.curator_articles)
            curator_df["curator_added"] = True
            if "curator_added" not in filtered.columns:
                filtered["curator_added"] = False
            filtered = pd.concat([filtered, curator_df], ignore_index=True)

        n_curator = filtered["curator_added"].sum() if "curator_added" in filtered.columns else 0
        with col_count:
            st.markdown("<br>", unsafe_allow_html=True)
            st.info(f"**Week {selected_week}:** {len(filtered)} articles to review" + (f" ({n_curator} added by curator)" if n_curator else ""))

    # Download for manual review (centred)
    review_cols = ["title", "source", "article_date", "url", "top1", "top1_confidence", "top2", "top2_confidence"]
    available = [c for c in review_cols if c in filtered.columns]
    review_export = filtered[available].copy()
    if "top1_confidence" in review_export.columns:
        review_export["top1_confidence"] = (review_export["top1_confidence"] * 100).round(0).astype(int)
    if "top2_confidence" in review_export.columns:
        review_export["top2_confidence"] = (review_export["top2_confidence"] * 100).round(0).astype(int)

    from io import BytesIO
    buffer = BytesIO()
    review_export.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)

    st.download_button(
        f"Download week {selected_week} for manual review",
        buffer,
        file_name=f"week_{selected_week}_review.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    st.markdown("")

    # Sort + Progress side by side
    n_reviewed = sum(1 for url in filtered["url"] if url in st.session_state.decisions)
    col_sort, col_progress = st.columns(2)
    with col_sort:
        sort_by = st.selectbox("Order by", ["Date (newest first)", "Date (oldest first)", "Source"])
    with col_progress:
        st.markdown(f"**Progress:** {n_reviewed} / {len(filtered)} reviewed")
        st.progress(n_reviewed / len(filtered) if len(filtered) > 0 else 0)

    if sort_by == "Date (newest first)":
        filtered = filtered.sort_values("article_date", ascending=False, na_position="first")
    elif sort_by == "Date (oldest first)":
        filtered = filtered.sort_values("article_date", ascending=True, na_position="last")
    else:
        filtered = filtered.sort_values("source", na_position="last")

    # Article cards
    for card_idx, (idx, row) in enumerate(filtered.iterrows()):
        url = row.get("url", str(idx))
        conf1 = row["top1_confidence"]
        conf2 = row.get("top2_confidence", 0)
        cat1 = row["top1"]
        cat2 = row.get("top2", "")
        cat1_label = CATEGORY_LABELS.get(cat1, cat1)
        cat2_label = CATEGORY_LABELS.get(cat2, cat2)
        cat1_color = CATEGORY_COLORS.get(cat1, "#666")
        cat2_color = CATEGORY_COLORS.get(cat2, "#666")
        conf1_color = "#27ae60" if conf1 >= 0.6 else "#f39c12" if conf1 >= 0.4 else "#e74c3c"
        conf2_color = "#27ae60" if conf2 >= 0.6 else "#f39c12" if conf2 >= 0.4 else "#e74c3c"

        # Check if already reviewed
        decision = st.session_state.decisions.get(url)

        total_articles = len(filtered)

        # Article heading with separator
        st.markdown(f"<div style='border-top:3px solid #1d3461;margin:20px 0;'></div>", unsafe_allow_html=True)
        st.markdown(f"### Article {card_idx + 1}/{total_articles}: {row.get('title', 'No title')}")

        with st.container(border=True):
            is_curator = row.get("curator_added", False)
            badge = " <span style='background:#f39c12;color:white;padding:2px 8px;border-radius:3px;font-size:11px;font-weight:600;'>CURATOR ADDED</span>" if is_curator else ""

            # Category badges — Top 1 always blue, Top 2 always orange
            TOP1_COLOR = "#4472c4"
            TOP2_COLOR = "#ed7d31"
            cat1_badge = f"<span style='background:{TOP1_COLOR};color:white;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;'>{cat1_label}</span>"
            cat2_badge = f"<span style='background:{TOP2_COLOR};color:white;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;'>{cat2_label}</span>"
            conf1_badge = f"<span style='color:{conf1_color};font-weight:600;font-size:12px;'>{conf1:.0%}</span>"
            conf2_badge = f"<span style='color:{conf2_color};font-weight:600;font-size:12px;'>{conf2:.0%}</span>"

            # Source and date
            source_name = SOURCE_LABELS.get(row.get('source', ''), row.get('source', ''))
            link_html = f" &nbsp;<a href='{row['url']}' target='_blank' style='font-size:14px;'>Open article ↗</a>" if row.get("url") else ""
            st.markdown(f"<p style='color:#666;font-size:16px;text-align:center;'><b>Source:</b> {source_name}  &middot;  <b>Date:</b> {row.get('article_date', '')}{link_html}{badge}</p>", unsafe_allow_html=True)

            # Text preview
            if row.get("text_clean"):
                with st.expander("Click to preview text"):
                    st.write(str(row["text_clean"])[:500])

            # Action buttons with category info inside
            btn1_label = f"Category 1: {cat1_label} ({conf1:.0%})" if not is_curator else f"Category 1: {cat1_label}"
            btn2_label = f"Category 2: {cat2_label} ({conf2:.0%})" if not is_curator else f"Category 2: {cat2_label}"

            col_a, col_b, col_c, col_d = st.columns(4)
            with col_a:
                if st.button(btn1_label, key=f"acc1_{url}", use_container_width=True, type="primary"):
                    st.session_state.decisions[url] = {"action": "accept_top1", "label": cat1}
                    _save_decisions()
                    st.rerun()
            with col_b:
                if st.button(btn2_label, key=f"acc2_{url}", use_container_width=True, type="tertiary"):
                    st.session_state.decisions[url] = {"action": "accept_top2", "label": cat2}
                    _save_decisions()
                    st.rerun()
            with col_c:
                if st.button("✎ Manual selection", key=f"man_{url}", use_container_width=True):
                    st.session_state[f"show_manual_{url}"] = True
            with col_d:
                if st.button("✕ Reject", key=f"rej_{url}", use_container_width=True, type="secondary"):
                    st.session_state.decisions[url] = {"action": "reject", "label": ""}
                    _save_decisions()
                    st.rerun()

            # Manual category dropdown (appears below buttons when clicked)
            if st.session_state.get(f"show_manual_{url}", False):
                manual_col1, manual_col2 = st.columns([3, 1])
                with manual_col1:
                    manual_cat = st.selectbox(
                        "Select category",
                        options=CATEGORY_ORDER,
                        format_func=lambda x: CATEGORY_LABELS.get(x, x),
                        key=f"manual_{url}",
                    )
                with manual_col2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("Confirm", key=f"confirm_man_{url}", use_container_width=True, type="primary"):
                        st.session_state.decisions[url] = {"action": "manual", "label": manual_cat}
                        st.session_state[f"show_manual_{url}"] = False
                        _save_decisions()
                        st.rerun()

            # Show status
            if not decision:
                st.markdown("<p style='text-align:center;color:#888;font-weight:600;'>Status: Pending</p>", unsafe_allow_html=True)
            elif decision["action"] == "reject":
                st.markdown("<p style='text-align:center;color:#c0392b;font-weight:600;'>Status: Rejected</p>", unsafe_allow_html=True)
            else:
                st.markdown(f"<p style='text-align:center;color:#1e8449;font-weight:600;'>Status: Accepted for {CATEGORY_LABELS.get(decision['label'], decision['label'])}</p>", unsafe_allow_html=True)

    # Export decisions
    if st.session_state.decisions:
        st.markdown("")
        decision_rows = []
        for url, dec in st.session_state.decisions.items():
            if dec["action"] == "reject":
                continue
            article = df[df["url"] == url].iloc[0] if url in df["url"].values else {}
            decision_rows.append({
                "url": url,
                "title": article.get("title", ""),
                "curator_label": dec["label"],
            })
        decisions_df = pd.DataFrame(decision_rows)

        from io import BytesIO
        buffer_dec = BytesIO()
        decisions_df.to_excel(buffer_dec, index=False, engine="openpyxl")
        buffer_dec.seek(0)

        _, dl_dec_col, _ = st.columns([1, 3, 1])
        with dl_dec_col:
            st.download_button(
                f"Download {len(decisions_df)} decisions",
                buffer_dec,
                file_name=f"curator_decisions_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )


# -----------------------------
# PAGE: ADD ARTICLE
# -----------------------------
elif page == "Add Article":
    st.title("Add Article")
    st.markdown("Articles from the programme's source feeds are automatically scraped, classified and loaded into the **Review Articles** page each week. Use this page to manually add any additional articles the pipeline may have missed, for example from sources not yet in the feed, or articles shared directly by colleagues. Added articles will appear on the Review page with a **CURATOR ADDED** badge.")

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
                st.success(f"Added: **{title}** → {CATEGORY_LABELS[cat1]} / {CATEGORY_LABELS[cat2]}")

    # Show previously added articles
    if st.session_state.curator_articles:
        st.subheader(f"Curator-added articles ({len(st.session_state.curator_articles)})")
        for i, art in enumerate(st.session_state.curator_articles):
            st.markdown(f"**{art['title']}** · {art['source']} · {art['article_date']} → {CATEGORY_LABELS.get(art['top1'], art['top1'])}")


# -----------------------------
# PAGE: ORGANISE
# -----------------------------
elif page == "Organise":
    st.title("Organise Newsletter")
    st.markdown("Accepted articles grouped by category. Select up to **3 per category** for the newsletter. Use **Move to** to reassign an article to a different category.")

    # Initialise newsletter selections
    if "newsletter_picks" not in st.session_state:
        st.session_state.newsletter_picks = set()
    if "category_overrides" not in st.session_state:
        st.session_state.category_overrides = {}  # {url: new_category}

    # Get accepted articles only
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
        # Apply category override if exists
        if url in st.session_state.category_overrides:
            row["curator_label"] = st.session_state.category_overrides[url]
        accepted.append(row)

    # Also add curator-added articles
    for art in st.session_state.curator_articles:
        art_copy = art.copy()
        art_copy["curator_label"] = art["top1"]
        art_copy["curator_added"] = True
        if art.get("url") in st.session_state.category_overrides:
            art_copy["curator_label"] = st.session_state.category_overrides[art["url"]]
        accepted.append(art_copy)

    if not accepted:
        st.warning("No accepted articles yet. Go to **Review Articles** and accept some articles first.")
    else:
        n_picked = len(st.session_state.newsletter_picks)
        st.info(f"**{len(accepted)} accepted articles** | **{n_picked} selected for newsletter**")

        # Group by category
        for cat_key in CATEGORY_ORDER:
            cat_label = CATEGORY_LABELS[cat_key]
            cat_articles = [a for a in accepted if a.get("curator_label") == cat_key]

            if not cat_articles:
                continue

            n_selected = sum(1 for a in cat_articles if a.get("url") in st.session_state.newsletter_picks)
            st.subheader(f"{cat_label} ({len(cat_articles)} articles, {n_selected} selected)")

            for art in cat_articles:
                art_url = art.get("url", "")
                is_picked = art_url in st.session_state.newsletter_picks
                is_curator = art.get("curator_added", False)
                badge = " <span style='background:#f39c12;color:white;padding:2px 6px;border-radius:3px;font-size:10px;'>CURATOR</span>" if is_curator else ""
                pick_badge = " <span style='background:#27ae60;color:white;padding:2px 6px;border-radius:3px;font-size:10px;'>SELECTED</span>" if is_picked else ""

                with st.container(border=True):
                    left, btn_col, move_col = st.columns([3, 1, 1])
                    with left:
                        st.markdown(f"**Article title:** {art.get('title', 'No title')}{badge}{pick_badge}", unsafe_allow_html=True)
                        source_name = SOURCE_LABELS.get(art.get('source', ''), art.get('source', ''))
                        st.markdown(f"**Article source:** {source_name}  |  **Date:** {art.get('article_date', '')}")
                    with btn_col:
                        if is_picked:
                            if st.button("Remove", key=f"unpick_{art_url}", use_container_width=True):
                                st.session_state.newsletter_picks.discard(art_url)
                                st.rerun()
                        else:
                            if n_selected >= 3:
                                st.button("Select (max 3)", key=f"pick_{art_url}", use_container_width=True, disabled=True)
                            else:
                                if st.button("Select", key=f"pick_{art_url}", use_container_width=True):
                                    st.session_state.newsletter_picks.add(art_url)
                                    st.rerun()
                    with move_col:
                        other_cats = [k for k in CATEGORY_LABELS if k != cat_key]
                        move_to = st.selectbox(
                            "Move to",
                            [""] + other_cats,
                            format_func=lambda x: "Move to..." if x == "" else CATEGORY_LABELS.get(x, x),
                            key=f"move_{art_url}",
                            label_visibility="collapsed",
                        )
                        if move_to:
                            st.session_state.category_overrides[art_url] = move_to
                            st.rerun()

        # Export newsletter selections
        st.markdown("")

        newsletter_articles = [a for a in accepted if a.get("url") in st.session_state.newsletter_picks]
        if newsletter_articles:
            st.markdown(f"**Newsletter selections: {len(newsletter_articles)} articles**")

            newsletter_df = pd.DataFrame(newsletter_articles)[["title", "curator_label", "url"]].copy()
            newsletter_df["curator_label"] = newsletter_df["curator_label"].map(lambda x: CATEGORY_LABELS.get(x, x))

            from io import BytesIO
            buffer_nl = BytesIO()
            newsletter_df.to_excel(buffer_nl, index=False, engine="openpyxl")
            buffer_nl.seek(0)

            st.download_button(
                "Download newsletter selections",
                buffer_nl,
                file_name=f"newsletter_selections_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )



# -----------------------------
# PAGE: NEWSLETTER DRAFT
# -----------------------------
elif page == "Newsletter Draft":
    st.title("Newsletter Draft")
    st.markdown("Preview and download the newsletter as plain text. Edit descriptions inline before downloading.")

    # Gather selected articles grouped by category
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
        if art.get("url") in st.session_state.get("category_overrides", {}):
            art_copy["curator_label"] = st.session_state.category_overrides[art["url"]]
        accepted.append(art_copy)

    picks = st.session_state.get("newsletter_picks", set())
    newsletter_articles = [a for a in accepted if a.get("url") in picks]

    if not newsletter_articles:
        st.warning("No articles selected for the newsletter. Go to **Organise** and select articles first.")
    else:
        today = datetime.now()
        newsletter_date = today.strftime("%d %B %Y")

        # Editable descriptions in session state
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

        # Build plain text alongside the preview
        plain_text = f"ERP Newsletter\n{newsletter_date}\n\n"

        for cat_key in CATEGORY_ORDER:
            cat_articles = [a for a in newsletter_articles if a.get("curator_label") == cat_key]
            if not cat_articles:
                continue

            cat_label = CATEGORY_LABELS[cat_key]

            # Category header
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
                default_desc = str(art.get("text_clean", ""))[:300]

                # Editable description — empty by default for curator to write
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

        # Footer
        plain_text += "\n---\n"
        plain_text += "You have indicated that you are happy to receive news and updates from the ESRC Education Research Programme. "
        plain_text += "To unsubscribe, please email nina.charalambous.15@ucl.ac.uk with the word UNSUBSCRIBE in the title of the email.\n"
        plain_text += "Do you find this newsletter useful? Are you happy with its frequency? Which section do you find most useful? "
        plain_text += "Any pressing topics we haven't covered? Any good sources of information you think we're missing? "
        plain_text += "How could we improve? We advocate for listening to different stakeholders and so we want your views too!\n"

        # Download
        st.markdown("")

        st.download_button(
            "Download newsletter draft (plain text)",
            plain_text,
            file_name=f"newsletter_draft_{today.strftime('%Y%m%d')}.txt",
            mime="text/plain",
            use_container_width=True,
        )


# -----------------------------
# PAGE: SOURCES
# -----------------------------
elif page == "Sources":
    st.title("Newsletter Sources")
    st.markdown("All sources monitored for the ERP Weekly Newsletter. Click a source name to visit the site. The **Status** column shows whether the source is automated in the pipeline, being investigated, or requires manual checking.")

    st.markdown("")

    # Sources actually in the pipeline (from Supabase articles table):
    # epi, fed, fft, gov (DfE), schoolsweek — everything else is not yet automated
    SOURCES = [
        # Government & Parliament
        {"Source": "Department for Education (DfE)", "URL": "https://www.gov.uk/government/organisations/department-for-education", "Category": "Government & Parliament", "How monitored": "Manual check", "Status": "Automated", "Notes": "Source: gov"},
        {"Source": "Ofsted", "URL": "https://www.gov.uk/government/organisations/ofsted", "Category": "Government & Parliament", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "Education Select Committee", "URL": "https://committees.parliament.uk/committee/203/education-committee/", "Category": "Government & Parliament", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "Knowledge Exchange Unit – Parliament", "URL": "https://www.parliament.uk/get-involved/research-impact-at-the-uk-parliament/knowledge-exchange-at-uk-parliament/", "Category": "Government & Parliament", "How monitored": "Newsletter", "Status": "Not automated", "Notes": ""},
        {"Source": "POST Parliament", "URL": "https://post.parliament.uk/resources/", "Category": "Government & Parliament", "How monitored": "Newsletter", "Status": "Not automated", "Notes": ""},
        {"Source": "Local Government Association", "URL": "https://www.local.gov.uk/", "Category": "Government & Parliament", "How monitored": "Newsletter", "Status": "Not automated", "Notes": ""},

        # Four Nations
        {"Source": "Welsh Government – Children & Families", "URL": "https://www.gov.wales/children-families", "Category": "Four Nations", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "Welsh Government – Education & Skills", "URL": "https://www.gov.wales/education-skills", "Category": "Four Nations", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "Welsh Government – Digital", "URL": "https://www.gov.wales/digital", "Category": "Four Nations", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "Welsh Government – Hwb Education News", "URL": "https://hwb.gov.wales/news/articles/discovery?sort=recent", "Category": "Four Nations", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "Senedd Cymru – Children & Young People", "URL": "https://senedd.wales/senedd-now/topics/children-and-young-people/", "Category": "Four Nations", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "Senedd Cymru – Children & Young People Committee", "URL": "https://senedd.wales/committees/children-young-people-and-education-committee/", "Category": "Four Nations", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "Senedd Cymru – Education", "URL": "https://senedd.wales/senedd-now/topics/education/", "Category": "Four Nations", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "Wales Centre for Public Policy", "URL": "https://www.wcpp.org.uk/", "Category": "Four Nations", "How monitored": "Newsletter", "Status": "Not automated", "Notes": ""},
        {"Source": "Future Generations Commissioner for Wales", "URL": "https://www.futuregenerations.wales/", "Category": "Four Nations", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "Scottish Government – News", "URL": "https://www.gov.scot/news/", "Category": "Four Nations", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "Scottish Government – Publications", "URL": "https://www.gov.scot/publications/", "Category": "Four Nations", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "Scottish Government – Digital Blog", "URL": "https://blogs.gov.scot/digital/", "Category": "Four Nations", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "Scottish Parliament – SPICe Spotlight Blog", "URL": "https://spice-spotlight.scot/", "Category": "Four Nations", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "Scottish Parliament – News", "URL": "https://www.parliament.scot/about/news/news-listing", "Category": "Four Nations", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "Scottish Parliament – Education Committee", "URL": "https://www.parliament.scot/chamber-and-committees/committees/current-and-previous-committees/session-6-education-children-and-young-people-committee", "Category": "Four Nations", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "Digital Skills Scotland", "URL": "https://www.gov.scot/publications/a-changing-nation-how-scotland-will-thrive-in-a-digital-world/pages/digital-education-and-skills/", "Category": "Four Nations", "How monitored": "Newsletter", "Status": "Not automated", "Notes": ""},
        {"Source": "NI Executive – Publications", "URL": "https://www.northernireland.gov.uk/publications", "Category": "Four Nations", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "Belfast Telegraph – Education", "URL": "https://www.belfasttelegraph.co.uk/news/education", "Category": "Four Nations", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},

        # Research & Think Tanks
        {"Source": "EPI – Education Policy Institute", "URL": "https://epi.org.uk/", "Category": "Research & Think Tanks", "How monitored": "Newsletter", "Status": "Automated", "Notes": "Source: epi"},
        {"Source": "Nuffield Foundation", "URL": "https://www.nuffieldfoundation.org/", "Category": "Research & Think Tanks", "How monitored": "Newsletter", "Status": "Not automated", "Notes": ""},
        {"Source": "EEF – Education Endowment Foundation", "URL": "https://educationendowmentfoundation.org.uk/", "Category": "Research & Think Tanks", "How monitored": "Newsletter", "Status": "Not automated", "Notes": ""},
        {"Source": "NFER", "URL": "https://www.nfer.ac.uk/", "Category": "Research & Think Tanks", "How monitored": "Newsletter", "Status": "Not automated", "Notes": ""},
        {"Source": "BERA", "URL": "https://www.bera.ac.uk/", "Category": "Research & Think Tanks", "How monitored": "Newsletter", "Status": "Not automated", "Notes": ""},
        {"Source": "FFT Education Datalab", "URL": "https://ffteducationdatalab.org.uk/", "Category": "Research & Think Tanks", "How monitored": "Newsletter", "Status": "Automated", "Notes": "Source: fft"},
        {"Source": "ESRC / UKRI", "URL": "https://www.ukri.org/councils/esrc/", "Category": "Research & Think Tanks", "How monitored": "Newsletter", "Status": "Not automated", "Notes": ""},
        {"Source": "Sutton Trust", "URL": "https://www.suttontrust.com/", "Category": "Research & Think Tanks", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "Joseph Rowntree Foundation", "URL": "https://www.jrf.org.uk/", "Category": "Research & Think Tanks", "How monitored": "Newsletter", "Status": "Not automated", "Notes": ""},
        {"Source": "Nesta", "URL": "https://www.nesta.org.uk/", "Category": "Research & Think Tanks", "How monitored": "Newsletter", "Status": "Not automated", "Notes": ""},
        {"Source": "Jacobs Foundation", "URL": "https://jacobsfoundation.org/", "Category": "Research & Think Tanks", "How monitored": "Newsletter", "Status": "Not automated", "Notes": ""},
        {"Source": "Child Poverty Action Group", "URL": "https://cpag.org.uk/", "Category": "Research & Think Tanks", "How monitored": "Newsletter", "Status": "Not automated", "Notes": ""},
        {"Source": "Centre for Education and Youth", "URL": "https://cfey.org/news-and-events/", "Category": "Research & Think Tanks", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "FED – Foundation for Education Development", "URL": "https://fed.education/", "Category": "Research & Think Tanks", "How monitored": "Newsletter", "Status": "Automated", "Notes": "Source: fed"},
        {"Source": "Institute for Government", "URL": "https://www.instituteforgovernment.org.uk/", "Category": "Research & Think Tanks", "How monitored": "Forwarded", "Status": "Not automated", "Notes": "Forwarded by Gemma"},
        {"Source": "OECD – Education", "URL": "https://www.oecd.org/education/", "Category": "Research & Think Tanks", "How monitored": "Newsletter", "Status": "Not automated", "Notes": ""},
        {"Source": "EPPI Centre", "URL": "https://eppi.ioe.ac.uk/cms/", "Category": "Research & Think Tanks", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "Greater Manchester Combined Authority", "URL": "https://www.greatermanchester-ca.gov.uk/", "Category": "Research & Think Tanks", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "National Coordinating Centre for Public Engagement", "URL": "https://www.publicengagement.ac.uk/", "Category": "Research & Think Tanks", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "CAPE", "URL": "https://www.cape.ac.uk/", "Category": "Research & Think Tanks", "How monitored": "N/A", "Status": "Cannot automate", "Notes": "Now closed"},
        {"Source": "IPPO", "URL": "https://theippo.co.uk/", "Category": "Research & Think Tanks", "How monitored": "N/A", "Status": "Cannot automate", "Notes": "Now closed"},

        # Education Sector Bodies
        {"Source": "ASCL", "URL": "https://www.ascl.org.uk/", "Category": "Education Sector Bodies", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "NEU – National Education Union", "URL": "https://neu.org.uk/", "Category": "Education Sector Bodies", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "NAHT", "URL": "https://www.naht.org.uk/", "Category": "Education Sector Bodies", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "Chartered College of Teaching", "URL": "https://chartered.college/", "Category": "Education Sector Bodies", "How monitored": "Newsletter", "Status": "Automated", "Notes": "Source: cct"},
        {"Source": "Education Development Trust", "URL": "https://www.educationdevelopmenttrust.com/our-research-and-insights", "Category": "Education Sector Bodies", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "Confederation of School Trusts", "URL": "https://cstuk.org.uk/", "Category": "Education Sector Bodies", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "Teacher Tapp", "URL": "https://teachertapp.co.uk/", "Category": "Education Sector Bodies", "How monitored": "Newsletter", "Status": "Not automated", "Notes": ""},
        {"Source": "Children's Commissioner", "URL": "https://www.childrenscommissioner.gov.uk/", "Category": "Education Sector Bodies", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},

        # EdTech & Digital Rights
        {"Source": "Ada Lovelace Institute", "URL": "https://www.adalovelaceinstitute.org/", "Category": "EdTech & Digital Rights", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "5Rights Foundation", "URL": "https://5rightsfoundation.com/", "Category": "EdTech & Digital Rights", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "Defend Digital Me", "URL": "https://defenddigitalme.org/", "Category": "EdTech & Digital Rights", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "Digital Poverty Alliance", "URL": "https://digitalpovertyalliance.org/", "Category": "EdTech & Digital Rights", "How monitored": "Newsletter", "Status": "Not automated", "Notes": ""},
        {"Source": "TPEA", "URL": "https://tpea.ac.uk/", "Category": "EdTech & Digital Rights", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},

        # Media & Commentary
        {"Source": "Schools Week", "URL": "https://schoolsweek.co.uk/", "Category": "Media & Commentary", "How monitored": "Manual check", "Status": "Automated", "Notes": "Source: schoolsweek"},
        {"Source": "The Guardian – Education", "URL": "https://www.theguardian.com/education", "Category": "Media & Commentary", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "WonkHE", "URL": "https://wonkhe.com/", "Category": "Media & Commentary", "How monitored": "Newsletter", "Status": "Not automated", "Notes": "Higher education focus"},
        {"Source": "HEPI", "URL": "https://www.hepi.ac.uk/", "Category": "Media & Commentary", "How monitored": "Newsletter", "Status": "Not automated", "Notes": "Higher education focus"},
        {"Source": "LPIPS", "URL": "https://lpiphub.bham.ac.uk/", "Category": "Media & Commentary", "How monitored": "Newsletter", "Status": "Not automated", "Notes": ""},
        {"Source": "Stian Westlake Substack", "URL": "https://magicsmoke.substack.com/", "Category": "Media & Commentary", "How monitored": "Newsletter", "Status": "Not automated", "Notes": ""},

        # Internal Sources (UCL / IOE)
        {"Source": "IOE Blog", "URL": "https://www.ucl.ac.uk/ioe/news-and-events/ioe-blog", "Category": "Internal (UCL / IOE)", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "IOE Research News", "URL": "https://www.ucl.ac.uk/ioe/research/research-news", "Category": "Internal (UCL / IOE)", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "IOE Professorial Public Lectures", "URL": "https://www.ucl.ac.uk/ioe/news-and-events/ioe-professorial-public-lectures", "Category": "Internal (UCL / IOE)", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "IOE in the Media", "URL": "https://www.ucl.ac.uk/ioe/news-and-events/media", "Category": "Internal (UCL / IOE)", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "CEPEO Blog", "URL": "https://blogs.ucl.ac.uk/cepeo/", "Category": "Internal (UCL / IOE)", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "UCL Knowledge Lab", "URL": "https://www.ucl.ac.uk/ioe/departments-and-centres/centres/ucl-knowledge-lab/knowledge-lab-seminar-series", "Category": "Internal (UCL / IOE)", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "Helen Hamlyn Centre for Pedagogy", "URL": "https://www.ucl.ac.uk/ioe/departments-and-centres/centres/helen-hamlyn-centre-pedagogy-0-11-years/", "Category": "Internal (UCL / IOE)", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "CLOSER Blog", "URL": "https://closer.ac.uk/news-opinion/blog/", "Category": "Internal (UCL / IOE)", "How monitored": "Manual check", "Status": "Not automated", "Notes": ""},
        {"Source": "Emma Wisby (IOE)", "URL": "", "Category": "Internal (UCL / IOE)", "How monitored": "Weekly email", "Status": "Cannot automate", "Notes": "Email distribution list"},
        {"Source": "IOE Announcements", "URL": "", "Category": "Internal (UCL / IOE)", "How monitored": "Weekly email", "Status": "Cannot automate", "Notes": "Email bulletin"},
        {"Source": "UPEN", "URL": "", "Category": "Internal (UCL / IOE)", "How monitored": "Newsletter", "Status": "Cannot automate", "Notes": "Cross-university network"},
        {"Source": "UCL Policy Lab", "URL": "", "Category": "Internal (UCL / IOE)", "How monitored": "Newsletter", "Status": "Cannot automate", "Notes": "Via policylab@ucl.ac.uk"},
    ]

    sources_df = pd.DataFrame(SOURCES)

    # Summary counts
    status_counts = sources_df["Status"].value_counts()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total sources", len(sources_df))
    col2.metric("Automated", status_counts.get("Automated", 0))
    col3.metric("Not automated", status_counts.get("Not automated", 0))
    col4.metric("Cannot automate", status_counts.get("Cannot automate", 0))

    st.markdown("")

    # Filters
    col_cat, col_status = st.columns(2)
    with col_cat:
        cat_filter = st.selectbox("Filter by category", ["All"] + sorted(sources_df["Category"].unique().tolist()))
    with col_status:
        status_filter = st.selectbox("Filter by status", ["All"] + sorted(sources_df["Status"].unique().tolist()))

    display_df = sources_df.copy()
    if cat_filter != "All":
        display_df = display_df[display_df["Category"] == cat_filter]
    if status_filter != "All":
        display_df = display_df[display_df["Status"] == status_filter]

    # Status colours
    STATUS_COLORS = {
        "Automated": "#70ad47",
        "Not automated": "#5b9bd5",
        "Cannot automate": "#c00000",
    }

    st.markdown(f"**Showing {len(display_df)} of {len(sources_df)} sources**")

    # Display grouped by category
    for category in display_df["Category"].unique():
        cat_df = display_df[display_df["Category"] == category]
        st.subheader(category)

        for _, row in cat_df.iterrows():
            status_color = STATUS_COLORS.get(row["Status"], "#666")
            link_html = f"<a href='{row['URL']}' target='_blank'>{row['Source']}</a>" if row["URL"] else row["Source"]
            notes_html = f" · <em>{row['Notes']}</em>" if row["Notes"] else ""
            status_badge = f"<span style='background-color:{status_color};color:white;padding:2px 8px;border-radius:4px;font-size:0.8em;'>{row['Status']}</span>"

            st.markdown(
                f"{link_html} {status_badge} &nbsp; <span style='color:#888;font-size:0.85em;'>({row['How monitored']})</span>{notes_html}",
                unsafe_allow_html=True,
            )

    st.markdown("")

    # Legend
    st.markdown("**Status key**")
    legend_cols = st.columns(4)
    for col, (status, color) in zip(legend_cols, STATUS_COLORS.items()):
        col.markdown(f"<span style='background-color:{color};color:white;padding:2px 8px;border-radius:4px;font-size:0.85em;'>{status}</span>", unsafe_allow_html=True)

    st.caption("**Automated** = articles from this source are pulled automatically into the pipeline. **Not automated** = source is not yet in the pipeline; curator checks this source directly. **Cannot automate** = source is closed, email-only, or otherwise not automatable.")


# -----------------------------
# PAGE: FEEDBACK
# -----------------------------
elif page == "Feedback":
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
            # Save to CSV
            feedback_path = DATA_DIR / "curator_feedback.csv"
            feedback_df = pd.DataFrame([feedback_entry])
            if feedback_path.exists():
                existing = pd.read_csv(feedback_path)
                feedback_df = pd.concat([existing, feedback_df], ignore_index=True)
            feedback_df.to_csv(feedback_path, index=False)
            st.success("Thank you! Your feedback has been saved.")
