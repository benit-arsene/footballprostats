"""Focused tests for refresh_current normalization."""

from ingestion.refresh_current import _normalize_name


def test_normalize_name_basic():
    assert _normalize_name("Erling Haaland") == "erlinghaaland"
    assert _normalize_name("  E. Haaland ") == "ehaaland"
    assert _normalize_name("") == ""
    assert _normalize_name(None) == ""


def test_normalize_name_punctuation():
    assert _normalize_name("Ollie Watkins") == "olliewatkins"
    assert _normalize_name("K. Palmer") == "kpalmer"


def test_normalize_name_unicode_and_accents():
    assert _normalize_name("José Mourinho") == "josmourinho"
    assert _normalize_name("Müller") == "mller"


def test_normalize_name_empty_and_none():
    assert _normalize_name("") == ""
    assert _normalize_name(None) == ""
