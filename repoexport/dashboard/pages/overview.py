"""
Overview / landing page — pipeline-wide summary across all time.

Template variant: no classifier means no "categories per week" chart and no
val-accuracy caption. Add those back per the original ERP repo if your topic
includes a classifier.

Shows: total articles, sources contributing, sources monitored, plus 12-week
trend of article volume, and an all-time top-sources list.
"""

from datetime import datetime, date, timedelta
from pathlib import Path

import streamlit as st
import pandas as pd

from dashboard.config import SOURCE_LABELS


def _count_monitored_sources() -> int | None:
    """Read sources.yml and return the count of enabled sources monitored
    by the scraping pipeline. Returns None on any failure."""
    try:
        import yaml
        repo_root = Path(__file__).resolve().parents[2]
        data = yaml.safe_load((repo_root / "src" / "scraping" / "sources.yml").read_text())
        return sum(1 for s in (data.get("sources") or []) if not s.get("disabled"))
    except Exception:
        return None


def render(df: pd.DataFrame):
    st.title("Overview")
    st.markdown("Pipeline-wide summary of articles and sources.")

    if df.empty:
        st.warning("No articles in Supabase yet. Trigger the scrape workflow to populate.")
        return

    df = df.copy()
    df["_article_date"] = pd.to_datetime(
        df["article_date"], errors="coerce", dayfirst=True
    ).dt.date

    # ── Headline metrics (all time) ─────────────────────────────────────────
    n_articles = len(df)
    n_sources_contributing = df["source"].nunique() if "source" in df.columns else 0
    n_sources_monitored = _count_monitored_sources()

    cols = st.columns(3)
    cols[0].metric("Articles scraped (all time)", f"{n_articles:,}")
    cols[1].metric("Sources contributing (all time)", n_sources_contributing)
    cols[2].metric("Sources monitored", n_sources_monitored if n_sources_monitored is not None else "—")

    st.markdown("")

    # ── 12-week trend window (Mon-Sun calendar weeks) ───────────────────────
    today = date.today()
    this_monday = today - timedelta(days=today.weekday())
    earliest_monday = this_monday - timedelta(weeks=11)
    all_weeks = [earliest_monday + timedelta(weeks=i) for i in range(12)]

    recent = df[df["_article_date"] >= earliest_monday].copy()
    recent = recent[recent["_article_date"].notna()]
    recent["_week_start"] = recent["_article_date"].apply(
        lambda d: d - timedelta(days=d.weekday())
    )

    # ── Articles per week ───────────────────────────────────────────────────
    st.subheader("Articles per week (last 12 weeks)")
    weekly_counts = recent.groupby("_week_start").size().reset_index(name="Articles")
    week_index = pd.DataFrame({"_week_start": all_weeks})
    weekly_counts = week_index.merge(weekly_counts, on="_week_start", how="left").fillna(0)
    weekly_counts["_week_start"] = pd.to_datetime(weekly_counts["_week_start"])
    st.line_chart(weekly_counts.set_index("_week_start")["Articles"])

    st.markdown("")

    # ── Top contributing sources (all time) ─────────────────────────────────
    if "source" in df.columns:
        st.subheader("Top contributing sources (all time)")
        src_counts = df["source"].value_counts().head(10)
        for source_name, count in src_counts.items():
            label = SOURCE_LABELS.get(source_name, source_name)
            st.markdown(
                f"- **{label}** &middot; {count} article{'s' if count != 1 else ''}",
                unsafe_allow_html=True,
            )

    # ── Footer ──────────────────────────────────────────────────────────────
    st.markdown("---")
    st.caption(
        f"Last refresh: {datetime.now().strftime('%Y-%m-%d %H:%M')} &middot; "
        f"Go to **Review Articles** to start curating."
    )
