"""
s01_clean.py
Loads raw extracted newsletter data, fixes text encoding, removes rows
with missing essential fields, and deduplicates.

Input:  data/interim/extracted_newsletters.csv
Output: data/interim/newsletters_cleaned.csv
"""

import unicodedata as ud

import pandas as pd
from ftfy import fix_text

# -----------------------------
# CONFIG
# -----------------------------
INPUT_CSV  = "data/interim/extracted_newsletters.csv"
OUTPUT_CSV = "data/interim/newsletters_cleaned.csv"

# Text tokens to treat as missing
NA_TOKENS = ["", " ", "NA", "N/A", "na", "NaN", "nan", "null", "NULL", "-"]

# Common encoding artifacts to fix
REPL = {
    "\u00c2 ": " ", "\u00c2": "",
    "\u201a\u00c4\u00ec": "\u2013", "\u201a\u00c4\u00ee": "\u2014",
    "\u201a\u00c4\u00f4": "\u2018", "\u201a\u00c4\u00f2": "\u2019",
    "\u201a\u00c4\u00fa": "\u201c", "\u201a\u00c4\u00f9": "\u201d",
    "\u00e2\u20ac\u201c": "\u2013", "\u00e2\u20ac\u201d": "\u2014",
    "\u00e2\u20ac\u02dc": "\u2018", "\u00e2\u20ac\u2122": "\u2019",
    "\u00e2\u20ac\u0153": "\u201c", "\u00e2\u20ac\x9d": "\u201d",
    "\u00e2\u20ac\u00a2": "\u2022", "\u00e2\u20ac\u00a6": "\u2026",
}


# -----------------------------
# FUNCTIONS
# -----------------------------

def clean_series(s: pd.Series) -> pd.Series:
    """Fix encoding, normalise unicode, collapse whitespace."""
    s = s.astype("string")
    mask = s.notna()
    s.loc[mask] = s.loc[mask].apply(fix_text)
    s.loc[mask] = s.loc[mask].apply(lambda x: ud.normalize("NFKC", x))
    s.loc[mask] = s.loc[mask].str.replace(r"\s+", " ", regex=True).str.strip()
    return s


def fix_artifacts(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    """Apply known encoding artifact replacements to string columns."""
    for c in cols:
        s = df[c].astype("string")
        for bad, good in REPL.items():
            s = s.str.replace(bad, good, regex=False)
        s = s.str.replace(r"\s+", " ", regex=True).str.strip()
        df[c] = s
    return df


def drop_missing_essentials(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows missing title or link. Description is optional."""
    before = len(df)
    df = df.dropna(subset=["title", "link"]).copy()
    # Drop rows where the extracted 'title' is just a bare URL (extraction artefact)
    url_mask = df["title"].str.strip().str.match(r"https?://", na=False)
    df = df[~url_mask].copy()
    print(f"  Dropped {before - len(df)} rows with missing title/link or URL-as-title. Remaining: {len(df)}")
    return df


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicates in three passes: title+link, title only, link only."""
    before = len(df)

    df = df.drop_duplicates(subset=["title", "link"], keep="first").reset_index(drop=True)
    print(f"  After title+link dedup: {len(df)} rows (removed {before - len(df)})")

    before = len(df)
    df = df.drop_duplicates(subset=["title"], keep="first").reset_index(drop=True)
    print(f"  After title-only dedup: {len(df)} rows (removed {before - len(df)})")

    before = len(df)
    df = df.drop_duplicates(subset=["link"], keep="first").reset_index(drop=True)
    print(f"  After link-only dedup:  {len(df)} rows (removed {before - len(df)})")

    return df


# -----------------------------
# MAIN
# -----------------------------

def main():
    print("Loading data...")
    df = pd.read_csv(INPUT_CSV)
    print(f"  Loaded {len(df)} rows from {INPUT_CSV}")

    print("\nCleaning text columns...")
    obj_cols = [c for c in df.columns if df[c].dtype == object or pd.api.types.is_string_dtype(df[c])]
    for c in obj_cols:
        df[c] = clean_series(df[c])
    df = fix_artifacts(df, obj_cols)

    print("\nDropping rows with missing essential fields...")
    df = drop_missing_essentials(df)

    print("\nDeduplicating...")
    df = deduplicate(df)

    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSaved {len(df)} rows to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
