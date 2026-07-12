"""Tests for the pipeline health check's blank-detection — the guard behind the
2026-07-11 NULL-topics incident. The key regression risk is that `topic_tags`
(an array column) must be treated as blank when NULL *or* empty []."""

from src.monitoring.pipeline_health import _is_blank


def test_none_and_empty_string_are_blank():
    assert _is_blank(None) is True
    assert _is_blank("") is True
    assert _is_blank("   ") is True


def test_placeholder_marker_strings_are_blank():
    for v in ("nan", "NaN", "none", "None", "nat", "NAT"):
        assert _is_blank(v) is True, v


def test_empty_collection_is_blank_but_populated_is_not():
    # topic_tags is an array column: NULL and [] both mean "no tags".
    assert _is_blank([]) is True
    assert _is_blank(()) is True
    assert _is_blank(["schools", "policy"]) is False
    assert _is_blank(["one-tag"]) is False


def test_real_values_are_not_blank():
    assert _is_blank("A genuine summary sentence.") is False
    # The accepted body-less placeholder is NOT blank (it means "we tried").
    assert _is_blank("Summary unavailable") is False
