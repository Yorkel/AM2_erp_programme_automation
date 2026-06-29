"""Smoke tests for the pure scraping helpers in src/scraping/common.py.

These are deliberately dependency-light (no model, no network) so they run fast
in CI and guard the URL/text normalisation that de-duplication relies on.
"""
from datetime import date

from src.scraping.common import build_text_clean, normalise_url, parse_date_loose


def test_build_text_clean_joins_title_and_body_snippet():
    assert build_text_clean("Title", "one two three four five", max_words=3) == "Title one two three"


def test_build_text_clean_returns_title_when_body_empty():
    assert build_text_clean("Title", "") == "Title"


def test_build_text_clean_returns_body_when_title_empty():
    assert build_text_clean("", "body words here") == "body words here"


def test_normalise_url_lowercases_host_strips_slash_and_tracking():
    assert (
        normalise_url("https://Example.COM/News/Thing/?utm_source=x&id=1")
        == "https://example.com/News/Thing?id=1"
    )


def test_normalise_url_keeps_content_param_drops_tracking():
    assert normalise_url("https://x.com/a/?mc_cid=1&q=keep") == "https://x.com/a?q=keep"


def test_normalise_url_passthrough_for_non_url():
    assert normalise_url("not a url") == "not a url"
    assert normalise_url("") == ""


def test_parse_date_loose_parses_and_rejects():
    assert parse_date_loose("12 May 2026") == date(2026, 5, 12)
    assert parse_date_loose("") is None
    assert parse_date_loose("not a date") is None
