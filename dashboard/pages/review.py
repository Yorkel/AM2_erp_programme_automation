from io import BytesIO
from datetime import datetime

import streamlit as st
import pandas as pd

from dashboard.config import CATEGORY_LABELS, CATEGORY_ORDER, CATEGORY_COLORS, SOURCE_LABELS
from dashboard.data import record_decision, load_decisions, is_authenticated


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
        review_export["top1_confidence"] = (review_export["top1_confidence"] * 100).round(0).astype("Int64")
    if "top2_confidence" in review_export.columns:
        review_export["top2_confidence"] = (review_export["top2_confidence"] * 100).round(0).astype("Int64")

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

    # Pull current decisions (cached 60s)
    decisions = load_decisions()

    # Status filter + Sort + Progress
    STATUS_OPTIONS = ["All", "Pending", "Saved for later", "Accepted", "Rejected"]
    col_status, col_sort, col_progress = st.columns(3)
    with col_status:
        status_filter = st.selectbox("Show", STATUS_OPTIONS, index=0)
    with col_sort:
        sort_by = st.selectbox("Order by", ["Date (newest first)", "Date (oldest first)", "Source"])

    def _status_for(url: str) -> str:
        dec = decisions.get(url)
        if not dec: return "Pending"
        a = dec.get("action")
        if a == "reject": return "Rejected"
        if a == "save_for_later": return "Saved for later"
        return "Accepted"

    if status_filter != "All":
        filtered = filtered[filtered["url"].apply(lambda u: _status_for(u) == status_filter)].copy()

    n_reviewed = sum(1 for url in filtered["url"] if url in decisions)
    with col_progress:
        st.markdown(f"**Progress:** {n_reviewed} / {len(filtered)} reviewed")
        st.progress(n_reviewed / len(filtered) if len(filtered) > 0 else 0)

    # Primary sort: review status (pending first, reviewed pushed down).
    # Secondary: chosen by the curator (date or source).
    _STATUS_ORDER = {"Pending": 0, "Saved for later": 1, "Accepted": 2, "Rejected": 3}
    filtered = filtered.assign(_status_rank=filtered["url"].apply(
        lambda u: _STATUS_ORDER.get(_status_for(u), 0)
    ))

    if sort_by == "Date (newest first)":
        filtered = filtered.sort_values(
            ["_status_rank", "article_date"], ascending=[True, False], na_position="last"
        )
    elif sort_by == "Date (oldest first)":
        filtered = filtered.sort_values(
            ["_status_rank", "article_date"], ascending=[True, True], na_position="last"
        )
    else:
        filtered = filtered.sort_values(
            ["_status_rank", "source"], ascending=[True, True], na_position="last"
        )
    filtered = filtered.drop(columns=["_status_rank"])

    # Article cards
    for card_idx, (idx, row) in enumerate(filtered.iterrows()):
        url = row.get("url", str(idx))
        conf1 = row.get("top1_confidence")
        conf2 = row.get("top2_confidence")
        conf1 = float(conf1) if pd.notna(conf1) else None
        conf2 = float(conf2) if pd.notna(conf2) else None
        cat1 = row.get("top1") if pd.notna(row.get("top1")) else None
        cat2 = row.get("top2") if pd.notna(row.get("top2")) else None
        cat1_label = CATEGORY_LABELS.get(cat1, cat1) if cat1 else "(unclassified)"
        cat2_label = CATEGORY_LABELS.get(cat2, cat2) if cat2 else ""

        def _conf_color(c):
            if c is None: return "#999999"
            return "#27ae60" if c >= 0.6 else "#f39c12" if c >= 0.4 else "#e74c3c"
        conf1_color = _conf_color(conf1)
        conf2_color = _conf_color(conf2)

        decision = decisions.get(url)

        st.markdown(f"<div style='border-top:3px solid #1d3461;margin:20px 0;'></div>", unsafe_allow_html=True)
        st.markdown(f"### {row.get('title', 'No title')}")

        with st.container(border=True):
            is_curator = row.get("curator_added", False)
            badge = " <span style='background:#f39c12;color:white;padding:2px 8px;border-radius:3px;font-size:11px;font-weight:600;'>MANUALLY ADDED</span>" if is_curator else ""

            source_name = SOURCE_LABELS.get(row.get('source', ''), row.get('source', ''))
            link_html = f" &nbsp;<a href='{row['url']}' target='_blank' style='font-size:14px;'>Open article \u2197</a>" if row.get("url") else ""
            st.markdown(f"<p style='color:#666;font-size:16px;text-align:center;'><b>Source:</b> {source_name}  &middot;  <b>Date:</b> {row.get('article_date', '')}{link_html}{badge}</p>", unsafe_allow_html=True)

            if row.get("text_clean"):
                with st.expander("Click to preview text"):
                    st.write(str(row["text_clean"])[:500])

            def _label(prefix, lbl, c):
                if is_curator or c is None:
                    return f"{prefix}: {lbl}"
                return f"{prefix}: {lbl} ({c:.0%})"
            btn1_label = _label("Category 1", cat1_label, conf1)
            btn2_label = _label("Category 2", cat2_label, conf2)

            auth = is_authenticated()
            col_a, col_b, col_c, col_d, col_e = st.columns(5)
            with col_a:
                if st.button(btn1_label, key=f"acc1_{url}", use_container_width=True, type="primary", disabled=not auth):
                    record_decision(url, "accept_top1", cat1)
                    st.rerun()
            with col_b:
                if st.button(btn2_label, key=f"acc2_{url}", use_container_width=True, type="tertiary", disabled=not auth):
                    record_decision(url, "accept_top2", cat2)
                    st.rerun()
            with col_c:
                if st.button("\u270e Manual selection", key=f"man_{url}", use_container_width=True, type="primary", disabled=not auth):
                    st.session_state[f"show_manual_{url}"] = True
            with col_d:
                if st.button("\u2606 Save for later", key=f"save_{url}", use_container_width=True, type="tertiary", disabled=not auth):
                    record_decision(url, "save_for_later", "")
                    st.rerun()
            with col_e:
                if st.button("\u2715 Reject", key=f"rej_{url}", use_container_width=True, type="secondary", disabled=not auth):
                    record_decision(url, "reject", "")
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
                        record_decision(url, "manual", manual_cat)
                        st.session_state[f"show_manual_{url}"] = False
                        st.rerun()

            if not decision:
                st.markdown("<p style='text-align:center;color:#888;font-weight:600;'>Status: Pending</p>", unsafe_allow_html=True)
            elif decision.get("action") == "reject":
                st.markdown("<p style='text-align:center;color:#c0392b;font-weight:600;'>Status: Rejected</p>", unsafe_allow_html=True)
            elif decision.get("action") == "save_for_later":
                st.markdown("<p style='text-align:center;color:#8e44ad;font-weight:600;'>Status: Saved for later</p>", unsafe_allow_html=True)
            else:
                lbl = decision.get("label", "")
                st.markdown(f"<p style='text-align:center;color:#1e8449;font-weight:600;'>Status: Accepted for {CATEGORY_LABELS.get(lbl, lbl)}</p>", unsafe_allow_html=True)

    # Export decisions
    if decisions:
        st.markdown("")
        decision_rows = []
        for url, dec in decisions.items():
            if dec.get("action") == "reject":
                continue
            article = df[df["url"] == url].iloc[0] if url in df["url"].values else {}
            decision_rows.append({
                "url": url,
                "title": article.get("title", ""),
                "curator_label": dec.get("label", ""),
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
