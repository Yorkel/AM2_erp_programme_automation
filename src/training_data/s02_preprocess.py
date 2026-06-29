"""
s02_preprocess.py
Takes cleaned newsletter data and adds:
  - Standardised theme (new_theme)
  - Domain extraction
  - Organisation mapping
  - Organisation broad/specific category
  - Item type (article, academic_article, video, tweet, etc.)
  - Combined text feature

Input:  data/interim/newsletters_cleaned.csv
Output: data/preprocessed/newsletters_preprocessed.csv
"""

import re
from urllib.parse import urlparse

import pandas as pd

# -----------------------------
# CONFIG
# -----------------------------
INPUT_CSV  = "data/interim/newsletters_cleaned.csv"
OUTPUT_CSV = "data/preprocessed/newsletters_preprocessed.csv"

UNSUB_THEME = (
    "You have indicated that you are happy to receive news and updates from the "
    "ESRC Education Research Programme. To unsubscribe, please email the "
    "programme contact address with the word UNSUBSCRIBE in the title of the email."
)


# -----------------------------
# LOOKUP TABLES
# -----------------------------

# Raw theme → standardised theme
THEME_PAIRS = [
    # update_from_programme
    ("update_from_programme", "Programme Update"),
    ("update_from_programme", "Programme news"),
    ("update_from_programme", "Programme update"),
    ("update_from_programme", "Updates from the Programme"),
    ("update_from_programme", "Updates from the programme"),
    ("update_from_programme", "Update from the ESRC Education Research Programme"),
    ("update_from_programme", "Updates from the ESRC"),
    ("update_from_programme", "Conferences"),
    ("update_from_programme", "Events"),
    ("update_from_programme", "Opportunities"),
    ("update_from_programme", "Opportunities for funding"),
    ("update_from_programme", "Opportunities to blog"),
    ("update_from_programme", "Relevant Events"),
    ("update_from_programme", "Seminar series topics"),
    ("update_from_programme", "Seminar topics"),

    # update_from_pi
    ("update_from_pi", "PI Updates and Papers"),
    ("update_from_pi", "PI: David Lundie"),
    ("update_from_pi", "Toby Greany"),
    ("update_from_pi", "News from the Projects"),
    ("update_from_pi", "News from the projects"),
    ("update_from_pi", "Project news"),
    ("update_from_pi", "Update from the ERP projects"),
    ("update_from_pi", "Update from the projects"),
    ("update_from_pi", "Updates from David Lundie"),
    ("update_from_pi", "Updates from Steph Ainsworth"),
    ("update_from_pi", "Updates from the ERP projects"),
    ("update_from_pi", "Updates from the projects"),
    ("update_from_pi", "Embedding children's participation rights in pedagogical practice in lower primary classrooms in Wales PI: Sarah Chicken"),
    ("update_from_pi", "Investigating the recruitment and retention of ethnic minority teachers PI: Stephen Gorard"),
    ("update_from_pi", "Rethinking teacher recruitment: New approaches to attracting prospective STEM teachers PI: Rob Klassen"),
    ("update_from_pi", "Sustainable school leadership: comparing approaches to the training, supply and retention of senior school leaders across the UK PI Toby Greany"),
    ("update_from_pi", "Towards equity focused approaches to EdTech: a socio-technical perspective PI: Professor Rebecca Eynon"),
    ("update_from_pi", "Towards equity focused approaches to EdTech: a socio-technical perspective PI: Rebecca Eynon"),
    ("update_from_pi", "Decentring the 'resilient teacher': exploring interactions between individuals and their social ecologies PI: Steph Ainsworth"),
    ("update_from_pi", "Peer reviewed articles from the ERP projects"),
    ("update_from_pi", "Peer reviewed publications from the ERP projects"),
    ("update_from_pi", "Updates from Stephen Gorard"),
    ("update_from_pi", "Updates from Toby Greany"),
    ("update_from_pi", "Updates from Sarah Chicken"),
    ("update_from_pi", "Updates from PI Steven Gorard"),
    ("update_from_pi", "Update from PI Stephanie Ainsworth"),
    ("update_from_pi", "Updates from PI Sarah Chicken"),
    ("update_from_pi", "Update from PI Robert Klassen"),
    ("update_from_pi", "Update from PI David Lundie"),
    ("update_from_pi", "Update from PI Alison Porter"),
    ("update_from_pi", "Update from PI Toby Greany"),
    ("update_from_pi", "Update from PI Stephen Gorard"),
    ("update_from_pi", "Update from PI John Gordon"),
    ("update_from_pi", "Update from PI Rebecca Eynon"),

    # what_matters_ed
    ("what_matters_ed", "What Matters in Education?"),
    ("what_matters_ed", "What matters in education?"),

    # teacher_rrd
    ("teacher_rrd", "Teacher recruitment, retention & development"),

    # edtech
    ("edtech", "EdTech"),

    # four_nations
    ("four_nations", "4 Nations"),
    ("four_nations", "4 Nations & key organisations"),
    ("four_nations", "Four Nations"),
    ("four_nations", "Four Nations Landscape"),
    ("four_nations", "Four Nations landscape"),
    ("four_nations", "Four nations"),
    ("four_nations", "Political landscape across Four Nations & key organisations"),

    # policy_practice_research
    ("policy_practice_research", "Research \u2013 Practice \u2013 Policy"),
    ("policy_practice_research", "Education, Policy & Practice"),
    ("policy_practice_research", "Calls for evidence"),
    ("policy_practice_research", "Other Reports"),
    ("policy_practice_research", "Other Research"),
    ("policy_practice_research", "Relevant Research"),
    ("policy_practice_research", "Reports"),
    ("policy_practice_research", "Research"),

    # political_environment_key_organisations
    ("political_environment_key_organisations", "What are the politicians saying?"),
    ("political_environment_key_organisations", "Political environment and key organisations"),
    ("political_environment_key_organisations", "Political landscape - the election"),
    ("political_environment_key_organisations", "Political landscape & key organisations"),
    ("political_environment_key_organisations", "DfE"),
    ("political_environment_key_organisations", "EEF"),
    ("political_environment_key_organisations", "ESRC"),
    ("political_environment_key_organisations", "Politics"),
    ("political_environment_key_organisations", "Launch of ESRC survey on social science research skills"),
    ("political_environment_key_organisations", "Updates from UKRI"),
    ("political_environment_key_organisations", "Update from UKRI"),
]

DOMAIN_TO_ORG = {
    "schoolsweek.co.uk": "schools_week",
    "www.gov.uk": "uk_government",
    "assets.publishing.service.gov.uk": "uk_government",
    "educationhub.blog.gov.uk": "uk_government",
    "publicpolicydesign.blog.gov.uk": "uk_government",
    "openpolicy.blog.gov.uk": "uk_government",
    "explore-education-statistics.service.gov.uk": "uk_government",
    "consult.education.gov.uk": "uk_government",
    "teaching-vacancies.service.gov.uk": "uk_government",
    "deprivation.communities.gov.uk": "uk_government",
    "fellows.ai.gov.uk": "uk_government",
    "www.gov.scot": "scottish_government",
    "blogs.gov.scot": "scottish_government",
    "www.gov.wales": "welsh_government",
    "educationwales.blog.gov.wales": "welsh_government",
    "hwb.gov.wales": "welsh_government",
    "www.medr.cymru": "welsh_government",
    "www.education-ni.gov.uk": "ni_government",
    "www.economy-ni.gov.uk": "ni_government",
    "www.health-ni.gov.uk": "ni_government",
    "committees.parliament.uk": "uk_parliament",
    "commonslibrary.parliament.uk": "uk_parliament",
    "hansard.parliament.uk": "uk_parliament",
    "lordslibrary.parliament.uk": "uk_parliament",
    "post.parliament.uk": "uk_parliament",
    "publications.parliament.uk": "uk_parliament",
    "researchbriefings.files.parliament.uk": "uk_parliament",
    "www.parliament.uk": "uk_parliament",
    "whatson.parliament.uk": "uk_parliament",
    "parliamentlive.tv": "uk_parliament",
    "senedd.wales": "welsh_parliament",
    "business.senedd.wales": "welsh_parliament",
    "research.senedd.wales": "welsh_parliament",
    "www.parliament.scot": "scottish_parliament",
    "education.gov.scot": "education_scotland",
    "educationinspection.blog.gov.uk": "ofsted_blog",
    "www.oecd.org": "oecd",
    "www.oecd-ilibrary.org": "oecd",
    "newsletter.oecd.org": "oecd",
    "www.oecd-events.org": "oecd",
    "oecdedutoday.com": "oecd",
    "one.oecd.org": "oecd",
    "www.ucl.ac.uk": "ucl",
    "blogs.ucl.ac.uk": "ucl",
    "mediacentral.ucl.ac.uk": "ucl",
    "discovery.ucl.ac.uk": "ucl",
    "profiles.ucl.ac.uk": "ucl",
    "uclpress.scienceopen.com": "ucl",
    "doi-org.libproxy.ucl.ac.uk": "ucl",
    "www-nature-com.libproxy.ucl.ac.uk": "ucl",
    "ucl.us20.list-manage.com": "ucl",
    "blogs.uwe.ac.uk": "uwe_bristol_blog",
    "www.uwe.ac.uk": "uwe_bristol_blog",
    "www.bera.ac.uk": "bera",
    "bera.us9.list-manage.com": "bera",
    "bera-journals.onlinelibrary.wiley.com": "bera_journals",
    "theconversation.com": "conversation",
    "www.theguardian.com": "guardian",
    "observer.co.uk": "guardian",
    "epi.org.uk": "epi",
    "contacts.epi.org.uk": "epi",
    "epi.us15.list-manage.com": "epi",
    "www.nfer.ac.uk": "nfer",
    "nfer.ac.uk": "nfer",
    "ffteducationdatalab.org.uk": "fft_ed_datalab",
    "ffteducationdatalab.us12.list-manage.com": "fft_ed_datalab",
    "www.nuffieldfoundation.org": "nuffield",
    "nuffieldfoundation.cmail19.com": "nuffield",
    "nuffieldfoundation.cmail20.com": "nuffield",
    "www.instituteforgovernment.org.uk": "ifg",
    "upen.ac.uk": "upen",
    "www.upen.ac.uk": "upen",
    "upen.us14.list-manage.com": "upen",
    "blog.bham.ac.uk": "university_of_birmingham",
    "www.birmingham.ac.uk": "university_of_birmingham",
    "ifs.org.uk": "ifs",
    "fed.education": "fed",
    "www.bbc.co.uk": "bbc",
    "bbc.co.uk": "bbc",
    "www.tes.com": "tes",
    "educationendowmentfoundation.org.uk": "eef",
    "my.chartered.college": "chartered_college_of_teaching",
    "chartered.college": "chartered_college_of_teaching",
    "news.chartered.college": "chartered_college_of_teaching",
    "www.childrenscommissioner.gov.uk": "childrens_commissioner",
    "www.thebritishacademy.ac.uk": "british_academy",
    "email.thebritishacademy.ac.uk": "british_academy",
    "thebritishacademyecrn.com": "british_academy",
    "teachertapp.co.uk": "teacher_tapp",
    "teachertapp.com": "teacher_tapp",
    "theippo.co.uk": "ippo",
    "www.hepi.ac.uk": "hepi",
    "www.ippr.org": "ippr",
    "ippr-org.files.svdcdn.com": "ippr",
    "www.jrf.org.uk": "joseph_rowntree_foundation",
    "www.nesta.org.uk": "nesta",
    "www.nao.org.uk": "national_audit_office",
    "news.comms.nao.org.uk": "national_audit_office",
    "www.belfasttelegraph.co.uk": "belfast_telegraph",
    "www.independent.co.uk": "independent",
    "inews.co.uk": "inews",
    "link.news.inews.co.uk": "inews",
    "wonkhe.com": "wonkhe",
    "wonkhe.cmail20.com": "wonkhe",
    "feweek.co.uk": "fe_week",
    "literacytrust.org.uk": "national_literacy_trust",
    "neu.org.uk": "national_education_union",
    "5rightsfoundation.com": "5rights_foundation",
    "www.linkedin.com": "linkedin",
    "twitter.com": "twitter",
    "x.com": "twitter",
    "www.ukri.org": "ukri",
    "gtr.ukri.org": "ukri",
    "engagementhub.ukri.org": "ukri",
    "www.adalovelaceinstitute.org": "ada_lovelace_institute",
    "www.suttontrust.com": "sutton_trust",
    "www.ascl.org.uk": "ascl",
    "ascl.org.uk": "ascl",
    "digitalpovertyalliance.org": "digital_poverty_alliance",
    "www.edge.co.uk": "edge_foundation",
    "cfey.org": "centre_for_education_and_youth",
    "srhe.ac.uk": "society_for_research_into_higher_education",
    "www.gse.harvard.edu": "harvard_graduate_school_of_education",
    "click.communications.gse.harvard.edu": "harvard_graduate_school_of_education",
    "scholar.harvard.edu": "harvard_graduate_school_of_education",
    "www.transformingsociety.co.uk": "transforming_society",
    "www.researchgate.net": "researchgate",
    "www.lse.ac.uk": "london_school_of_economics",
    "eprints.lse.ac.uk": "london_school_of_economics",
    "cep.lse.ac.uk": "centre_for_economic_performance_lse",
    "www.institute.global": "tony_blair_institute",
    "institute.global": "tony_blair_institute",
    "cpag.org.uk": "child_poverty_action_group",
    "crae.org.uk": "children_rights_alliance_england",
    "demos.co.uk": "demos",
    "wcpp.org.uk": "wales_centre_for_public_policy",
    "wcpp.us12.list-manage.com": "wales_centre_for_public_policy",
    "www.politicshome.com": "politics_home",
    "transforming-evidence.org": "transforming_evidence",
    "www.nurseryworld.co.uk": "nursery_world_magazine",
    "www.naht.org.uk": "national_association_head_teachers",
    "www.nasuwt.org.uk": "nasuwt_teachers_union",
    "ripl.uk": "research_improvement_for_policy_and_learning",
    "www.internetmatters.org": "internet_matters",
    "www.cape.ac.uk": "cape_collaboration_for_public_engagement",
    "www.coproductioncollective.co.uk": "coproduction_collective",
    "options2040.co.uk": "options_2040_project",
    "www.turing.ac.uk": "alan_turing_institute",
    "www.unicef.org": "unicef",
    "www.n8research.org.uk": "n8_research_partnership",
    "cstuk.org.uk": "charities_supporting_teachers_uk",
    "www.tandfonline.com": "taylor_and_francis",
    "insights.taylorandfrancis.com": "taylor_and_francis",
    "journals.sagepub.com": "sage_journals",
    "edtech.oii.ox.ac.uk": "oii_edtech_equity",
    "childrens-participation.org": "childrend_participation_in_schools",
    "fairnessfoundation.com": "fairness_foundation",
    "files.fairnessfoundation.com": "fairness_foundation",
    "youthendowmentfund.org.uk": "youth_endowment_fund",
    "www.teachfirst.org.uk": "teach_first",
    "niot.org.uk": "national_institute_of_teaching",
    "niot.s3.amazonaws.com": "national_institute_of_teaching",
    "www.orielsquare.co.uk": "oriel_square",
    "www.mirror.co.uk": "daily_mirror",
    "www.telegraph.co.uk": "daily_telegraph",
    "fullfact.org": "full_fact",
    "www.fenews.co.uk": "fe_news",
    "www.pearson.com": "pearson",
    "www.scottishai.com": "scottish_ai",
    "universitas21.com": "universitas_21",
    "www.unesco.org": "unesco",
    "unesdoc.unesco.org": "unesco",
    "www.educationsupport.org.uk": "education_support_charity",
    "teachingcommission.co.uk": "teaching_commission",
    "www.centreforyounglives.org.uk": "centre_for_young_lives",
    "onlinelibrary.wiley.com": "wiley",
    "el.wiley.com": "wiley",
    "www.elsevier.com": "elsevier",
    "www.sciencedirect.com": "sciencedirect",
    "researcheracademy.elsevier.com": "elsevier_researcher_academy",
    "www.mdpi.com": "mdpi_journals",
    "www.frontiersin.org": "frontiers_journal",
    "ideas.repec.org": "repec_ideas",
    "econpapers.repec.org": "repec_econpapers",
    "www.jstor.org": "jstor",
    "daily.jstor.org": "jstor_daily",
    "edarxiv.org": "education_arxiv",
    "doi.org": "doi_via_ucl_proxy",
    "www.leverhulme.ac.uk": "leverhulme_trust",
    "profbeckyallen.substack.com": "becky_allen_substack",
    "rebeccaallen.co.uk": "rebecca_allen",
    "magicsmoke.substack.com": "magicsmoke_substack",
    "samf.substack.com": "samf_substack",
    "benniekara.substack.com": "bennie_kara_substack",
    "blog.policy.manchester.ac.uk": "policy_manchester_blog",
    "acss.org.uk": "academy_of_social_sciences",
    "acss.civiplus.net": "academy_of_social_sciences",
    "nepc.colorado.edu": "national_education_policy_center",
    "www.echild.ac.uk": "echild_research_centre",
    "ari.org.uk": "ari_association_for_research_innovation",
    "www.workinglivesofteachers.com": "working_lives_of_teachers",
    "shadowpanel.uk": "shadow_panel_project",
    "news.sky.com": "sky_news",
    "www.thetimes.com": "the_times",
    "www.the-tls.co.uk": "times_literary_supplement",
    "www.yorkshirepost.co.uk": "yorkshire_post",
    "www.ft.com": "financial_times",
    "hechingerreport.org": "hechinger_report",
    "www.holyrood.com": "holyrood_magazine",
    "nation.cymru": "nation_cymru",
    "www.standard.co.uk": "evening_standard",
    "www.fda.org.uk": "fda_union",
    "sustainableschoolleadership.uk": "sustainable_school_leadership",
    "bigeducation.org": "big_education",
    "edsk.org": "edsk_think_tank",
    "uk.bettshow.com": "bett_show",
    "www.techuk.org": "tech_uk",
    "www.edtechdigest.com": "edtech_digest",
    "techbullion.com": "techbullion",
    "www.wired-gov.net": "wired_gov",
    "labourlist.org": "labour_list",
    "labour.org.uk": "labour_party",
    "www.labourtogether.uk": "labour_together",
    "www.libdems.org.uk": "liberal_democrats",
    "onthinktanks.org": "on_think_tanks",
    "www.chandlerinstitute.org": "chandler_institute",
    "issuu.com": "issuu",
    "e-estonia.com": "e_estonia",
    "www.ons.gov.uk": "office_for_national_statistics",
    "www.barnardos.org.uk": "barnardos",
    "www.magicbreakfast.com": "magic_breakfast",
    "learning.nspcc.org.uk": "nspcc_learning",
    "www.centreforsocialjustice.org.uk": "centre_for_social_justice",
    "www.centreformentalhealth.org.uk": "centre_for_mental_health",
    "media.actionforchildren.org.uk": "action_for_children",
    "play.wales": "play_wales",
    "www.childreninwales.org.uk": "children_in_wales",
    "www.qmul.ac.uk": "queen_mary_university_london",
    "www.kcl.ac.uk": "kings_college_london",
    "kingsfundmail.org.uk": "kings_fund",
    "www.ntu.ac.uk": "nottingham_trent_university",
    "dundee.onlinesurveys.ac.uk": "university_of_dundee_surveys",
    "etat.uea.ac.uk": "university_of_east_anglia",
    "www.mmu.ac.uk": "manchester_metropolitan_university",
    "www.bristol.ac.uk": "university_of_bristol",
    "www.nottingham.ac.uk": "university_of_nottingham",
    "www.eyalliance.org.uk": "early_years_alliance",
    "www.ambition.org.uk": "ambition_institute",
    "www.twinkl.co.uk": "twinkl",
    "www.ocr.org.uk": "ocr_exam_board",
    "digitalgood.net": "digital_good_network",
    "www.edtechinnovationhub.com": "edtech_innovation_hub",
    "www.edtechstrategylab.org": "edtech_strategy_lab",
    "www.atkinsrealis.com": "atkins_realis",
    "beyth.co.uk": "beyth_consultancy",
    "thestaffcollege.uk": "staff_college",
    "adcs.org.uk": "association_of_directors_of_childrens_services",
    "www.hmc.org.uk": "headmasters_and_headmistresses_conference",
    "www.nationalcrimeagency.gov.uk": "national_crime_agency",
    "downloads2.dodsmonitoring.com": "dods_monitoring",
    "mmail.dods.co.uk": "dods_monitoring",
    "lgiu.org": "local_government_information_unit",
    "www.lgcplus.com": "local_government_chronicle",
    "gamayo.co.uk": "gamayo",
    "www.rijksoverheid.nl": "dutch_government",
    "educationappg.org.uk": "education_appg",
    "www.schoolsappg.org.uk": "all_party_parliamentary_group_schools",
    "cipr.co.uk": "chartered_institute_of_public_relations",
    "upp-foundation.org": "upp_foundation",
    "researchonresearch.org": "research_on_research_institute",
    "arcinstitute.org": "arc_institute",
    "www.oxfordschoolofthought.org": "oxford_school_of_thought",
    "www.thenhsa.co.uk": "northern_health_science_alliance",
    "www.coe.int": "council_of_europe",
    "www.cambridge.org": "cambridge_university_press",
    "www.civilservicejobs.service.gov.uk": "uk_civil_service_jobs",
    "londondesignbiennale.com": "london_design_biennale",
    "the-difference.com": "the_difference",
    "www.the-difference.com": "the_difference",
    "teachersuccess.co.uk": "teacher_success",
    "inclusioninpractice.org.uk": "inclusion_in_practice",
    "www.innovate-ed.uk": "innovate_ed",
    "www.insideedgetraining.co.uk": "inside_edge_training",
    "www.funding-futures.org": "funding_futures",
    "digitalyouthindex.uk": "digital_youth_index",
    "newvisionsforeducation.org.uk": "new_visions_for_education",
    "tpea.ac.uk": "tpea_association",
    "localed2025.org.uk": "local_ed_2025",
    "lucaf.org": "lucas_education_foundation",
    # video
    "www.youtube.com": "youtube",
    "youtu.be": "youtube",
    "youtube.com": "youtube",
    "vimeo.com": "vimeo",
}

ORG_TO_CATEGORY = {
    # GOVERNMENT_PUBLIC_SECTOR
    "all_party_parliamentary_group_schools":        ("government_public_sector", "government_legislature"),
    "council_of_europe":                            ("government_public_sector", "government_legislature"),
    "dods_monitoring":                              ("government_public_sector", "government_legislature"),
    "dutch_government":                             ("government_public_sector", "government_legislature"),
    "education_scotland":                           ("government_public_sector", "government_legislature"),
    "labour_party":                                 ("government_public_sector", "government_legislature"),
    "liberal_democrats":                            ("government_public_sector", "government_legislature"),
    "local_government_chronicle":                   ("government_public_sector", "government_legislature"),
    "local_government_information_unit":            ("government_public_sector", "government_legislature"),
    "national_audit_office":                        ("government_public_sector", "government_legislature"),
    "national_crime_agency":                        ("government_public_sector", "government_legislature"),
    "ni_government":                                ("government_public_sector", "government_legislature"),
    "office_for_national_statistics":               ("government_public_sector", "government_legislature"),
    "scottish_government":                          ("government_public_sector", "government_legislature"),
    "scottish_parliament":                          ("government_public_sector", "government_legislature"),
    "uk_civil_service_jobs":                        ("government_public_sector", "government_legislature"),
    "uk_government":                                ("government_public_sector", "government_legislature"),
    "uk_parliament":                                ("government_public_sector", "government_legislature"),
    "welsh_government":                             ("government_public_sector", "government_legislature"),
    "welsh_parliament":                             ("government_public_sector", "government_legislature"),
    "ofsted_blog":                                  ("government_public_sector", "executive_non_departmental_public_body_ndpb"),
    "oecd":                                         ("government_public_sector", "international_organisation"),
    "unesco":                                       ("government_public_sector", "international_organisation"),
    "unicef":                                       ("government_public_sector", "international_organisation"),

    # ACADEMIC_SECTOR
    "harvard_graduate_school_of_education":         ("academic_sector", "universities"),
    "kings_college_london":                         ("academic_sector", "universities"),
    "london_school_of_economics":                   ("academic_sector", "universities"),
    "manchester_metropolitan_university":           ("academic_sector", "universities"),
    "nottingham_trent_university":                  ("academic_sector", "universities"),
    "queen_mary_university_london":                 ("academic_sector", "universities"),
    "ucl":                                          ("academic_sector", "universities"),
    "universitas_21":                               ("academic_sector", "universities"),
    "university_of_birmingham":                     ("academic_sector", "universities"),
    "university_of_bristol":                        ("academic_sector", "universities"),
    "university_of_dundee_surveys":                 ("academic_sector", "universities"),
    "university_of_east_anglia":                    ("academic_sector", "universities"),
    "university_of_nottingham":                     ("academic_sector", "universities"),
    "uwe_bristol_blog":                             ("academic_sector", "universities"),
    "bera_journals":                                ("academic_sector", "academic_publisher_platform"),
    "cambridge_university_press":                   ("academic_sector", "academic_publisher_platform"),
    "doi_via_ucl_proxy":                            ("academic_sector", "academic_publisher_platform"),
    "education_arxiv":                              ("academic_sector", "academic_publisher_platform"),
    "elsevier":                                     ("academic_sector", "academic_publisher_platform"),
    "elsevier_researcher_academy":                  ("academic_sector", "academic_publisher_platform"),
    "frontiers_journal":                            ("academic_sector", "academic_publisher_platform"),
    "jstor":                                        ("academic_sector", "academic_publisher_platform"),
    "jstor_daily":                                  ("academic_sector", "academic_publisher_platform"),
    "mdpi_journals":                                ("academic_sector", "academic_publisher_platform"),
    "repec_econpapers":                             ("academic_sector", "academic_publisher_platform"),
    "repec_ideas":                                  ("academic_sector", "academic_publisher_platform"),
    "researchgate":                                 ("academic_sector", "academic_publisher_platform"),
    "sage_journals":                                ("academic_sector", "academic_publisher_platform"),
    "sciencedirect":                                ("academic_sector", "academic_publisher_platform"),
    "taylor_and_francis":                           ("academic_sector", "academic_publisher_platform"),
    "wiley":                                        ("academic_sector", "academic_publisher_platform"),
    "academy_of_social_sciences":                   ("academic_sector", "academic_network"),
    "ari_association_for_research_innovation":      ("academic_sector", "academic_network"),
    "bera":                                         ("academic_sector", "academic_network"),
    "british_academy":                              ("academic_sector", "academic_network"),
    "n8_research_partnership":                      ("academic_sector", "academic_network"),
    "society_for_research_into_higher_education":   ("academic_sector", "academic_network"),

    # RESEARCH_EVIDENCE_SECTOR
    "centre_for_economic_performance_lse":          ("research_evidence_sector", "research_organisation"),
    "echild_research_centre":                       ("research_evidence_sector", "research_organisation"),
    "national_education_policy_center":             ("research_evidence_sector", "research_organisation"),
    "nfer":                                         ("research_evidence_sector", "research_organisation"),
    "northern_health_science_alliance":             ("research_evidence_sector", "research_organisation"),
    "oii_edtech_equity":                            ("research_evidence_sector", "research_organisation"),
    "oxford_school_of_thought":                     ("research_evidence_sector", "research_organisation"),
    "research_improvement_for_policy_and_learning": ("research_evidence_sector", "research_organisation"),
    "ada_lovelace_institute":                       ("research_evidence_sector", "research_institution"),
    "alan_turing_institute":                        ("research_evidence_sector", "research_institution"),
    "arc_institute":                                ("research_evidence_sector", "research_institution"),
    "kings_fund":                                   ("research_evidence_sector", "research_institution"),
    "research_on_research_institute":               ("research_evidence_sector", "research_institution"),
    "scottish_ai":                                  ("research_evidence_sector", "research_institution"),
    "coproduction_collective":                      ("research_evidence_sector", "research_project_initiative"),
    "working_lives_of_teachers":                    ("research_evidence_sector", "research_project_initiative"),
    "leverhulme_trust":                             ("research_evidence_sector", "research_funder"),
    "nuffield":                                     ("research_evidence_sector", "research_funder"),
    "ukri":                                         ("research_evidence_sector", "research_funder"),

    # CIVIL_SOCIETY_NONPROFIT_SECTOR
    "fda_union":                                    ("civil_society_nonprofit_sector", "labour_union"),
    "nasuwt_teachers_union":                        ("civil_society_nonprofit_sector", "labour_union"),
    "national_education_union":                     ("civil_society_nonprofit_sector", "labour_union"),
    "5rights_foundation":                           ("civil_society_nonprofit_sector", "charity_ngo"),
    "action_for_children":                          ("civil_society_nonprofit_sector", "charity_ngo"),
    "barnardos":                                    ("civil_society_nonprofit_sector", "charity_ngo"),
    "centre_for_mental_health":                     ("civil_society_nonprofit_sector", "charity_ngo"),
    "centre_for_social_justice":                    ("civil_society_nonprofit_sector", "charity_ngo"),
    "centre_for_young_lives":                       ("civil_society_nonprofit_sector", "charity_ngo"),
    "child_poverty_action_group":                   ("civil_society_nonprofit_sector", "charity_ngo"),
    "children_in_wales":                            ("civil_society_nonprofit_sector", "charity_ngo"),
    "children_rights_alliance_england":             ("civil_society_nonprofit_sector", "charity_ngo"),
    "childrend_participation_in_schools":           ("civil_society_nonprofit_sector", "charity_ngo"),
    "childrens_commissioner":                       ("civil_society_nonprofit_sector", "charity_ngo"),
    "digital_poverty_alliance":                     ("civil_society_nonprofit_sector", "charity_ngo"),
    "education_support_charity":                    ("civil_society_nonprofit_sector", "charity_ngo"),
    "fairness_foundation":                          ("civil_society_nonprofit_sector", "charity_ngo"),
    "internet_matters":                             ("civil_society_nonprofit_sector", "charity_ngo"),
    "joseph_rowntree_foundation":                   ("civil_society_nonprofit_sector", "charity_ngo"),
    "magic_breakfast":                              ("civil_society_nonprofit_sector", "charity_ngo"),
    "national_literacy_trust":                      ("civil_society_nonprofit_sector", "charity_ngo"),
    "nspcc_learning":                               ("civil_society_nonprofit_sector", "charity_ngo"),
    "sutton_trust":                                 ("civil_society_nonprofit_sector", "charity_ngo"),
    "youth_endowment_fund":                         ("civil_society_nonprofit_sector", "charity_ngo"),
    "ascl":                                         ("civil_society_nonprofit_sector", "professional_network"),
    "association_of_directors_of_childrens_services": ("civil_society_nonprofit_sector", "professional_network"),
    "charities_supporting_teachers_uk":             ("civil_society_nonprofit_sector", "professional_network"),
    "chartered_college_of_teaching":                ("civil_society_nonprofit_sector", "professional_network"),
    "chartered_institute_of_public_relations":      ("civil_society_nonprofit_sector", "professional_network"),
    "headmasters_and_headmistresses_conference":    ("civil_society_nonprofit_sector", "professional_network"),
    "national_association_head_teachers":           ("civil_society_nonprofit_sector", "professional_network"),
    "ambition_institute":                           ("civil_society_nonprofit_sector", "practitioner_organisation"),
    "early_years_alliance":                         ("civil_society_nonprofit_sector", "practitioner_organisation"),
    "national_institute_of_teaching":               ("civil_society_nonprofit_sector", "practitioner_organisation"),
    "play_wales":                                   ("civil_society_nonprofit_sector", "practitioner_organisation"),
    "teach_first":                                  ("civil_society_nonprofit_sector", "practitioner_organisation"),

    # KNOWLEDGE_MOBILISER_THINK_TANK_SECTOR
    "centre_for_education_and_youth":               ("knowledge_mobiliser_think_tank_sector", "think_tank"),
    "chandler_institute":                           ("knowledge_mobiliser_think_tank_sector", "think_tank"),
    "demos":                                        ("knowledge_mobiliser_think_tank_sector", "think_tank"),
    "edge_foundation":                              ("knowledge_mobiliser_think_tank_sector", "think_tank"),
    "edsk_think_tank":                              ("knowledge_mobiliser_think_tank_sector", "think_tank"),
    "epi":                                          ("knowledge_mobiliser_think_tank_sector", "think_tank"),
    "hepi":                                         ("knowledge_mobiliser_think_tank_sector", "think_tank"),
    "ifg":                                          ("knowledge_mobiliser_think_tank_sector", "think_tank"),
    "ifs":                                          ("knowledge_mobiliser_think_tank_sector", "think_tank"),
    "ippr":                                         ("knowledge_mobiliser_think_tank_sector", "think_tank"),
    "labour_together":                              ("knowledge_mobiliser_think_tank_sector", "think_tank"),
    "nesta":                                        ("knowledge_mobiliser_think_tank_sector", "think_tank"),
    "on_think_tanks":                               ("knowledge_mobiliser_think_tank_sector", "think_tank"),
    "tony_blair_institute":                         ("knowledge_mobiliser_think_tank_sector", "think_tank"),
    "wales_centre_for_public_policy":               ("knowledge_mobiliser_think_tank_sector", "think_tank"),
    "eef":                                          ("knowledge_mobiliser_think_tank_sector", "evidence_mobiliser"),
    "fft_ed_datalab":                               ("knowledge_mobiliser_think_tank_sector", "evidence_mobiliser"),
    "full_fact":                                    ("knowledge_mobiliser_think_tank_sector", "evidence_mobiliser"),
    "ippo":                                         ("knowledge_mobiliser_think_tank_sector", "evidence_mobiliser"),
    "teacher_tapp":                                 ("knowledge_mobiliser_think_tank_sector", "evidence_mobiliser"),
    "transforming_evidence":                        ("knowledge_mobiliser_think_tank_sector", "evidence_mobiliser"),
    "cape_collaboration_for_public_engagement":     ("knowledge_mobiliser_think_tank_sector", "advocacy_organisation"),
    "education_appg":                               ("knowledge_mobiliser_think_tank_sector", "advocacy_organisation"),
    "options_2040_project":                         ("knowledge_mobiliser_think_tank_sector", "advocacy_organisation"),
    "shadow_panel_project":                         ("knowledge_mobiliser_think_tank_sector", "advocacy_organisation"),
    "teaching_commission":                          ("knowledge_mobiliser_think_tank_sector", "advocacy_organisation"),

    # COMMERCIAL_PRIVATE_SECTOR
    "atkins_realis":                                ("commercial_private_sector", "consultancy"),
    "beyth_consultancy":                            ("commercial_private_sector", "consultancy"),
    "big_education":                                ("commercial_private_sector", "consultancy"),
    "oriel_square":                                 ("commercial_private_sector", "consultancy"),
    "staff_college":                                ("commercial_private_sector", "consultancy"),
    "ocr_exam_board":                               ("commercial_private_sector", "edtech_education_business"),
    "pearson":                                      ("commercial_private_sector", "edtech_education_business"),
    "twinkl":                                       ("commercial_private_sector", "edtech_education_business"),
    "bett_show":                                    ("commercial_private_sector", "industry_association"),
    "digital_good_network":                         ("commercial_private_sector", "industry_association"),
    "edtech_innovation_hub":                        ("commercial_private_sector", "industry_association"),
    "edtech_strategy_lab":                          ("commercial_private_sector", "industry_association"),
    "tech_uk":                                      ("commercial_private_sector", "industry_association"),

    # MEDIA_SECTOR
    "bbc":                                          ("media_sector", "news_media"),
    "belfast_telegraph":                            ("media_sector", "news_media"),
    "daily_mirror":                                 ("media_sector", "news_media"),
    "daily_telegraph":                              ("media_sector", "news_media"),
    "evening_standard":                             ("media_sector", "news_media"),
    "financial_times":                              ("media_sector", "news_media"),
    "guardian":                                     ("media_sector", "news_media"),
    "hechinger_report":                             ("media_sector", "news_media"),
    "holyrood_magazine":                            ("media_sector", "news_media"),
    "independent":                                  ("media_sector", "news_media"),
    "inews":                                        ("media_sector", "news_media"),
    "labour_list":                                  ("media_sector", "news_media"),
    "nation_cymru":                                 ("media_sector", "news_media"),
    "politics_home":                                ("media_sector", "news_media"),
    "sky_news":                                     ("media_sector", "news_media"),
    "the_times":                                    ("media_sector", "news_media"),
    "times_literary_supplement":                    ("media_sector", "news_media"),
    "yorkshire_post":                               ("media_sector", "news_media"),
    "edtech_digest":                                ("media_sector", "specialist_media"),
    "fe_news":                                      ("media_sector", "specialist_media"),
    "fe_week":                                      ("media_sector", "specialist_media"),
    "fed":                                          ("media_sector", "specialist_media"),
    "nursery_world_magazine":                       ("media_sector", "specialist_media"),
    "schools_week":                                 ("media_sector", "specialist_media"),
    "techbullion":                                  ("media_sector", "specialist_media"),
    "tes":                                          ("media_sector", "specialist_media"),
    "wired_gov":                                    ("media_sector", "specialist_media"),
    "wonkhe":                                       ("media_sector", "specialist_media"),
    "becky_allen_substack":                         ("media_sector", "commentary_platform"),
    "bennie_kara_substack":                         ("media_sector", "commentary_platform"),
    "conversation":                                 ("media_sector", "commentary_platform"),
    "magicsmoke_substack":                          ("media_sector", "commentary_platform"),
    "policy_manchester_blog":                       ("media_sector", "commentary_platform"),
    "rebecca_allen":                                ("media_sector", "commentary_platform"),
    "samf_substack":                                ("media_sector", "commentary_platform"),

    # DIGITAL_SOCIAL_MEDIA_PLATFORMS
    "linkedin":                                     ("digital_social_media_platforms", "social_media"),
    "twitter":                                      ("digital_social_media_platforms", "social_media"),
    "youtube":                                      ("digital_social_media_platforms", "video_platform"),
    "vimeo":                                        ("digital_social_media_platforms", "video_platform"),

    # OTHER
    "digital_youth_index":                          ("other_miscellaneous", "unclear"),
    "e_estonia":                                    ("other_miscellaneous", "government_initiative"),
    "funding_futures":                              ("other_miscellaneous", "unclear"),
    "gamayo":                                       ("other_miscellaneous", "unclear"),
    "inclusion_in_practice":                        ("other_miscellaneous", "unclear"),
    "innovate_ed":                                  ("other_miscellaneous", "unclear"),
    "inside_edge_training":                         ("other_miscellaneous", "unclear"),
    "issuu":                                        ("other_miscellaneous", "content_platform"),
    "local_ed_2025":                                ("other_miscellaneous", "unclear"),
    "london_design_biennale":                       ("other_miscellaneous", "cultural_organisation"),
    "lucas_education_foundation":                   ("other_miscellaneous", "unclear"),
    "new_visions_for_education":                    ("other_miscellaneous", "unclear"),
    "sustainable_school_leadership":                ("other_miscellaneous", "unclear"),
    "teacher_success":                              ("other_miscellaneous", "unclear"),
    "the_difference":                               ("other_miscellaneous", "unclear"),
    "tpea_association":                             ("other_miscellaneous", "unclear"),
    "transforming_society":                         ("other_miscellaneous", "unclear"),
    "upen":                                         ("other_miscellaneous", "unclear"),
    "upp_foundation":                               ("other_miscellaneous", "unclear"),
}

# item_type rules: maps (org_broad_category, org_category) → item_type
# Domain-level overrides are applied first (see classify_item_type function)
CATEGORY_TO_ITEM_TYPE = {
    ("digital_social_media_platforms", "video_platform"):      "video",
    ("digital_social_media_platforms", "social_media"):        "social_media_post",
    ("academic_sector", "academic_publisher_platform"):        "academic_article",
    ("academic_sector", "universities"):                       "academic_article",
    ("academic_sector", "academic_network"):                   "report",
    ("government_public_sector", "government_legislature"):    "government_document",
    ("government_public_sector", "executive_non_departmental_public_body_ndpb"): "government_document",
    ("government_public_sector", "international_organisation"): "report",
    ("research_evidence_sector", "research_organisation"):     "report",
    ("research_evidence_sector", "research_institution"):      "report",
    ("research_evidence_sector", "research_project_initiative"): "report",
    ("research_evidence_sector", "research_funder"):           "report",
    ("knowledge_mobiliser_think_tank_sector", "think_tank"):   "report",
    ("knowledge_mobiliser_think_tank_sector", "evidence_mobiliser"): "report",
    ("knowledge_mobiliser_think_tank_sector", "advocacy_organisation"): "report",
    ("media_sector", "news_media"):                            "news_article",
    ("media_sector", "specialist_media"):                      "news_article",
    ("media_sector", "commentary_platform"):                   "blog_post",
    ("civil_society_nonprofit_sector", "charity_ngo"):         "report",
    ("civil_society_nonprofit_sector", "labour_union"):        "report",
    ("civil_society_nonprofit_sector", "professional_network"): "report",
    ("civil_society_nonprofit_sector", "practitioner_organisation"): "report",
    ("commercial_private_sector", "consultancy"):              "report",
    ("commercial_private_sector", "edtech_education_business"): "article",
    ("commercial_private_sector", "industry_association"):     "article",
}

# Domain patterns that override category-based rules
DOMAIN_ITEM_TYPE_OVERRIDES = {
    "twitter.com":    "tweet",
    "x.com":          "tweet",
    "www.linkedin.com": "linkedin_post",
    "www.youtube.com":  "video",
    "youtu.be":         "video",
    "youtube.com":      "video",
    "vimeo.com":        "video",
}

# Substack / blog URL patterns
BLOG_PATTERNS = re.compile(r"substack\.com|\.blog\.|blog\.|blogspot\.", re.IGNORECASE)


# -----------------------------
# FUNCTIONS
# -----------------------------

def norm_theme(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    s = s.replace("\u2014", "-").replace("\u2013", "-")
    s = s.replace("\u2018", "'").replace("\u2019", "'")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    return s.lower()


def norm_key(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = s.strip().lower()
    s = s.replace("\u2014", " ").replace("\u2013", " ").replace("-", " ")
    s = s.replace("&", " and ")
    s = re.sub(r"[,\.\u00A0]", " ", s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def add_themes(df: pd.DataFrame) -> pd.DataFrame:
    """Standardise raw theme column into new_theme."""
    # Drop unsubscribe rows — match any variant (email address changes over time)
    mask_unsub = df["theme"].astype(str).str.lower().str.contains("unsubscribe", na=False)
    dropped = int(mask_unsub.sum())
    df = df[~mask_unsub].copy()
    print(f"  Dropped {dropped} unsubscribe row(s)")

    lookup = {norm_theme(raw): new for new, raw in THEME_PAIRS}
    theme_norm = df["theme"].map(norm_theme)
    df["new_theme"] = theme_norm.map(lookup)

    # Keyword overrides
    kw_four_nations = theme_norm.str.contains(r"\b(4|four) nations\b", regex=True, na=False)
    df.loc[kw_four_nations, "new_theme"] = "four_nations"

    # Thematic roundup — split by subtheme
    sub_norm = df["subtheme"].map(norm_key)
    kw_thematic = theme_norm.str.contains(r"thematic\s+round", regex=True, na=False)
    df.loc[kw_thematic & sub_norm.str.contains("digital", na=False), "new_theme"] = "edtech"
    df.loc[kw_thematic & sub_norm.str.contains("teacher", na=False), "new_theme"] = "teacher_rrd"
    df.loc[kw_thematic & df["new_theme"].isna(), "new_theme"] = "update_from_programme"

    df.loc[sub_norm.eq("teacher recruitment retention and development"), "new_theme"] = "teacher_rrd"
    df.loc[sub_norm.eq("digital"), "new_theme"] = "edtech"

    # Fill remaining unmapped
    df["new_theme"] = df["new_theme"].fillna(df["theme"])

    unmapped = df[~df["new_theme"].isin([
        "update_from_programme", "update_from_pi", "what_matters_ed",
        "teacher_rrd", "edtech", "four_nations",
        "policy_practice_research", "political_environment_key_organisations",
    ])]["new_theme"].value_counts()
    if not unmapped.empty:
        print(f"  Warning: {unmapped.sum()} rows have unmapped themes")

    return df


def add_domain_and_org(df: pd.DataFrame) -> pd.DataFrame:
    """Extract domain from link, map to organisation and category."""
    df["domain"] = df["link"].apply(
        lambda x: urlparse(str(x)).netloc if pd.notna(x) else None
    )
    df["organisation"] = df["domain"].map(DOMAIN_TO_ORG)
    mapped = df["organisation"].map(ORG_TO_CATEGORY)
    df[["org_broad_category", "org_category"]] = mapped.apply(pd.Series)

    unmapped = df[df["organisation"].isna()]["domain"].value_counts()
    print(f"  Unmapped domains: {unmapped.sum()} rows")
    return df


def classify_item_type(row) -> str:
    """
    Classify each item as one of:
      video, tweet, linkedin_post, academic_article, government_document,
      report, news_article, blog_post, social_media_post, article
    Uses domain-level overrides first, then org category rules, then URL patterns.
    """
    domain = str(row.get("domain", "") or "")
    link   = str(row.get("link", "") or "")

    # 1. Hard domain overrides
    if domain in DOMAIN_ITEM_TYPE_OVERRIDES:
        return DOMAIN_ITEM_TYPE_OVERRIDES[domain]

    # 2. Blog URL patterns
    if BLOG_PATTERNS.search(link):
        return "blog_post"

    # 3. Category-based lookup
    broad = row.get("org_broad_category")
    cat   = row.get("org_category")
    if pd.notna(broad) and pd.notna(cat):
        item_type = CATEGORY_TO_ITEM_TYPE.get((broad, cat))
        if item_type:
            return item_type

    # 4. Fallback
    return "article"


def add_text_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add length columns and combined text field."""
    df["title_length"]       = df["title"].str.len()
    df["description_length"] = df["description"].str.len()
    df["text"] = df["title"].fillna("") + " " + df["description"].fillna("")
    df["text_length_words"]  = df["text"].str.split().str.len()
    return df


# -----------------------------
# MAIN
# -----------------------------

def main():
    print("Loading cleaned data...")
    df = pd.read_csv(INPUT_CSV)
    print(f"  Loaded {len(df)} rows")

    print("\nStandardising themes...")
    df = add_themes(df)

    print("\nExtracting domains and mapping organisations...")
    df = add_domain_and_org(df)

    print("\nClassifying item types...")
    df["item_type"] = df.apply(classify_item_type, axis=1)
    print(df["item_type"].value_counts().to_string())

    print("\nAdding text features...")
    df = add_text_features(df)

    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSaved {len(df)} rows to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
