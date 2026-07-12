"""
Shared constants: category labels, colors, source labels, brand colors.

Note: DATA_DIR removed 2026-05-17 - dashboard now reads from Supabase
`v_dashboard` view (see dashboard/data.py), not local CSV.
"""

# These MUST match the MS Form's "Which section…" dropdown values EXACTLY — the
# dashboard's Excel export is pasted into the Form spreadsheet, and a non-matching
# section value fails the Form's validation (Gemma, 2026-06). Verified against
# experiments/agent_draft/ERPNewsletterSubmissions_June.xlsx. The en-dashes in the Research
# label are the Form's official punctuation, so they're required here.
CATEGORY_LABELS = {
    "teacher_rrd": "Teacher recruitment, retention and development",
    "edtech": "Edtech",
    "political_environment_key_organisations": "Political environment and key organisations",
    "four_nations": "Four Nations",
    "policy_practice_research": "Research – Practice – Policy",
    "what_matters_ed": "What matters in education?",
}

CATEGORY_ORDER = [
    "teacher_rrd",
    "edtech",
    "political_environment_key_organisations",
    "four_nations",
    "policy_practice_research",
    "what_matters_ed",
]

# Short labels used on the Select Categories buttons - full CATEGORY_LABELS
# names ("Political environment and key organisations" etc.) make Top 1 /
# Top 2 buttons enormous because they wrap to three lines.
CATEGORY_SHORT_LABELS = {
    "teacher_rrd":                            "Teacher RRD",
    "edtech":                                 "EdTech",
    "political_environment_key_organisations":"Politics & key orgs",
    "four_nations":                           "Four Nations",
    "policy_practice_research":               "Research/Practice/Policy",
    "what_matters_ed":                        "What matters",
}

CATEGORY_COLORS = {
    "edtech": "#5b9bd5",
    "four_nations": "#70ad47",
    "policy_practice_research": "#7b7fb5",
    "political_environment_key_organisations": "#4472c4",
    "teacher_rrd": "#ed7d31",
    "what_matters_ed": "#44b4a6",
}

# Friendly organisation names for the `source` value on each article.
# Keys MUST match the raw values in articles.source (mix of internal keys and
# domains). Curators see these names on every page (Gemma asked for org names,
# not raw URLs/keys). Some sources appear in both an internal-key and a domain
# form, so both are mapped to the same name.
SOURCE_LABELS = {
    # News / media
    "schoolsweek": "Schools Week",
    "schoolsweek.co.uk": "Schools Week",
    "tes.com": "TES",
    "bbc.co.uk": "BBC",
    "theguardian.com": "The Guardian",
    "belfast_telegraph": "Belfast Telegraph",
    "belfasttelegraph.co.uk": "Belfast Telegraph",
    # UK government / parliament / regulators
    "gov.uk": "GOV.UK",
    "dfe": "Department for Education",
    "ofsted": "Ofsted",
    "committees.parliament.uk": "UK Parliament Committees",
    "post_parliament": "POST (UK Parliament)",
    # Scotland
    "gov_scot": "Scottish Government",
    "gov.scot": "Scottish Government",
    "scotland_digital_blog": "Scottish Government (Digital)",
    "scotland_scottish_parliament_blog": "Scottish Parliament",
    "gtcs": "General Teaching Council for Scotland",
    "ades": "Association of Directors of Education in Scotland (ADES)",
    "sera": "Scottish Educational Research Association",
    "children_in_scotland": "Children in Scotland",
    # Wales
    "gov.wales": "Welsh Government",
    "wales_centre_for_public_policy": "Wales Centre for Public Policy",
    # Northern Ireland
    "education-ni.gov.uk": "Department of Education (NI)",
    # Unions / sector bodies
    "ascl": "ASCL (School & College Leaders)",
    "neu.org.uk": "National Education Union",
    "lga": "Local Government Association",
    "local.gov.uk": "Local Government Association",
    # Media
    "bbc_education": "BBC",
    # Research / think tanks / foundations
    "fft_datalab": "FFT Education Datalab",
    "epi": "Education Policy Institute",
    "nfer": "National Foundation for Educational Research",
    "nuffield": "Nuffield Foundation",
    "sutton_trust": "Sutton Trust",
    "institute_for_government": "Institute for Government",
    "jacobs_foundation": "Jacobs Foundation",
    "joseph_rowntree_foundation": "Joseph Rowntree Foundation",
    "fed": "Foundation for Education Development",
    "lpips": "Local Policy Innovation Partnership (LPIP) Hub",
    # Children / digital rights
    "children_s_commissioner": "Children's Commissioner",
    "childrenscommissioner.gov.uk": "Children's Commissioner",
    "defend_digital_me": "Defend Digital Me",
    "digital_poverty_alliance": "Digital Poverty Alliance",
    # UCL / academics
    "ucl.ac.uk": "UCL",
    "ucl_ioe_blog": "UCL Institute of Education",
    "ucl_ioe_news": "UCL Institute of Education",
    "ucl_research_for_the_real_world_ioe_podcast": "UCL Institute of Education",
    "professor_rebecca_eynon": "Professor Rebecca Eynon",
    "teacher_tapp": "Teacher Tapp",
}

_TLDS = (".co.uk", ".org.uk", ".gov.uk", ".ac.uk", ".com", ".org", ".uk", ".net")


def source_label(src) -> str:
    """Friendly organisation name for a source value.

    Looks up SOURCE_LABELS; for any unmapped source, prettifies (strip TLD,
    underscores/dots → spaces, title-case) so a raw key or domain is NEVER shown
    to curators again. Returns '' for null-ish input.
    """
    if src is None:
        return ""
    s = str(src).strip()
    if not s or s.lower() in {"nan", "none", "nat"}:
        return ""
    if s in SOURCE_LABELS:
        return SOURCE_LABELS[s]
    base = s
    for tld in _TLDS:
        if base.lower().endswith(tld):
            base = base[: -len(tld)]
            break
    base = base.replace("_", " ").replace(".", " ").strip()
    return base.title() if base else s

# ESRC brand colours
NAVY = "#0f1e3d"
TEAL = "#44b4a6"
LIGHT_BLUE = "#5b9bd5"
MID_BLUE = "#1d3461"

# MS Form URL - Page 1 "Add article" hyperlink. Curators fill the form
# externally; submissions are stored in MS only for now (post-AM2: sync
# back into Supabase).
MS_FORM_URL = "https://forms.office.com/Pages/ResponsePage.aspx?id=_oivH5ipW0yTySEKEdmlwtqBMy17V29Hgbgj295AyCRUNDZDWlJaWUU1V1VKNjRVUThPMklOOVRSWiQlQCN0PWcu"
