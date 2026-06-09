"""
weekly_reset.py — archive + reset the curator's working week.

Run by .github/workflows/weekly_reset.yml every Monday morning (and triggerable
manually). Snapshots the current week's curator_decisions into
curator_decisions_archive, then records a new week boundary in curator_resets so
last week's kept/categorised articles drop out of the Categorise + Draft pages
and the new week starts fresh.

NON-DESTRUCTIVE: curator_decisions is left intact, so kept/rejected articles
keep their status (they don't reappear in Review) and pending articles are
untouched. The boundary only hides last week's work from Categorise + Draft.

This mirrors dashboard.data.archive_and_reset_week but is standalone (no
Streamlit) so it can run headless in CI.

Env required: SUPABASE_URL, SUPABASE_SERVICE_KEY
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone

from src.scraping.supabase_client import get_client


def main() -> int:
    client = get_client()

    # Current week boundary = most recent reset_at (None if never reset).
    r = (
        client.table("curator_resets")
        .select("reset_at").order("reset_at", desc=True).limit(1).execute()
    )
    boundary = r.data[0]["reset_at"] if r.data else None

    # This week's decisions = everything decided at/after the last boundary.
    q = client.table("curator_decisions").select("*")
    if boundary:
        q = q.gte("decided_at", boundary)
    rows = q.execute().data or []

    week_label = f"week up to {datetime.now(timezone.utc).strftime('%a %d %b %Y')}"

    if rows:
        client.table("curator_decisions_archive").insert(
            [{"week_label": week_label, "url": x.get("url"), "decision": x} for x in rows]
        ).execute()

    client.table("curator_resets").insert(
        {"week_label": week_label, "n_archived": len(rows)}
    ).execute()

    print(f"Weekly reset done: archived {len(rows)} decision(s) as '{week_label}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
