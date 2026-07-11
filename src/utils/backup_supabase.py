"""
backup_supabase.py

Dump the small curator-state tables from Supabase to dated CSVs under
backups/YYYY-MM-DD/. Run nightly by .github/workflows/backup.yml so a
seven-day rolling history exists in git in case curator_decisions ever
gets wiped or corrupted.

Tables backed up:
  - curator_decisions       (accept/reject/manual/save_for_later + summaries + picks)
  - curator_feedback        (curator-submitted feedback)
  - drift_log               (weekly drift snapshots)
  - fairness_log            (weekly fairness snapshots)
  - source_suggestions      (curator-submitted new-source requests)

Articles + classify_newsletter are NOT backed up here — they can always be
re-derived from a scrape + re-classify (~10 min). Only the editorial state
of curator work is irreplaceable.

Usage:
  python -m src.utils.backup_supabase
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKUP_ROOT = REPO_ROOT / "backups"
TABLES = (
    "curator_decisions",
    "curator_feedback",
    "drift_log",
    "fairness_log",
    "source_suggestions",
)


def main() -> int:
    load_dotenv()
    from supabase import create_client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("  ERROR: SUPABASE_URL + SUPABASE_SERVICE_KEY required.")
        return 1

    client = create_client(url, key)
    today = datetime.now().strftime("%Y-%m-%d")
    out_dir = BACKUP_ROOT / today
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Backing up to {out_dir}")

    summary_rows = []
    errored: list[str] = []
    row_counts: dict[str, int] = {}
    for table in TABLES:
        try:
            resp = client.table(table).select("*").execute()
            rows = resp.data or []
            df = pd.DataFrame(rows)
            path = out_dir / f"{table}.csv"
            df.to_csv(path, index=False)
            print(f"  {table:<25} {len(rows):>5} rows → {path.relative_to(REPO_ROOT)}")
            summary_rows.append({"table": table, "rows": len(rows)})
            row_counts[table] = len(rows)
        except Exception as e:
            print(f"  {table:<25} ERROR: {e}")
            summary_rows.append({"table": table, "rows": -1, "error": str(e)[:100]})
            errored.append(table)

    # Always write the summary first so the artifact exists for diagnosis even
    # when we fail below.
    pd.DataFrame(summary_rows).to_csv(out_dir / "_summary.csv", index=False)

    # Fail loudly rather than reporting a green run over an empty/partial backup.
    # (1) any table that errored is a failure; (2) an empty curator_decisions is a
    # failure — it's the one irreplaceable table this backup exists for, and the
    # weekly reset never clears it, so 0 rows in live operation means something is
    # wrong (bad auth, wrong DB, silent API error).
    if errored:
        print(f"\n  FAILED: {len(errored)} table(s) errored: {', '.join(errored)}. "
              f"Backup is incomplete — NOT a valid snapshot.")
        return 1
    if row_counts.get("curator_decisions", 0) == 0:
        print("\n  FAILED: curator_decisions backed up 0 rows — an empty snapshot of "
              "the irreplaceable table. Check SUPABASE_URL/key point at the live DB.")
        return 1

    print(f"\n  Done. Restore from these CSVs via `supabase-py insert` if needed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
