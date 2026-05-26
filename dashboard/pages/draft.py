"""
Page 3 — Newsletter Draft.

Shows every categorised article (action ∈ {accept_top1, accept_top2, manual}),
grouped by section. Curator can:
  - edit each summary in place + Save
  - click Generate summary to re-draft via Claude
  - click × in the top-right of a card to remove from the draft (sets reject)
  - download the lot as Excel (TITLE / SOURCE / URL / SUMMARY / SECTION / DATE)
  - leave free-text feedback at the bottom (→ curator_feedback.suggestions)
"""

from datetime import datetime
from io import BytesIO

import streamlit as st
import pandas as pd

from dashboard.config import CATEGORY_LABELS, CATEGORY_ORDER, SOURCE_LABELS
from dashboard.data import (
    fetch_article_text, get_accepted_articles, is_authenticated, load_decisions,
    record_decision, record_feedback, record_summary,
)
from src.inference.summarise import summarise_article


def _category_of(art: dict) -> str | None:
    """Effective section assignment — what Page 2 set on the curator_decisions row."""
    return art.get("curator_label") or art.get("top1")


def _build_excel(grouped: dict, today: datetime) -> bytes:
    """Single-sheet Excel matching the curator MS Form export structure, so the
    download can be merged directly with the curator-suggestions spreadsheet.

    Columns match the MS Form column headers exactly (including punctuation):
      Id, Start time, Organisation, Title, Include,
      Link (website address / URL), Short description,
      Which section of the newsletter is this for?, Any other comments?,
      Submitter, Question

    "Include" defaults to "Yes" (the curator accepted all of these on Page 2).
    "Submitter" / "Any other comments?" / "Question" are left blank for the
    curator to fill on review.
    """
    rows = []
    row_id = 1
    for cat_key in CATEGORY_ORDER:
        for art in grouped.get(cat_key, []):
            url = art.get("url") or ""
            session_key = f"desc_{url}"
            summary = (
                st.session_state.get(session_key)
                or (art.get("summary") or "")
                or "Summary unavailable"
            )
            article_date = art.get("article_date") or ""
            # Render article_date as DD/MM/YYYY to match MS Forms convention
            try:
                d = pd.to_datetime(article_date, errors="coerce", dayfirst=True)
                date_str = d.strftime("%d/%m/%Y") if not pd.isna(d) else (article_date or "")
            except Exception:
                date_str = article_date or ""
            rows.append({
                "Id": row_id,
                "Start time": date_str,
                "Organisation": SOURCE_LABELS.get(art.get("source", ""), art.get("source") or ""),
                "Title": art.get("title") or "",
                "Include": "Yes",
                "Link (website address / URL)": url,
                "Short description": summary,
                "Which section of the newsletter is this for?": CATEGORY_LABELS.get(cat_key, cat_key),
                "Any other comments?": st.session_state.get(f"notes_{url}", "") or "",
                "Submitter": st.session_state.get("draft_submitter", "") or "",
                "Question": st.session_state.get(f"question_{url}", "") or "",
            })
            row_id += 1
    columns = [
        "Id", "Start time", "Organisation", "Title", "Include",
        "Link (website address / URL)", "Short description",
        "Which section of the newsletter is this for?",
        "Any other comments?", "Submitter", "Question",
    ]
    df = pd.DataFrame(rows, columns=columns)
    buf = BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    buf.seek(0)
    return buf.getvalue()


def render(df):
    st.title("Newsletter Draft")
    st.markdown(
        "Each categorised article appears below, grouped by section. "
        "**Save** persists summary edits; **Generate summary** re-drafts via Claude; "
        "**×** removes the article from the draft. Download as Excel at the bottom."
    )

    accepted = get_accepted_articles(df)
    if not accepted:
        st.info(
            "No categorised articles yet. Use **Triage** → **Select Categories** "
            "first, then come back."
        )
        return

    # Group by curator-assigned category. Articles without a valid category
    # are silently skipped — Page 2 always sets one, so this shouldn't happen.
    grouped: dict[str, list[dict]] = {k: [] for k in CATEGORY_ORDER}
    for art in accepted:
        cat = _category_of(art)
        if cat in grouped:
            grouped[cat].append(art)

    today = datetime.now()
    newsletter_date = today.strftime("%d %B %Y")

    # Newsletter header
    st.markdown(
        f"""
        <div style="background:#0f1e3d;color:white;padding:20px;border-radius:8px;
                    text-align:center;margin-bottom:20px;">
            <div style="font-size:18px;font-weight:700;">ESRC Education Research Programme</div>
            <div style="font-size:14px;color:#8fa8c8;margin-top:4px;">ERP Newsletter</div>
            <div style="font-size:14px;color:#8fa8c8;">{newsletter_date}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Submitter — applies to every row of the Excel download. Lives in session
    # state only (no persistence) — set per session by the curator running the
    # draft. Empty cells in MS Form merges are fine.
    auth = is_authenticated()
    st.text_input(
        "Submitter (your name — appears on every row of the Excel download)",
        key="draft_submitter",
        placeholder="e.g. Louise Y",
        disabled=not auth,
    )

    decisions = load_decisions()

    # ── Articles by section ─────────────────────────────────────────────────
    for cat_key in CATEGORY_ORDER:
        articles = grouped.get(cat_key, [])
        if not articles:
            continue
        cat_label = CATEGORY_LABELS[cat_key]
        st.markdown(
            f"<div style='background:#1d3461;padding:10px 16px;border-radius:4px;"
            f"margin:18px 0 8px 0;'>"
            f"<span style='color:#c8d8ec;font-size:15px;font-weight:600;'>{cat_label}</span></div>",
            unsafe_allow_html=True,
        )

        for art in articles:
            art_url = art.get("url") or ""
            title = art.get("title") or "No title"
            source_name = SOURCE_LABELS.get(art.get("source", ""), art.get("source") or "")
            article_date = art.get("article_date") or ""
            session_key = f"desc_{art_url}"

            # Seed text_area initial value from DB on first render of this URL.
            # Fallback order: curator edit > pre-generated articles.summary > empty.
            # articles.summary is exposed via v_dashboard after migration 012.
            if session_key not in st.session_state:
                st.session_state[session_key] = (
                    (decisions.get(art_url) or {}).get("summary")
                    or art.get("summary")
                    or ""
                )

            with st.container(border=True):
                # Top row: TITLE on the left, × on the right
                col_t, col_x = st.columns([10, 1])
                with col_t:
                    st.markdown(f"**TITLE:** {title}")
                with col_x:
                    if st.button(
                        "×",
                        key=f"xrm_{art_url}",
                        help="Remove from newsletter (sets to Rejected)",
                        disabled=not auth,
                    ):
                        record_decision(art_url, "reject", "")
                        st.rerun()

                st.markdown(f"**SOURCE:** {source_name}")
                if art_url:
                    st.markdown(f"**URL:** [{art_url}]({art_url})")

                st.markdown("**SUMMARY:**")
                edited_desc = st.text_area(
                    "summary",
                    key=session_key,
                    height=120,
                    label_visibility="collapsed",
                    disabled=not auth,
                )

                # Per-article curator-fillable fields. Written into the Excel
                # download under the MS-Form column headers. Session-only for
                # now — survives within a tab, resets on reload.
                col_notes, col_question = st.columns(2)
                with col_notes:
                    st.text_input(
                        "Any other comments?",
                        key=f"notes_{art_url}",
                        placeholder="Optional curator note for this row",
                        disabled=not auth,
                    )
                with col_question:
                    st.text_input(
                        "Question",
                        key=f"question_{art_url}",
                        placeholder="Optional",
                        disabled=not auth,
                    )

                col_save, col_gen = st.columns(2)
                with col_save:
                    if st.button(
                        "💾 Save", key=f"sv_{art_url}",
                        use_container_width=True, disabled=not auth,
                    ):
                        record_summary(art_url, edited_desc)
                        st.toast("Saved.")
                with col_gen:
                    if st.button(
                        "✎ Generate summary", key=f"gn_{art_url}",
                        use_container_width=True, disabled=not auth,
                    ):
                        with st.spinner("Summarising via Claude…"):
                            # Fetch full body from articles.text (v_dashboard
                            # only exposes text_clean, the 80-word snippet).
                            body = fetch_article_text(art_url) or art.get("text_clean") or ""
                            new_summary = summarise_article(
                                title=title, text=body, category=cat_key,
                            )
                        record_summary(art_url, new_summary)
                        # Drop the widget's session_state key so the next
                        # render re-seeds from the freshly-saved Supabase
                        # summary. Streamlit forbids writing to a widget key
                        # in the same script run that created the widget.
                        if session_key in st.session_state:
                            del st.session_state[session_key]
                        st.rerun()

    # ── Download Excel ──────────────────────────────────────────────────────
    st.markdown("---")
    excel_bytes = _build_excel(grouped, today)
    st.download_button(
        "📥 Download newsletter as Excel",
        excel_bytes,
        file_name=f"newsletter_{today.strftime('%Y_%m_%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        type="primary",
    )
    st.caption(
        "Tip: hit **Save** on any edited summary before downloading — "
        "unsaved edits will still appear in the Excel, but won't persist if you reload."
    )

    # ── Feedback ────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Feedback")
    st.caption("Anonymous. Whatever you write here goes to the curator_feedback log.")
    feedback_text = st.text_area(
        "Free-text feedback",
        key="_feedback_box",
        height=120,
        placeholder="Anything you'd like to flag — wrong categorisations, broken articles, sources missing, etc.",
        label_visibility="collapsed",
        disabled=not auth,
    )
    if st.button("Submit feedback", key="_feedback_submit", disabled=not auth):
        if feedback_text and feedback_text.strip():
            record_feedback(feedback_text.strip())
            # Reset the box on the next rerun
            st.session_state["_feedback_box"] = ""
            st.success("Feedback submitted. Thank you.")
            st.rerun()
        else:
            st.warning("Feedback is empty.")
