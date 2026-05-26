"""
Page 2 — Select Categories.

Curator picks a section for each article kept on Page 1 (Triage). Articles are
grouped into clusters (cosine-similarity ≥ 0.85, computed by
src/inference/scoring.py) so cross-outlet duplicates and same-source near-
duplicates appear together — curator picks one (or several) per cluster.

Action transitions:
  keep  →  accept_top1  (curator confirms top1 prediction)
        →  accept_top2  (curator chooses top2)
        →  manual       (curator picks a different category)
"""

from __future__ import annotations
from collections import defaultdict

import streamlit as st
import pandas as pd

from dashboard.config import CATEGORY_LABELS, CATEGORY_ORDER, CATEGORY_SHORT_LABELS, SOURCE_LABELS
from dashboard.data import (
    get_kept_articles, is_authenticated, record_decision,
)


_STATUS_COLOUR = {
    "Awaiting category": "#d35400",
    "Categorised": "#1e8449",
}

_TAG_STYLE = (
    "background:#eef;color:#333;padding:2px 8px;border-radius:10px;"
    "font-size:10px;border:1px solid #ccd;margin-right:3px;"
)


def _badges_html(geo, topics) -> str:
    """'Key tags:' row — geographic_focus + up to 3 topic_tags, all in the
    same neutral style (country no longer coloured differently)."""
    parts = []
    if geo:
        parts.append(f"<span style='{_TAG_STYLE}'>{geo}</span>")
    for t in (topics or [])[:3]:
        parts.append(f"<span style='{_TAG_STYLE}'>{t}</span>")
    if not parts:
        return ""
    return (
        "<p style='margin:2px 0;font-size:11px;color:#555;'>"
        "<b>Key tags:</b> " + "".join(parts) + "</p>"
    )


def _format_conf(c) -> str:
    """Return ' (87%)' style suffix; empty if confidence missing."""
    try:
        v = float(c)
        if v != v:  # NaN
            return ""
        return f" ({v:.0%})"
    except (TypeError, ValueError):
        return ""


def _status_for(action: str | None) -> str:
    if action in ("accept_top1", "accept_top2", "manual"):
        return "Categorised"
    return "Awaiting category"


@st.fragment
def _render_article(art: dict, idx_in_cluster: int):
    """Render one article card with the category-assignment UI.

    Wrapped in @st.fragment so button clicks (Top 1, Top 2, Manual, Reject)
    only rerun this single card — not the whole page list. Massively cuts
    perceived latency on a busy queue.
    """
    url = art.get("url", "")
    title = art.get("title") or "No title"
    source = SOURCE_LABELS.get(art.get("source", ""), art.get("source", ""))
    article_date = art.get("article_date", "")
    action = art.get("action")
    curator_label = art.get("curator_label")
    status = _status_for(action)

    top1 = art.get("top1") if pd.notna(art.get("top1")) else None
    top2 = art.get("top2") if pd.notna(art.get("top2")) else None
    conf1 = _format_conf(art.get("top1_confidence"))
    conf2 = _format_conf(art.get("top2_confidence"))

    auth = is_authenticated()

    with st.container(border=True):
        # Title row — title on the left, status badge inline on the right
        col_title, col_status = st.columns([5, 1])
        with col_title:
            st.markdown(f"### {title}")
        with col_status:
            colour = _STATUS_COLOUR[status]
            badge_text = "Categorised" if status == "Categorised" else "Awaiting category"
            st.markdown(
                f"<p style='text-align:right;color:{colour};font-weight:600;"
                f"margin:14px 0 0 0;font-size:13px;'>{badge_text}</p>",
                unsafe_allow_html=True,
            )

        # Key tags row — directly under title, smaller font.
        badges = _badges_html(art.get("geographic_focus"), art.get("topic_tags"))
        if badges:
            st.markdown(badges, unsafe_allow_html=True)

        # Source, Date
        st.markdown(
            f"<p style='color:#666;font-size:13px;margin:2px 0;'>"
            f"<b>Source:</b> {source} &nbsp;&nbsp; <b>Date:</b> {article_date}</p>",
            unsafe_allow_html=True,
        )

        # URL (full, clickable)
        if url:
            st.markdown(
                f"<p style='font-size:12px;margin:0 0 6px 0;overflow-wrap:anywhere;'>"
                f"<b>URL:</b> <a href='{url}' target='_blank'>{url}</a></p>",
                unsafe_allow_html=True,
            )

        # Action buttons — all four on ONE row.
        # Top 1 (green) | Top 2 (blue) | Manual (dropdown + Set) | Remove (grey)
        col_t1, col_t2, col_man, col_rem = st.columns([2, 2, 3, 1])
        with col_t1:
            short1 = CATEGORY_SHORT_LABELS.get(top1, "(no top1)") if top1 else "(no top1)"
            st.markdown('<div class="cat-top1-marker"></div>', unsafe_allow_html=True)
            if st.button(
                f"{short1}{conf1}",
                key=f"cat_t1_{url}",
                type="secondary",
                use_container_width=True,
                disabled=(not auth) or (top1 is None),
            ):
                record_decision(url, "accept_top1", top1)
                st.rerun()
        with col_t2:
            short2 = CATEGORY_SHORT_LABELS.get(top2, "(no top2)") if top2 else "(no top2)"
            st.markdown('<div class="cat-top2-marker"></div>', unsafe_allow_html=True)
            if st.button(
                f"{short2}{conf2}",
                key=f"cat_t2_{url}",
                type="secondary",
                use_container_width=True,
                disabled=(not auth) or (top2 is None),
            ):
                record_decision(url, "accept_top2", top2)
                st.rerun()
        with col_man:
            # Manual = popover. One button to open; the dropdown lives inside.
            # Cleaner than always-visible selectbox + Set button.
            with st.popover(
                "Manual",
                use_container_width=True,
                disabled=not auth,
            ):
                manual_default = (
                    curator_label if action == "manual" and curator_label in CATEGORY_ORDER
                    else CATEGORY_ORDER[0]
                )
                manual_choice = st.selectbox(
                    "Pick category",
                    options=CATEGORY_ORDER,
                    index=CATEGORY_ORDER.index(manual_default),
                    format_func=lambda x: CATEGORY_SHORT_LABELS.get(x, x),
                    key=f"cat_man_choice_{url}",
                    label_visibility="collapsed",
                )
                if st.button(
                    "Apply",
                    key=f"cat_man_apply_{url}",
                    type="primary",
                    use_container_width=True,
                ):
                    record_decision(url, "manual", manual_choice)
                    st.rerun()
        with col_rem:
            if st.button(
                "Remove",
                key=f"cat_reject_{url}",
                type="secondary",
                use_container_width=True,
                disabled=not auth,
            ):
                record_decision(url, "reject", "")
                st.rerun()


def render(df):
    st.title("Select Categories")
    st.markdown(
        "For each article kept on **Triage**, pick a newsletter section. "
        "Articles covering the same story are grouped together; pick one or "
        "categorise several if they offer different angles."
    )

    # Page-wide button + popover shrink (Top 1 / Top 2 / Manual / Remove
    # buttons were too tall and the labels too big at default Streamlit size).
    st.markdown("""
    <style>
    /* Shrink all buttons + popover triggers on this page only */
    [data-testid="stButton"] button,
    [data-testid="stPopover"] button {
        font-size: 12px !important;
        padding: 4px 8px !important;
        min-height: 32px !important;
    }
    /* Tighten the selectbox inside popovers too */
    [data-testid="stPopover"] [data-testid="stSelectbox"] {
        font-size: 12px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Targeted button colours via marker-divs + sibling-selector CSS.
    # Top 1 = green (model's best guess), Top 2 = blue (alternative).
    # Same trick as the Keep button on Triage.
    st.markdown("""
    <style>
    .element-container:has(.cat-top1-marker) { display: none; }
    .element-container:has(.cat-top1-marker) + div [data-testid="stButton"] button {
        background-color: #2ecc71 !important;
        border-color: #27ae60 !important;
        color: white !important;
    }
    .element-container:has(.cat-top2-marker) { display: none; }
    .element-container:has(.cat-top2-marker) + div [data-testid="stButton"] button {
        background-color: #3498db !important;
        border-color: #2980b9 !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

    kept = get_kept_articles(df)
    if not kept:
        st.info(
            "Nothing here yet. Keep some articles on the **Triage** page and "
            "they'll appear here for category assignment."
        )
        return

    # Group by cluster_id. NaN/None becomes its own per-article group so
    # uncluster-ed items still render.
    groups: dict[object, list[dict]] = defaultdict(list)
    for art in kept:
        cid = art.get("cluster_id")
        # Treat NaN/None as a unique key per-URL — singleton groups, no grouping
        if cid is None or (isinstance(cid, float) and cid != cid):
            cid = f"_solo_{art.get('url', id(art))}"
        groups[cid].append(art)

    # Sort articles within each group: cluster lead first (if present), then
    # by composite_score desc, then by URL for stability.
    def _within_group_sort_key(a):
        lead = -1 if a.get("is_cluster_lead") else 0
        score = -(a.get("composite_score") or 0.0)
        return (lead, score, a.get("url") or "")
    for cid in groups:
        groups[cid].sort(key=_within_group_sort_key)

    # Sort groups by the lead article's date (newest first)
    def _group_sort_key(item):
        cid, members = item
        lead = members[0]
        d = pd.to_datetime(lead.get("article_date"), errors="coerce", dayfirst=True)
        # NaT sorts last
        return (pd.isna(d), -(d.value if not pd.isna(d) else 0))
    sorted_groups = sorted(groups.items(), key=_group_sort_key)

    # Summary line
    n_groups = len(sorted_groups)
    n_articles = len(kept)
    n_awaiting = sum(1 for a in kept if _status_for(a.get("action")) == "Awaiting category")
    st.info(
        f"**{n_articles}** kept article(s) across **{n_groups}** group(s); "
        f"{n_awaiting} awaiting category."
    )

    # Render
    for group_idx, (cid, members) in enumerate(sorted_groups):
        lead = members[0]
        size = len(members)
        if size == 1:
            # Singleton — render directly, no expander
            _render_article(lead, idx_in_cluster=0)
        else:
            # Cluster — header card + expander for siblings
            lead_title = lead.get("title") or "No title"
            lead_source = SOURCE_LABELS.get(lead.get("source", ""), lead.get("source", ""))
            st.markdown(
                f"<div style='border-top:3px solid #1d3461;margin:18px 0 4px 0;'></div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"### {lead_title}  "
                f"<span style='background:#1d3461;color:white;padding:2px 8px;"
                f"border-radius:10px;font-size:11px;'>+{size - 1} similar</span>",
                unsafe_allow_html=True,
            )
            st.caption(f"Cluster lead from {lead_source}. Expand to see {size - 1} other item(s) covering the same story.")
            _render_article(lead, idx_in_cluster=0)
            with st.expander(f"Show {size - 1} similar item(s) in this cluster"):
                for i, sibling in enumerate(members[1:], start=1):
                    _render_article(sibling, idx_in_cluster=i)
