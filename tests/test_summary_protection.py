"""Tests for the summary-overwrite guard (supabase_client.protect_existing_summaries).

Regression: during a provider outage, a re-scrape of a recent URL yields the
'Summary unavailable' placeholder, which must NOT overwrite a real summary already
in the DB. A genuinely body-less new article should still receive the placeholder."""

from src.scraping.supabase_client import (
    PLACEHOLDER_SUMMARY,
    _is_real_summary,
    protect_existing_summaries,
)


def test_is_real_summary_truth_table():
    assert _is_real_summary("A real summary.") is True
    assert _is_real_summary(None) is False
    assert _is_real_summary("") is False
    assert _is_real_summary("nan") is False
    assert _is_real_summary(PLACEHOLDER_SUMMARY) is False


def test_placeholder_does_not_overwrite_existing_real_summary():
    records = [{"url": "a", "summary": PLACEHOLDER_SUMMARY,
                "summary_generated_at": "t", "title": "keep me"}]
    n = protect_existing_summaries(records, {"a": "A good existing summary."})
    assert n == 1
    # summary fields stripped so the upsert leaves the DB value intact...
    assert "summary" not in records[0]
    assert "summary_generated_at" not in records[0]
    # ...but other fields are untouched.
    assert records[0]["title"] == "keep me"


def test_placeholder_written_when_no_real_summary_exists():
    records = [{"url": "b", "summary": PLACEHOLDER_SUMMARY}]
    n = protect_existing_summaries(records, {"b": None})
    assert n == 0
    assert records[0]["summary"] == PLACEHOLDER_SUMMARY


def test_placeholder_over_existing_placeholder_is_allowed():
    records = [{"url": "c", "summary": PLACEHOLDER_SUMMARY}]
    n = protect_existing_summaries(records, {"c": PLACEHOLDER_SUMMARY})
    assert n == 0
    assert records[0]["summary"] == PLACEHOLDER_SUMMARY


def test_real_new_summary_always_writes_through():
    records = [{"url": "d", "summary": "Fresh good summary"}]
    n = protect_existing_summaries(records, {"d": "old summary"})
    assert n == 0
    assert records[0]["summary"] == "Fresh good summary"


def test_junk_db_value_treated_as_blank_so_placeholder_allowed():
    records = [{"url": "e", "summary": PLACEHOLDER_SUMMARY}]
    n = protect_existing_summaries(records, {"e": "nan"})
    assert n == 0
