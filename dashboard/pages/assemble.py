"""
Newsletter agent page: upload the week's manual Excel, merge it with the
non-rejected dashboard items, run the three-voice categorisation panel, and
draft the issue in house style. The curator stays the decider; the panel only
auto-sorts the clear items and flags the contested few.
"""
from datetime import date, timedelta

import streamlit as st

from dashboard import agent_engine as eng


def _default_week():
    """Most recent Tuesday -> the following Monday (the scrape week)."""
    today = date.today()
    tue = today - timedelta(days=(today.weekday() - 1) % 7)  # Tuesday on/before today
    return tue, tue + timedelta(days=6)


def render(df):
    st.markdown("## 📰 Assemble newsletter")
    st.caption("Upload this week's submissions Excel. This merges them with the "
               "dashboard items, sorts everything into sections, flags the few it is "
               "unsure about, and drafts the issue. You make the final call.")

    avail = eng.available()
    if not avail["claude"] or not avail["supabase"]:
        st.error("Missing ANTHROPIC_API_KEY or SUPABASE_URL. Set them in the deployment secrets (or .env locally).")
        return
    if not avail["gpt"]:
        st.warning("No OPENAI_API_KEY found, so the panel runs with two voices (Claude + your classifier) instead of three.")

    authed = bool(st.session_state.get("authenticated"))
    if not authed:
        st.info("Log in (top right) to run the agent - it makes paid API calls.")

    win_a, win_b = _default_week()
    up = st.file_uploader("Manual submissions Excel (.xlsx)", type=["xlsx"])
    st.caption(f"This week: {win_a:%a %d %b} to {win_b:%a %d %b}")

    if st.button("🧩 Assemble draft", type="primary", disabled=not authed):
        with st.spinner("Building the candidate pool and running the three-voice panel…"):
            pool = eng.build_pool(up.getvalue() if up else None, str(win_a), str(win_b))
            if not pool:
                st.warning("No candidate items found for that week. Check the dates and the upload.")
                return
            st.session_state["_agent_panel"] = eng.run_panel(pool)
            st.session_state.pop("_agent_draft", None)

    panel = st.session_state.get("_agent_panel")
    if not panel:
        return

    flagged = [p for p in panel if p["flag"]]
    assigned = [p for p in panel if not p["flag"]]
    st.success(f"{len(panel)} items: {len(assigned)} auto-sorted, {len(flagged)} need your call.")

    # ── items the three voices split on ──────────────────────────────────────
    if flagged:
        st.markdown("### ⚠️ Needs your call (the voices disagree)")
        for p in flagged:
            with st.container(border=True):
                st.markdown(f"**{p['title']}**")
                v = p["votes"]
                st.caption(f"Claude: {v['Claude']}  ·  GPT-4o: {v['GPT-4o']}  ·  Your classifier: {v['Classifier']}")
                choice = st.selectbox("Your section", eng.SECTIONS, key=f"flag_{p['id']}",
                                      index=eng.SECTIONS.index(v["Claude"]) if v["Claude"] in eng.SECTIONS else 0)
                p["section"] = choice  # curator resolves it
                p["flag"] = False

    # ── auto-sorted, grouped by section ──────────────────────────────────────
    st.markdown("### Sorted into sections")
    for sec in eng.SECTIONS:
        rows = [p for p in panel if p.get("section") == sec]
        if not rows:
            continue
        st.markdown(f"**{sec}**  ·  {len(rows)}")
        for p in rows:
            badge = "✅" if p["agreement"] == "3/3" else "🟢"
            st.markdown(f"{badge} {p['title']}  \n<span style='color:#888;font-size:0.85em'>{p['origin']} · {p['agreement']} agree</span>",
                        unsafe_allow_html=True)

    st.markdown("---")
    if st.button("✍️ Generate house-style draft", disabled=not authed):
        with st.spinner("Drafting…"):
            st.session_state["_agent_draft"] = eng.generate_draft([p for p in panel if p.get("section")])

    draft = st.session_state.get("_agent_draft")
    if draft:
        st.markdown("### Draft issue")
        st.markdown(draft)
        st.download_button("⬇️ Download draft (.md)", draft, file_name="newsletter_draft.md")
