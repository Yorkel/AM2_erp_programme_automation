"""Tests for the relevance filter: the layer that decides what enters the newsletter.
Covers the two known leaks closed in the audit (BBC iPlayer/programme listings, and
FCDO overseas-development stories) plus the core hard-block, and confirms genuine
UK education content still passes."""

from src.scraping.relevance import (
    is_blocked_url_pattern,
    is_non_uk_content,
)


def test_iplayer_and_programme_listings_are_blocked():
    assert is_blocked_url_pattern("https://www.bbc.co.uk/iplayer/episode/x/school-swap") is True
    assert is_blocked_url_pattern("https://www.bbc.co.uk/programmes/b0abc") is True


def test_real_bbc_news_is_not_blocked_by_pattern():
    assert is_blocked_url_pattern("https://www.bbc.co.uk/news/education-12345") is False


def test_fcdo_overseas_countries_are_vetoed_as_non_uk():
    cases = [
        ("UK aid boosts education in Bangladesh", "FCDO funds schools in Dhaka."),
        ("New funding for schools in Ukraine", "Support for displaced pupils in Kyiv."),
        ("Brazil literacy programme expands", "Classrooms in Sao Paulo."),
        ("Education mission to Egypt", "British Council work in Cairo."),
    ]
    for title, body in cases:
        assert bool(is_non_uk_content(title, body)) is True, title


def test_genuine_uk_education_content_passes():
    cases = [
        ("Ofsted publishes new inspection framework", "Schools in England assessed differently."),
        ("Welsh Government funds classroom tech", "Pupils across Wales benefit."),
        ("Scottish attainment gap narrows", "Councils report progress."),
    ]
    for title, body in cases:
        assert not is_non_uk_content(title, body), title
