from io import BytesIO
from datetime import datetime

import streamlit as st
import pandas as pd

from ..config import CATEGORY_LABELS, CATEGORY_ORDER, CATEGORY_COLORS, SOURCE_LABELS
from ..data import save_decisions


def render(df):
    st.title("Review Articles")
    st.markdown("Review each article's classification. The model suggests two possible categories. **Accept** the correct one or **reject** if neither fits. Rejected articles won't appear in the newsletter draft.")

    weeks = sorted(df["week_number"].dropna().unique().astype(int).tolist(), reverse=True)
    with st.container(border=True):
        col_week, col_count = st.columns([1, 2])
        with col_week:
            selected_week = st.selectbox("Select week", weeks, index=0)

        filtered = df[df["week_number"] == selected_week].copy()

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

    # Download for manual review
    review_cols = ["title", "source", "article_date", "url", "top1", "top1_confidence", "top2", "top2_confidence"]
    available = [c for c in review_cols if c in filtered.columns]
    review_export = filtered[available].copy()
    if "top1_confidence" in review_export.columns:
        review_export["top1_confidence"] = (review_export["top1_confidence"] * 100).round(0).astype(int)
    if "top2_confidence" in review_export.columns:
        review_export["top2_confidence"] = (review_export["top2_confidence"] * 100).round(0).astype(int)

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

    # Sort + Progress
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
        conf1_color = "#27ae60" if conf1 >= 0.6 else "#f39c12" if conf1 >= 0.4 else "#e74c3c"
        conf2_color = "#27ae60" if conf2 >= 0.6 else "#f39c12" if conf2 >= 0.4 else "#e74c3c"

        decision = st.session_state.decisions.get(url)
        total_articles = len(filtered)

        st.markdown(f"<div style='border-top:3px solid #1d3461;margin:20px 0;'></div>", unsafe_allow_html=True)
        st.markdown(f"### Article {card_idx + 1}/{total_articles}: {row.get('title', 'No title')}")

        with st.container(border=True):
            is_curator = row.get("curator_added", False)
            badge = " <span style='background:#f39c12;color:white;padding:2px 8px;border-radius:3px;font-size:11px;font-weight:600;'>MANUALLY ADDED</span>" if is_curator else ""

            source_name = SOURCE_LABELS.get(row.get('source', ''), row.get('source', ''))
            link_html = f" &nbsp;<a href='{row['url']}' target='_blank' style='font-size:14px;'>Open article \u2197</a>" if row.get("url") else ""
            st.markdown(f"<p style='color:#666;font-size:16px;text-align:center;'><b>Source:</b> {source_name}  &middot;  <b>Date:</b> {row.get('article_date', '')}{link_html}{badge}</p>", unsafe_allow_html=True)

            if row.get("text_clean"):
                with st.expander("Click to preview text"):
                    st.write(str(row["text_clean"])[:500])

            btn1_label = f"Category 1: {cat1_label} ({conf1:.0%})" if not is_curator else f"Category 1: {cat1_label}"
            btn2_label = f"Category 2: {cat2_label} ({conf2:.0%})" if not is_curator else f"Category 2: {cat2_label}"

            col_a, col_b, col_c, col_d = st.columns(4)
            with col_a:
                if st.button(btn1_label, key=f"acc1_{url}", use_container_width=True, type="primary"):
                    st.session_state.decisions[url] = {"action": "accept_top1", "label": cat1}
                    save_decisions()
                    st.rerun()
            with col_b:
                if st.button(btn2_label, key=f"acc2_{url}", use_container_width=True, type="tertiary"):
                    st.session_state.decisions[url] = {"action": "accept_top2", "label": cat2}
                    save_decisions()
                    st.rerun()
            with col_c:
                if st.button("\u270e Manual selection", key=f"man_{url}", use_container_width=True, type="primary"):
                    st.session_state[f"show_manual_{url}"] = True
            with col_d:
                if st.button("\u2715 Reject", key=f"rej_{url}", use_container_width=True, type="secondary"):
                    st.session_state.decisions[url] = {"action": "reject", "label": ""}
                    save_decisions()
                    st.rerun()

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
                        save_decisions()
                        st.rerun()

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
