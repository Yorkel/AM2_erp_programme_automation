"""Tests for source -> UK nation mapping. Regression: Welsh/Scottish articles from
Google Alerts (source rewritten to the publisher domain) were defaulting to 'uk',
undercutting the Four Nations breakdown."""

from src.scraping.nations import nation_for_source


def test_welsh_domains_and_slugs_map_to_wales():
    for s in ("gov.wales", "senedd.wales", "wlga.wales", "hwb.gov.wales",
              "welsh_government", "wales_education"):
        assert nation_for_source(s) == "wal", s


def test_scottish_domains_and_slugs_map_to_scotland():
    for s in ("parliament.scot", "education.gov.scot", "cosla.gov.uk",
              "gov.scot", "scotland_news", "education_scotland_alert"):
        assert nation_for_source(s) == "sco", s


def test_ni_domains_map_to_northern_ireland():
    for s in ("nilga.org", "northernireland.gov.uk", "education-ni.gov.uk"):
        assert nation_for_source(s) == "nir", s


def test_uk_wide_and_england_unchanged():
    assert nation_for_source("gov.uk") == "uk"
    assert nation_for_source("bbc.co.uk") == "uk"
    assert nation_for_source("dfe") == "eng"
    assert nation_for_source("schoolsweek") == "eng"


def test_unknown_and_empty_default_to_uk():
    assert nation_for_source("something_unmapped") == "uk"
    assert nation_for_source(None) == "uk"
    assert nation_for_source("") == "uk"
