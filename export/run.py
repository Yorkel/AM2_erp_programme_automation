# Education Policy Scraper — pipeline entry point.
#
# MODE A — full retrospective (no --since flag):
#   python run.py --country eng
#   Scrapes all England sources back to 2023-01-01.
#   Output: per-source CSVs in data/training/england/
#           then run england/merge.py to produce data/training/training_data.csv
#
# MODE B — training top-up (--since and --until <= TRAINING_CUTOFF):
#   python run.py --country eng --since 2025-12-05 --until 2025-12-31
#   Appends new articles to existing training CSVs. Run england/merge.py afterwards.
#
# MODE C — weekly inference (--since and --until after TRAINING_CUTOFF):
#   python run.py --country eng --since 2026-02-21 --until 2026-02-27 --week 9
#   Writes one merged CSV to data/inference/england/week09_2026-02-27.csv
#
# Scotland / Ireland — retrospective (one-time, Jan 2023 → 20 Feb 2026):
#   python run.py --country sco --until 2026-02-20
#   python run.py --country irl --until 2026-02-20
#   → data/inference/scotland/2026-02-20.csv
#   → data/inference/ireland/2026-02-20.csv
#   Scotland and Ireland are inference-only (Phase 1). All data goes to data/inference/.
#
# Weekly inference (all three countries, from 21 Feb 2026 onwards):
#   python run.py --country eng --since 2026-02-21 --until 2026-02-27 --week 9
#   python run.py --country sco --since 2026-02-21 --until 2026-02-27 --week 9
#   python run.py --country irl --since 2026-02-21 --until 2026-02-27 --week 9
#
# GitHub Actions calls Mode C automatically each Monday for all three countries.

import argparse
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from england.dfe import scrape_dfe
from england.epi import scrape_epi
from england.nuffield import scrape_nuffield
from england.fftlabs import scrape_fft_datalab
from england.fed import scrape_fed
from england.schoolsweek import scrape_schoolsweek

from scotland.gov_scot import scrape_gov_scot
from scotland.sera import scrape_sera
from scotland.gtcs import scrape_gtcs
from scotland.ades import scrape_ades
from scotland.children_in_scotland import scrape_children_in_scotland

from ireland.gov_ie import scrape_gov_ie
from ireland.esri import scrape_esri
from ireland.erc import scrape_erc
from ireland.teaching_council import scrape_teaching_council
from ireland.education_matters import scrape_education_matters
from ireland.thejournal import scrape_thejournal
from ireland.rte import scrape_rte

from scraping.wordpress_adapter import make_wp_scraper

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data"

TRAINING_CUTOFF = date(2025, 12, 31)  # articles up to this date = training data

# Default retrospective start per country
RETROSPECTIVE_START = {
    "eng": date(2023, 1, 1),
    "sco": date(2023, 1, 1),
    "irl": date(2023, 1, 1),
    "wal": date(2023, 1, 1),
    "ni":  date(2023, 1, 1),
}

COUNTRY_DIR = {
    "eng": "england",
    "sco": "scotland",
    "irl": "ireland",
    "wal": "wales",
    "ni":  "northern_ireland",
}

# Countries whose retro data (up to TRAINING_CUTOFF) goes to training
TRAINING_COUNTRIES = {"eng", "irl", "sco", "wal", "ni"}

# Per-source training CSV filenames (country subfolder added at runtime)
TRAINING_FILENAMES = {
    # England
    "schoolsweek": "schoolsweek.csv",
    "gov":         "govuk_education.csv",
    "epi":         "epi.csv",
    "nuffield":    "nuffield.csv",
    "fft":         "fft_education_datalab.csv",
    "fed":         "fed.csv",
    # Ireland
    "gov_ie":            "gov_ie.csv",
    "esri":              "esri.csv",
    "erc":               "erc.csv",
    "teaching_council":  "teaching_council.csv",
    "education_matters": "education_matters.csv",
    "thejournal":        "thejournal.csv",
    "rte":               "rte.csv",
    # Scotland
    "gov_scot":               "gov_scot.csv",
    "sera":                   "sera.csv",
    "gtcs":                   "gtcs.csv",
    "ades":                   "ades.csv",
    "children_in_scotland":   "children_in_scotland.csv",
    # New WordPress sources (England)
    "sutton_trust":              "sutton_trust.csv",
    "childrens_commissioner_eng": "childrens_commissioner_eng.csv",
    "teacher_tapp":              "teacher_tapp.csv",
    "jacobs_foundation":         "jacobs_foundation.csv",
    "cfey":                      "cfey.csv",
    "ippo":                      "ippo.csv",
    "defend_digital_me":         "defend_digital_me.csv",
    "tpea":                      "tpea.csv",
    "lpip_hub":                  "lpip_hub.csv",
    "oii_edtech":                "oii_edtech.csv",
    "ucl_cepeo_blog":            "ucl_cepeo_blog.csv",
    "ucl_ioe_blog":              "ucl_ioe_blog.csv",
    # New WordPress sources (Scotland)
    "spice_spotlight":           "spice_spotlight.csv",
    "scot_gov_digital_blog":     "scot_gov_digital_blog.csv",
    # Top-10 research adds (2026-06)
    "fe_week":                   "fe_week.csv",
    "hepi":                      "hepi.csv",
    "ofqual_blog":               "ofqual_blog.csv",
    "ofsted_inspection":         "ofsted_inspection.csv",
    "enlighten":                 "enlighten.csv",
    "iwa":                       "iwa.csv",
    "wiserd":                    "wiserd.csv",
    "niccy":                     "niccy.csv",
    "into":                      "into.csv",
    "education_magazine_irl":    "education_magazine_irl.csv",
}

# Scrapers grouped by country code
SCRAPERS = {
    "eng": [
        ("schoolsweek", scrape_schoolsweek),
        ("gov",         scrape_dfe),
        ("epi",         scrape_epi),
        ("nuffield",    scrape_nuffield),
        ("fft",         scrape_fft_datalab),
        ("fed",         scrape_fed),
        # New WordPress sources
        ("sutton_trust",              make_wp_scraper("https://www.suttontrust.com/wp-json/wp/v2/posts")),
        ("childrens_commissioner_eng", make_wp_scraper("https://www.childrenscommissioner.gov.uk/wp-json/wp/v2/posts")),
        ("teacher_tapp",              make_wp_scraper("https://teachertapp.com/wp-json/wp/v2/posts")),
        ("jacobs_foundation",         make_wp_scraper("https://jacobsfoundation.org/wp-json/wp/v2/posts")),
        ("cfey",                      make_wp_scraper("https://cfey.org/wp-json/wp/v2/posts")),
        ("ippo",                      make_wp_scraper("https://theippo.co.uk/wp-json/wp/v2/posts")),
        ("defend_digital_me",         make_wp_scraper("https://defenddigitalme.org/wp-json/wp/v2/posts")),
        ("tpea",                      make_wp_scraper("https://tpea.ac.uk/wp-json/wp/v2/posts")),
        ("lpip_hub",                  make_wp_scraper("https://lpiphub.bham.ac.uk/wp-json/wp/v2/posts")),
        ("oii_edtech",                make_wp_scraper("https://edtech.oii.ox.ac.uk/wp-json/wp/v2/posts")),
        ("ucl_cepeo_blog",            make_wp_scraper("https://blogs.ucl.ac.uk/cepeo/wp-json/wp/v2/posts")),
        ("ucl_ioe_blog",              make_wp_scraper("https://blogs.ucl.ac.uk/ioe/wp-json/wp/v2/posts")),
        # Top-10 research adds (2026-06) — NB: ofqual_blog and ofsted_inspection
        # introduce a new "regulator" category that triggers NMF retrain
        # per pipeline_decisions.md §14.
        ("fe_week",           make_wp_scraper("https://feweek.co.uk/wp-json/wp/v2/posts")),
        ("hepi",              make_wp_scraper("https://www.hepi.ac.uk/wp-json/wp/v2/posts")),
        ("ofqual_blog",       make_wp_scraper("https://ofqual.blog.gov.uk/wp-json/wp/v2/posts")),
        ("ofsted_inspection", make_wp_scraper("https://educationinspection.blog.gov.uk/wp-json/wp/v2/posts")),
    ],
    "sco": [
        ("gov_scot",                scrape_gov_scot),
        ("sera",                    scrape_sera),
        ("gtcs",                    scrape_gtcs),
        ("ades",                    scrape_ades),
        ("children_in_scotland",    scrape_children_in_scotland),
        # New WordPress sources
        ("spice_spotlight",         make_wp_scraper("https://spice-spotlight.scot/wp-json/wp/v2/posts")),
        ("scot_gov_digital_blog",   make_wp_scraper("https://blogs.gov.scot/digital/wp-json/wp/v2/posts")),
        # Top-10 research adds (2026-06)
        ("enlighten",               make_wp_scraper("https://www.enlighten.scot/wp-json/wp/v2/posts")),
    ],
    "irl": [
        ("gov_ie",              scrape_gov_ie),
        ("esri",                scrape_esri),
        ("erc",                 scrape_erc),
        ("teaching_council",    scrape_teaching_council),
        ("education_matters",   scrape_education_matters),
        ("thejournal",          scrape_thejournal),
        ("rte",                 scrape_rte),
        # Top-10 research adds (2026-06) — INTO introduces a new "union"
        # category that triggers NMF retrain per pipeline_decisions.md §14.
        # INTO covers both irl + ni; classified under irl (HQ jurisdiction).
        ("into",                    make_wp_scraper("https://www.into.ie/wp-json/wp/v2/posts")),
        ("education_magazine_irl",  make_wp_scraper("https://educationmagazine.ie/wp-json/wp/v2/posts")),
    ],
    "wal": [
        # Wales is a brand-new jurisdiction (added 2026-06). Top-10 research adds.
        ("iwa",     make_wp_scraper("https://www.iwa.wales/wp-json/wp/v2/posts")),
        ("wiserd",  make_wp_scraper("https://wiserd.ac.uk/wp-json/wp/v2/posts")),
    ],
    "ni": [
        # Northern Ireland is a brand-new jurisdiction (added 2026-06). Top-10 research adds.
        ("niccy",   make_wp_scraper("https://www.niccy.org/wp-json/wp/v2/posts")),
    ],
}

# Metadata added to merged output — extend when Scotland/Ireland sources are added
SOURCE_META = {
    "schoolsweek": {"country": "eng", "type": "ed_media",       "institution_name": "Schools Week"},
    "gov":         {"country": "eng", "type": "government",    "institution_name": None},  # uses primary_org
    "epi":         {"country": "eng", "type": "think_tank",    "institution_name": "Education Policy Institute"},
    "nuffield":    {"country": "eng", "type": "funder",        "institution_name": "Nuffield Foundation"},
    "fft":         {"country": "eng", "type": "research_org",  "institution_name": "FFT Education Datalab"},
    "fed":         {"country": "eng", "type": "prof_body",     "institution_name": "Foundation for Educational Development"},
    # Scotland
    "gov_scot":              {"country": "sco", "type": "government",      "institution_name": "Scottish Government"},
    "sera":                  {"country": "sco", "type": "think_tank",      "institution_name": "SERA"},
    "gtcs":                  {"country": "sco", "type": "prof_body",       "institution_name": "GTCS"},
    "ades":                  {"country": "sco", "type": "prof_body",       "institution_name": "ADES"},
    "children_in_scotland":  {"country": "sco", "type": "civil_society",   "institution_name": "Children in Scotland"},
    # Ireland
    "gov_ie":             {"country": "irl", "type": "government",    "institution_name": "Department of Education (Ireland)"},
    "esri":               {"country": "irl", "type": "think_tank",    "institution_name": "ESRI"},
    "erc":                {"country": "irl", "type": "research_org",  "institution_name": "Educational Research Centre"},
    "teaching_council":   {"country": "irl", "type": "prof_body",     "institution_name": "Teaching Council"},
    "education_matters":  {"country": "irl", "type": "ed_media",      "institution_name": "Education Matters"},
    "thejournal":         {"country": "irl", "type": "ed_media",      "institution_name": "TheJournal.ie"},
    "rte":                {"country": "irl", "type": "ed_media",      "institution_name": "RTÉ News"},
    # New WordPress sources (England)
    "sutton_trust":              {"country": "eng", "type": "think_tank",    "institution_name": "Sutton Trust"},
    "childrens_commissioner_eng": {"country": "eng", "type": "government",   "institution_name": "Children's Commissioner for England"},
    "teacher_tapp":              {"country": "eng", "type": "ed_media",      "institution_name": "Teacher Tapp"},
    "jacobs_foundation":         {"country": "eng", "type": "funder",        "institution_name": "Jacobs Foundation"},
    "cfey":                      {"country": "eng", "type": "think_tank",    "institution_name": "Centre for Education and Youth"},
    "ippo":                      {"country": "eng", "type": "research_org",  "institution_name": "International Public Policy Observatory"},
    "defend_digital_me":         {"country": "eng", "type": "civil_society", "institution_name": "defenddigitalme"},
    "tpea":                      {"country": "eng", "type": "prof_body",     "institution_name": "Teacher Performance Evaluation Academy (TPEA)"},
    "lpip_hub":                  {"country": "eng", "type": "research_org",  "institution_name": "Local Policy Innovation Partnership Hub (University of Birmingham)"},
    "oii_edtech":                {"country": "eng", "type": "research_org",  "institution_name": "Oxford Internet Institute - EdTech research (Prof Rebecca Eynon)"},
    "ucl_cepeo_blog":            {"country": "eng", "type": "research_org",  "institution_name": "UCL Centre for Education Policy and Equalising Opportunities (CEPEO)"},
    "ucl_ioe_blog":              {"country": "eng", "type": "research_org",  "institution_name": "UCL Institute of Education (IOE) blog"},
    # New WordPress sources (Scotland)
    "spice_spotlight":           {"country": "sco", "type": "government",    "institution_name": "SPICe - Scottish Parliament Information Centre"},
    "scot_gov_digital_blog":     {"country": "sco", "type": "government",    "institution_name": "Scottish Government Digital Directorate"},
    # Top-10 research adds (2026-06)
    # NB: "regulator" and "union" are NEW category codes not in pipeline_decisions.md §15.
    # Per §14, adding union/parliament/advocacy categories triggers an NMF retrain in the
    # analysis repo — coordinate before promoting these into the next training cut.
    "fe_week":                {"country": "eng", "type": "ed_media",      "institution_name": "FE Week"},
    "hepi":                   {"country": "eng", "type": "think_tank",    "institution_name": "Higher Education Policy Institute (HEPI)"},
    "ofqual_blog":            {"country": "eng", "type": "regulator",     "institution_name": "Ofqual blog"},
    "ofsted_inspection":      {"country": "eng", "type": "regulator",     "institution_name": "Ofsted Education Inspection blog"},
    "enlighten":              {"country": "sco", "type": "think_tank",    "institution_name": "Enlighten (Reform Scotland)"},
    "iwa":                    {"country": "wal", "type": "think_tank",    "institution_name": "Institute of Welsh Affairs (IWA)"},
    "wiserd":                 {"country": "wal", "type": "research_org",  "institution_name": "Wales Institute of Social and Economic Research and Data (WISERD)"},
    "niccy":                  {"country": "ni",  "type": "civil_society", "institution_name": "Northern Ireland Commissioner for Children and Young People (NICCY)"},
    "into":                   {"country": "irl", "type": "union",         "institution_name": "Irish National Teachers' Organisation (INTO — covers irl + ni)"},
    "education_magazine_irl": {"country": "irl", "type": "ed_media",      "institution_name": "Education Magazine (Ireland)"},
}

FINAL_COLS = ["url", "title", "date", "text", "source", "country", "type", "institution_name", "language"]


# ----------------------------------------------------------
# Post-processing: title-only HE filter + language flagging
# ----------------------------------------------------------
# Simple rule: remove article only if title contains an HE term
# AND title does NOT contain a school-level term.
# This preserves articles about both levels (e.g. "Leaving Cert and CAO").

TITLE_HE_TERMS = [
    "university", "universities", "college fees", "college ranking",
    "undergraduate", "postgraduate", "phd", "doctoral",
    "campus", "tuition fees", "university ranking",
    "lecturer", "lecturers", "higher education",
    "third level", "third-level",
]

TITLE_SCHOOL_TERMS = [
    "school", "schools", "teacher", "teachers", "pupil", "pupils",
    "principal", "classroom", "headteacher", "head teacher",
    "leaving cert", "junior cycle", "senior cycle", "transition year",
    "junior cert", "sna", "special needs assistant", "deis",
    "national school", "post-primary", "special school",
    "school meals", "school transport", "school building",
    "school staff", "school secretary", "school closure",
    "curriculum", "inspectorate", "enrolment",
    "primary", "secondary", "education minister",
    # Scotland
    "curriculum for excellence", "additional support needs",
]

# Irish language indicators — common Irish function words
# An article with 8+ of these in the body is likely fully in Irish.
# Articles with fewer are English articles using occasional Irish terms.
IRISH_INDICATORS = [
    " agus ", " na ", " ar ", " le ", " do ", " sa ", " den ",
    " ag ", " ón ", " go ", " tá ", " bhí ", " seo ", " sin ",
    " scoil ", " oideachas ", " gaeilge ", " múinteoirí ",
    " an t", " i g", " i m", " i n", " i d", " i b",
]
IRISH_THRESHOLD = 8  # need 8+ matches to flag as Irish


def _postprocess(df):
    """Clean inference data: drop empty text, title-only HE filter, flag language, dedupe."""
    # 1. Drop empty text
    before = len(df)
    df = df.dropna(subset=["text"])
    df = df[df["text"].astype(str).str.strip() != ""]
    print(f"  Dropped {before - len(df)} empty-text rows → {len(df)}")

    # 2. Title-only HE filter
    before = len(df)
    df = df.copy()

    def _should_remove(title):
        t = str(title).lower()
        has_he = any(term in t for term in TITLE_HE_TERMS)
        if not has_he:
            return False
        has_school = any(term in t for term in TITLE_SCHOOL_TERMS)
        return not has_school  # remove only if HE in title AND no school term

    mask = df["title"].apply(_should_remove)
    removed_df = df[mask]
    if len(removed_df) > 0:
        print(f"  HE title removals:")
        for _, row in removed_df.head(10).iterrows():
            print(f"    {row.get('source','')} | {str(row.get('title',''))[:70]}")
    df = df[~mask]
    print(f"  Education filter: {before} → {len(df)} (removed {before - len(df)})")

    # 3. Language flagging (word-frequency, not langdetect)
    def _detect_lang(text):
        t = str(text).lower()
        if len(t) < 50:
            return "en"
        matches = sum(1 for term in IRISH_INDICATORS if term in t)
        return "ga" if matches >= IRISH_THRESHOLD else "en"

    df["language"] = df["text"].apply(_detect_lang)
    non_en = df[df["language"] != "en"]
    if len(non_en) > 0:
        print(f"  Non-English articles: {non_en['language'].value_counts().to_dict()}")
    else:
        print(f"  All articles detected as English")

    # 4. Deduplicate
    before = len(df)
    df = df.drop_duplicates(subset=["url"])
    if before - len(df) > 0:
        print(f"  Deduped: {before} → {len(df)}")

    return df


def parse_args():
    parser = argparse.ArgumentParser(description="Education Policy Scraper")
    parser.add_argument(
        "--country",
        choices=["eng", "sco", "irl", "wal", "ni", "all"],
        default="eng",
        help="Which country's sources to scrape, or 'all' for all five (default: eng).",
    )
    parser.add_argument(
        "--since",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        default=None,
        help="Only scrape articles published on or after this date (YYYY-MM-DD). "
             "Omit for full retrospective scrape from this country's default start.",
    )
    parser.add_argument(
        "--until",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        default=None,
        help="Only scrape articles published on or before this date (YYYY-MM-DD). "
             f"Articles up to {TRAINING_CUTOFF} go to data/training/; "
             "later articles go to data/inference/.",
    )
    parser.add_argument(
        "--week",
        type=int,
        default=None,
        help="Week number to include in the inference output filename (e.g. --week 1 → week01_YYYY-MM-DD.csv). "
             "Only used for inference runs.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run all scrapers but write no CSVs and skip the scrape log. "
             "Prints per-source raw and post-filter counts so new sources can be sanity-checked.",
    )
    return parser.parse_args()


def _enrich(rows, name):
    """Add source / country / type / institution_name columns to a list of row dicts."""
    if not rows:
        return None
    df = pd.DataFrame(rows)
    meta = SOURCE_META[name]
    df["source"] = name
    df["country"] = meta["country"]
    df["type"] = meta["type"]
    if name == "gov":
        if "core_education" in df.columns:
            df = df[df["core_education"] == True].copy()
        df["institution_name"] = df["primary_org"] if "primary_org" in df.columns else "Government"
    else:
        df["institution_name"] = meta["institution_name"]
    return df[[c for c in FINAL_COLS if c in df.columns]]


def _write_scrape_log(inference_dir, since_date, until_date, filename, frames, country):
    from datetime import datetime
    log_path = ROOT / "docs" / "scrape_log.md"
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    since_str = since_date.strftime("%Y-%m-%d")
    until_str = until_date.strftime("%Y-%m-%d") if until_date else "present"
    total = sum(len(f) for f in frames)

    counts = {f["source"].iloc[0]: len(f) for f in frames if "source" in f.columns}
    source_summary = ", ".join(f"{s}={n}" for s, n in counts.items())

    row = f"| {run_time} | {country} | {since_str} → {until_str} | {filename} | {source_summary} | **{total}** |\n"

    if not log_path.exists():
        header = (
            "# Inference Scrape Log\n\n"
            "| Run time | Country | Date range | File | Sources | Total |\n"
            "|----------|---------|------------|------|---------|-------|\n"
        )
        log_path.write_text(header + row)
    else:
        with open(log_path, "a") as f:
            f.write(row)

    print(f"📋 Scrape log updated → {log_path}")


def _validate_inference(df, filename):
    """Basic sanity checks on a merged inference CSV. Prints warnings but does not exit."""
    issues = []

    missing_cols = [c for c in FINAL_COLS if c not in df.columns]
    if missing_cols:
        issues.append(f"missing columns: {missing_cols}")

    empty_text = df["text"].isna().sum() + (df["text"].str.strip() == "").sum()
    if empty_text:
        issues.append(f"{empty_text} rows have empty text")

    if len(df) == 0:
        issues.append("no articles — check scrapers")
    elif len(df) < 5:
        issues.append(f"only {len(df)} articles — unusually low, verify sources")

    if issues:
        print(f"\n⚠️  Validation warnings for {filename}:")
        for issue in issues:
            print(f"   • {issue}")
    else:
        print(f"✅ Validation passed: {len(df)} articles, all columns present, no empty text")


def _run_country(country, args):
    """Run the scraping pipeline for a single country."""
    country_dir = COUNTRY_DIR[country]
    since_date = args.since or RETROSPECTIVE_START[country]
    until_date = args.until

    if args.since is None:
        print(f"MODE A — retrospective scrape [{country}] from {since_date}")
    else:
        print(f"MODE B/C — incremental scrape [{country}] {since_date} → {until_date or 'present'}")

    # Scotland and Ireland always go to inference (Phase 1)
    # England goes to training if until_date <= TRAINING_CUTOFF, otherwise inference
    if country not in TRAINING_COUNTRIES:
        is_training = False
    else:
        is_training = until_date is None or until_date <= TRAINING_CUTOFF

    training_dir = DATA_ROOT / "training" / country_dir
    inference_dir = DATA_ROOT / "inference" / country_dir
    output_dir = training_dir if is_training else inference_dir
    dry_run = getattr(args, "dry_run", False)
    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    append = is_training and args.since is not None

    mode_label = (
        "training (append)"    if append else
        "training (overwrite)" if is_training else
        "inference → one merged file"
    )
    if dry_run:
        mode_label = f"DRY-RUN ({mode_label})"
    print(f"Output  → {output_dir}  [{mode_label}]")

    scrapers = SCRAPERS.get(country, [])
    if not scrapers:
        print(f"⚠️  No scrapers registered for --country {country} yet.")
        return

    total = 0
    inference_frames = []

    for name, scrape_fn in scrapers:
        print(f"\n{'='*50}")
        print(f"Scraping: {name}")
        print(f"{'='*50}")
        try:
            if dry_run:
                output_path = None  # never write per-source CSVs in dry-run
            elif is_training:
                output_path = training_dir / TRAINING_FILENAMES[name]
                output_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                output_path = None  # scrapers return rows; we merge below

            rows = scrape_fn(
                since_date=since_date,
                until_date=until_date,
                output_path=output_path,
                append=append,
            )
            count = len(rows) if rows else 0
            total += count
            print(f"✅ {name}: {count} articles")

            if dry_run:
                # Per-source dry-run summary: raw vs post-filter count.
                if rows:
                    df = _enrich(rows, name)
                    raw_n = len(df) if df is not None else 0
                    if df is not None and raw_n > 0:
                        filtered = _postprocess(df)
                        post_n = len(filtered)
                    else:
                        post_n = 0
                    print(f"[DRY-RUN] {name}: raw={raw_n} post_filter={post_n}")
                else:
                    print(f"[DRY-RUN] {name}: raw=0 post_filter=0")
            elif not is_training and rows:
                df = _enrich(rows, name)
                if df is not None:
                    inference_frames.append(df)

        except Exception as e:
            print(f"❌ {name} failed: {e}")

    # Write single merged inference CSV — named by week number + Friday (until_date)
    if not dry_run and not is_training and inference_frames:
        until_str = until_date.strftime("%Y-%m-%d") if until_date else "present"
        if args.week is not None:
            filename_stem = f"week{args.week:02d}_{until_str}"
        else:
            filename_stem = until_str
        out = inference_dir / f"{filename_stem}.csv"
        merged = pd.concat(inference_frames, ignore_index=True)

        # --- Post-processing ---
        print(f"\n--- Post-processing ({len(merged)} raw articles) ---")
        merged = _postprocess(merged)

        merged.to_csv(out, index=False)
        print(f"\n✅ Wrote {len(merged)} articles to {out}")
        _write_scrape_log(inference_dir, since_date, until_date, out.name, inference_frames, country)
        _validate_inference(merged, out.name)

    print(f"\n{'='*50}")
    print(f"Done. Total articles scraped: {total}")
    if is_training:
        print("Next step: run merge.py to update data/training/training_data.csv")


def main():
    args = parse_args()
    if args.country == "all":
        for country in ["eng", "irl", "sco", "wal", "ni"]:
            print(f"\n{'#'*60}")
            print(f"# COUNTRY: {country.upper()}")
            print(f"{'#'*60}")
            _run_country(country, args)
    else:
        _run_country(args.country, args)


if __name__ == "__main__":
    main()
