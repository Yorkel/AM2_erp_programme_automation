"""
nations.py
Single source of truth for mapping a source -> UK nation code.

Used to populate the `articles.country` column at scrape time (in common.to_record)
so new articles get the right nation instead of falling back to the DB default 'eng'.
The same mapping seeds the one-off backfill and the notebook nation analysis.

Codes: eng | sco | wal | nir | uk   (uk = UK-wide / cross-nation body).
Both source forms are covered: the configured slug (e.g. `gov_scot`) and the raw
domain that Google Alerts records via `_domain_as_source` (e.g. `gov.scot`).
Unknown sources default to 'uk' (still passes the all-UK inference filter; re-map later).
"""

from __future__ import annotations

UK_NATIONS = ("eng", "sco", "wal", "nir", "uk")

SOURCE_NATION: dict[str, str] = {
    # Scotland (slugs + the domains Google Alerts records via _domain_as_source)
    "ades": "sco", "children_in_scotland": "sco", "gov_scot": "sco", "gov.scot": "sco",
    "gtcs": "sco", "scotland_digital_blog": "sco",
    "scotland_scottish_parliament_blog": "sco", "sera": "sco",
    "scotland_news": "sco", "education_scotland_alert": "sco", "cosla_alert": "sco",
    "scotland_scottish_parliament_news": "sco",
    "parliament.scot": "sco", "spice-spotlight.scot": "sco", "blogs.gov.scot": "sco",
    "education.gov.scot": "sco", "cosla.gov.uk": "sco",
    # Wales (slugs + Google-Alert domain forms)
    "wales_centre_for_public_policy": "wal",
    "welsh_government": "wal", "wales_education": "wal", "wlga_alert": "wal",
    "gov.wales": "wal", "senedd.wales": "wal", "hwb.gov.wales": "wal", "wlga.wales": "wal",
    # Northern Ireland
    "belfast_telegraph": "nir", "belfasttelegraph.co.uk": "nir", "education-ni.gov.uk": "nir",
    "nilga_alert": "nir", "deni_dept_education_ni_alert": "nir",
    "ni_ni_executive_publications": "nir",
    "nilga.org": "nir", "northernireland.gov.uk": "nir",
    # England (England-only education bodies)
    "dfe": "eng", "ofsted": "eng", "schoolsweek": "eng", "schoolsweek.co.uk": "eng",
    "ascl": "eng", "neu.org.uk": "eng", "epi": "eng", "fft_datalab": "eng",
    "sutton_trust": "eng", "fed": "eng", "children_s_commissioner": "eng",
    "childrenscommissioner.gov.uk": "eng", "teacher_tapp": "eng", "lga": "eng",
    "local.gov.uk": "eng", "lpips": "eng",
    # UK-wide (cross-UK bodies / national media / research)
    "bbc.co.uk": "uk", "gov.uk": "uk", "theguardian.com": "uk", "tes.com": "uk",
    "nuffield": "uk", "joseph_rowntree_foundation": "uk", "jacobs_foundation": "uk",
    "digital_poverty_alliance": "uk", "defend_digital_me": "uk", "ucl.ac.uk": "uk",
    "ucl_ioe_blog": "uk", "ucl_ioe_news": "uk",
    "ucl_research_for_the_real_world_ioe_podcast": "uk", "professor_rebecca_eynon": "uk",
    "committees.parliament.uk": "uk", "post_parliament": "uk",
}


def nation_for_source(source: str | None) -> str:
    """Return the UK nation code for a source slug or domain. Unknown -> 'uk'."""
    if not source:
        return "uk"
    return SOURCE_NATION.get(source, "uk")
