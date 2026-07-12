"""
Page 1 - Review (triage).

Curator quickly keeps or rejects each article from the selected week, and
optionally generates a summary. NO category assignment here - kept articles
flow to Page 2 (Organise) where the category is set.

Action values written to curator_decisions:
  - "keep"          curator wants this in the newsletter (no category yet)
  - "reject"        curator does not want this
  - "summary_only"  placeholder if Generate Summary clicked before keep/reject
"""

from datetime import date, timedelta
from html import escape as html_escape
from urllib.parse import urlparse

import streamlit as st
import pandas as pd

from dashboard.config import source_label
from dashboard.data import (
    delete_decision, fetch_article_text, is_authenticated, load_decisions,
    record_decision, record_summary, record_topic_sentence,
)
from src.inference.summarise import extract_topic_sentence, summarise_article


def _clean(v):
    """Coerce pandas nulls to ''. A pandas NaN is a *truthy* float, so the
    usual `x or ''` guard lets it slip through and renders the literal string
    'nan' in the UI. Lists/tuples (e.g. topic_tags) are returned as-is."""
    if isinstance(v, (list, tuple)):
        return v
    if v is None:
        return ""
    if isinstance(v, float) and pd.isna(v):
        return ""
    s = str(v).strip()
    return "" if s.lower() == "nan" else s


def _html(v) -> str:
    """Escape external text before inserting it into styled HTML snippets."""
    return html_escape(_clean(v), quote=True)


def _safe_href(v) -> str:
    """Return a clickable web URL, or '' for non-web / malformed values."""
    url = _clean(v)
    parsed = urlparse(url)
    return url if parsed.scheme in {"http", "https"} and parsed.netloc else ""


def _tuesday_on_or_before(d: date) -> date:
    """Most recent Tuesday on or before `d` - anchors a scrape-week (Tue→Mon)."""
    return d - timedelta(days=(d.weekday() - 1) % 7)


def _ordinal(n: int) -> str:
    """1 -> '1st', 2 -> '2nd', 11 -> '11th', etc."""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _format_week_label(wk_start: date, wk_end: date) -> str:
    """e.g. 'Tuesday 19th May - Monday 25th May 2026' (year only on the end
    date to keep the label readable). If the week spans years, show both."""
    start = f"Tuesday {_ordinal(wk_start.day)} {wk_start:%B}"
    if wk_start.year != wk_end.year:
        start = f"{start} {wk_start.year}"
    end = f"Monday {_ordinal(wk_end.day)} {wk_end:%B} {wk_end.year}"
    return f"{start} - {end}"


def _week_options(df: pd.DataFrame) -> list[tuple[str, date, date]]:
    """Build every completed Tue→Mon week back to the earliest article we have.
    A week is 'completed' only once its Monday end has passed (so the
    in-progress week isn't shown until the following Tuesday).
    Newest first."""
    if "_article_date" not in df.columns:
        return []
    dates = df["_article_date"].dropna()
    if dates.empty:
        return []
    earliest = _tuesday_on_or_before(dates.min())
    # Latest completed week ends on the most recent Monday < today.
    today = date.today()
    days_since_mon = (today.weekday() - 0) % 7  # Mon=0
    last_completed_end = today - timedelta(days=days_since_mon + 1) if days_since_mon == 0 else today - timedelta(days=days_since_mon)
    # If today is Mon, the week ending yesterday hasn't quite finished - so
    # only show weeks ending strictly before today.
    if last_completed_end >= today:
        last_completed_end = today - timedelta(days=1)
    anchor = _tuesday_on_or_before(last_completed_end)
    out: list[tuple[str, date, date]] = []
    cur = anchor
    while cur >= earliest:
        wk_end = cur + timedelta(days=6)
        out.append((_format_week_label(cur, wk_end), cur, wk_end))
        cur = cur - timedelta(days=7)
    return out


def _status_for(url: str, decisions: dict) -> str:
    dec = decisions.get(url)
    if not dec:
        return "Pending"
    action = dec.get("action")
    if action == "reject":
        return "Rejected"
    if action == "keep":
        return "Kept"
    if action in ("accept_top1", "accept_top2", "manual"):
        return "Categorised"
    # summary_only or unknown - show as pending in this view
    return "Pending"


_STATUS_COLOUR = {
    "Pending": "#888",
    "Kept": "#1e8449",
    "Rejected": "#c0392b",
    "Categorised": "#2980b9",
}

_TAG_STYLE = (
    "background:#eef;color:#333;padding:1px 6px;border-radius:8px;"
    "font-size:10px;border:1px solid #ccd;margin-right:3px;"
)


def _badges_html(geo: str | None, topics: list[str] | None) -> str:
    """Return an HTML snippet for the 'Key tags:' row - geographic_focus +
    up to 3 topic_tags. All badges share one neutral style (country isn't
    coloured differently from topics). Empty string if nothing to render."""
    parts = []
    geo = _clean(geo)
    if geo:
        parts.append(f"<span style='{_TAG_STYLE}'>{_html(geo)}</span>")
    topics = topics if isinstance(topics, (list, tuple)) else []
    for t in topics[:3]:
        t = _clean(t)
        if t:
            parts.append(f"<span style='{_TAG_STYLE}'>{_html(t)}</span>")
    if not parts:
        return ""
    return (
        "<p style='margin:2px 0;font-size:11px;color:#555;'>"
        "<b>Key tags:</b> " + "".join(parts) + "</p>"
    )


def render(df):
    st.title("Step 1: Triage")

    # Targeted button colours: the Keep button uses a marker div + sibling-selector
    # so it can be green (positive action) without recolouring every secondary button.
    # Reject stays neutral grey (Streamlit's default secondary).
    st.markdown("""
    <style>
    /* Keep button = green. The .keep-btn-marker div is placed immediately
       before the st.button("Keep") call; the adjacent-sibling selector then
       targets the button's element-container. The marker's wrapper is
       collapsed to 0 height so Keep stays aligned with Reject. */
    .element-container:has(.keep-btn-marker) {
        display: none;
    }
    .element-container:has(.keep-btn-marker) + div [data-testid="stButton"] button {
        background-color: #2ecc71 !important;
        border-color: #27ae60 !important;
        color: white !important;
    }
    .element-container:has(.keep-btn-marker) + div [data-testid="stButton"] button:hover {
        background-color: #27ae60 !important;
        border-color: #229954 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Normalise article_date. Scraped rows = ISO; curator-added = DD-MM-YYYY;
    # dayfirst=True handles both.
    df = df.copy()
    # Defensive: if the loaded data is missing article_date (schema drift in
    # classify_newsletter), don't crash - create an all-NaT column so the rest
    # of the page renders an empty week instead of white-screening.
    if "article_date" in df.columns:
        df["_article_date"] = pd.to_datetime(
            df["article_date"], errors="coerce", dayfirst=True
        ).dt.date
    else:
        df["_article_date"] = pd.Series([pd.NaT] * len(df), index=df.index)

    # ── Search (all weeks) ──────────────────────────────────────────────────
    # When the curator types here, search EVERY article (all weeks, any status)
    # by title/summary - for checking coverage ("did we cover X?") or finding a
    # past item. Empty box = normal current-week view below.
    col_search, col_clear = st.columns([8, 1])
    with col_search:
        query = st.text_input(
            "🔍 Search all articles",
            placeholder="Search every week by title or summary…",
            key="_triage_search",
        ).strip()
    with col_clear:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)  # align
        st.button(
            "✕ Clear", use_container_width=True,
            disabled=not query,
            on_click=lambda: st.session_state.update({"_triage_search": ""}),
            help="Clear the search and return to the current-week view.",
        )
    if query:
        q = query.lower()
        SEARCH_CAP = 50

        def _hit(row):
            hay = f"{_clean(row.get('title'))} {_clean(row.get('summary'))}".lower()
            return q in hay

        matches = df[df.apply(_hit, axis=1)].copy()
        matches = matches.sort_values(
            "_article_date", ascending=False, na_position="last"
        )
        total = len(matches)
        shown = matches.head(SEARCH_CAP)
        note = f" (showing newest {SEARCH_CAP})" if total > SEARCH_CAP else ""
        st.info(f"{total} article(s) matching “{query}” across all weeks{note}")
        for _, row in shown.iterrows():
            _render_triage_card(row.to_dict())
        return

    # ── Week selector ───────────────────────────────────────────────────────
    weeks = _week_options(df)
    if not weeks:
        st.info("No completed weeks of articles to review yet.")
        return
    selected_label = st.selectbox(
        "Week", [w[0] for w in weeks], index=0,
        help="Articles are scraped once a week (Tuesday morning). Each week runs Tue–Mon.",
    )
    week_start, week_end = next(
        ((s, e) for (lbl, s, e) in weeks if lbl == selected_label),
        (weeks[0][1], weeks[0][2]),
    )

    filtered = df[
        (df["_article_date"] >= week_start) & (df["_article_date"] <= week_end)
    ].copy()

    # Default behaviour: show only Pending articles, newest first. The filter
    # and sort selectboxes used to live here but Gemma asked them removed -
    # in practice she always used the defaults anyway.
    decisions = load_decisions()
    # .astype(bool) is load-bearing: when the selected week has no rows, apply()
    # returns an empty object/str Series, which pandas would treat as a list of
    # COLUMN labels (selecting zero columns and dropping _article_date) rather
    # than a boolean row mask - making the sort below KeyError. astype(bool)
    # keeps it a boolean mask even when empty.
    filtered = filtered[filtered["url"].apply(
        lambda u: _status_for(u, decisions) == "Pending"
    ).astype(bool)].copy()
    filtered = filtered.sort_values("_article_date", ascending=False, na_position="last")

    st.info(f"{len(filtered)} pending article(s)")

    # ── Article cards ───────────────────────────────────────────────────────
    for idx, row in filtered.iterrows():
        _render_triage_card(row.to_dict())


@st.fragment
def _render_triage_card(row: dict):
    """Render one article card. Wrapped in @st.fragment so clicks
    (Keep, Reject, Generate Summary) only rerun this single card - not
    the whole 100-card list. Fetches own decisions for fresh state."""
    decisions = load_decisions()
    auth = is_authenticated()
    url = _clean(row.get("url"))
    title = _clean(row.get("title")) or "No title"
    source_raw = _clean(row.get("source"))
    source_name = source_label(source_raw)
    article_date = _clean(row.get("article_date"))
    status = _status_for(url, decisions)

    st.markdown(
        "<div style='border-top:3px solid #1d3461;margin:20px 0;'></div>",
        unsafe_allow_html=True,
    )
    st.markdown(f"### {_html(title)}")

    with st.container(border=True):
        # Status badge sits inline with title area on the right; URL + tags
        # take up the rest. Tags go ABOVE source (matches Select Categories).
        colour = _STATUS_COLOUR.get(status, "#888")

        # Key tags row - directly under title, before source/date
        badges = _badges_html(row.get("geographic_focus"), row.get("topic_tags"))
        if badges:
            st.markdown(badges, unsafe_allow_html=True)

        # Status badge + Source · Date. The badge shows the article's current
        # state (Pending / Kept / Rejected / Categorised) - useful everywhere,
        # but especially in all-weeks search results where statuses are mixed.
        status_badge = (
            f"<span style='background:{colour};color:white;padding:1px 8px;"
            f"border-radius:8px;font-size:11px;font-weight:600;'>{status}</span>"
        )
        st.markdown(
            f"<p style='color:#666;font-size:14px;margin:2px 0;'>"
            f"{status_badge} &nbsp; <b>Source:</b> {_html(source_name)} "
            f"&nbsp;&nbsp; <b>Date:</b> {_html(article_date)}</p>",
            unsafe_allow_html=True,
        )

        # URL (full-width, no per-card Status badge - filter already gates view)
        if url:
            url_html = _html(url)
            href_html = _html(_safe_href(url))
            link = f"<a href='{href_html}' target='_blank'>{url_html}</a>" if href_html else url_html
            st.markdown(
                f"<p style='font-size:12px;margin:0;overflow-wrap:anywhere;'>"
                f"<b>URL:</b> {link}</p>",
                unsafe_allow_html=True,
            )

        # Triage shows the EXTRACTIVE topic sentence (verbatim from the article)
        # - quicker for the curator to trust during keep/reject. The polished
        # AI summary lives on the Draft page. Both are stored separately.
        topic_sentence = _clean(row.get("topic_sentence"))
        with st.expander("📌 Topic sentence", expanded=False):
            if topic_sentence:
                st.markdown(
                    f"<div style='background:#eef6ee;border-left:3px solid #2ecc71;"
                    f"padding:8px 12px;'>{_html(topic_sentence)}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div style='background:#f5f5f5;border-left:3px solid #aaa;"
                    "padding:8px 12px;color:#666;font-style:italic;'>"
                    "No topic sentence yet</div>",
                    unsafe_allow_html=True,
                )
            if auth:
                if st.button(
                    "📌 Regenerate topic sentence", key=f"topic_{url}",
                    use_container_width=True,
                    help="Pull a key sentence verbatim from the article "
                         "(its own words - quick to check).",
                ):
                    with st.spinner("Finding a key sentence…"):
                        body = fetch_article_text(url)
                        new_ts = extract_topic_sentence(title=title, text=body)
                    record_topic_sentence(url, new_ts)
                    st.rerun(scope="fragment")

        # AI summary: same AI-backed generation as the Draft page, surfaced
        # here so a curator can fill a blank summary at review time. The scheduled
        # pipeline can leave summaries blank when the GitHub runner cannot reach
        # Claude (incident 2026-06-29). Generation now falls back to OpenAI
        # and then to an extractive source-text summary. The
        # expander opens by default when there's no summary, to prompt the action.
        summary = _clean(row.get("summary"))
        with st.expander("📝 Summary", expanded=not summary):
            if summary:
                st.markdown(
                    f"<div style='background:#eef;border-left:3px solid #5b8def;"
                    f"padding:8px 12px;'>{_html(summary)}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div style='background:#fff4f4;border-left:3px solid #e0a;"
                    "padding:8px 12px;color:#666;font-style:italic;'>"
                    "No summary yet, generate one below.</div>",
                    unsafe_allow_html=True,
                )
            # Always render the button (greyed when not signed in) so it stays
            # consistent with Keep/Reject and the "generate one below" prompt
            # never points at a button that isn't there.
            if st.button(
                "✎ Generate summary" if not summary else "✎ Regenerate summary",
                key=f"summary_{url}", use_container_width=True, disabled=not auth,
                help="AI writes a 1-2 sentence summary from the article "
                     "(falls back to OpenAI/source text if Claude is unavailable).",
            ):
                with st.spinner("Summarising…"):
                    body = fetch_article_text(url)
                    new_summary = summarise_article(
                        title=title, text=body, category=row.get("top1"),
                    )
                record_summary(url, new_summary)
                st.rerun(scope="fragment")

        # Keep/Reject only while Pending. Once decided, the card flips IN PLACE to
        # its outcome + an Undo, and every click reruns ONLY this fragment
        # (scope="fragment") so the pending list does NOT reflow under the curator.
        # Fixes Gemma's 2026-06-09 report: rejecting a card used to shift the list
        # up and hide the next title, causing accidental rejects of unseen stories.
        if status == "Pending":
            col_keep, col_reject = st.columns(2)
            with col_keep:
                st.markdown('<div class="keep-btn-marker"></div>', unsafe_allow_html=True)
                if st.button(
                    "✓ Keep", key=f"keep_{url}",
                    type="secondary", use_container_width=True, disabled=not auth,
                ):
                    record_decision(url, "keep", "")
                    st.rerun(scope="fragment")
            with col_reject:
                if st.button(
                    "✕ Reject", key=f"reject_{url}",
                    type="secondary", use_container_width=True, disabled=not auth,
                ):
                    record_decision(url, "reject", "")
                    st.rerun(scope="fragment")
        else:
            st.markdown(
                f"<p style='font-size:14px;margin:4px 0;'>This article is "
                f"<b style='color:{colour};'>{status}</b>.</p>",
                unsafe_allow_html=True,
            )
            if st.button(
                "↩ Undo", key=f"undo_{url}",
                type="secondary", use_container_width=True, disabled=not auth,
                help="Put this article back to Pending - recovers an accidental Keep/Reject.",
            ):
                delete_decision(url)
                st.rerun(scope="fragment")
