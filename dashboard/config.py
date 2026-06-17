"""
Shared constants: category labels, colors, source labels, brand colors.

Note: DATA_DIR removed 2026-05-17 - dashboard now reads from Supabase
`v_dashboard` view (see dashboard/data.py), not local CSV.
"""

CATEGORY_LABELS = {
    "teacher_rrd": "Teacher recruitment, retention & development",
    "edtech": "EdTech",
    "political_environment_key_organisations": "Political environment and key organisations",
    "four_nations": "Four Nations",
    "policy_practice_research": "Research, Practice, Policy",
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

SOURCE_LABELS = {
    "schoolsweek": "Schools Week",
    "gov": "GOV.UK",
    "fft": "FFT Education Datalab",
    "fed": "Further Education Development",
    "epi": "Education Policy Institute",
    "tes": "TES",
    "nfer": "National Foundation for Educational Research",
    "ofsted": "Ofsted",
    "sutton_trust": "Sutton Trust",
    "bbc": "BBC",
    "guardian": "The Guardian",
}

# ESRC brand colours
NAVY = "#0f1e3d"
TEAL = "#44b4a6"
LIGHT_BLUE = "#5b9bd5"
MID_BLUE = "#1d3461"

# MS Form URL - Page 1 "Add article" hyperlink. Curators fill the form
# externally; submissions are stored in MS only for now (post-AM2: sync
# back into Supabase).
MS_FORM_URL = "https://forms.office.com/Pages/ResponsePage.aspx?id=_oivH5ipW0yTySEKEdmlwtqBMy17V29Hgbgj295AyCRUNDZDWlJaWUU1V1VKNjRVUThPMklOOVRSWiQlQCN0PWcu"
