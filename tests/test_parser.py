"""Tests for semantic parser."""

import pytest
from intent_shell.providers.registry import ProviderRegistry
from intent_shell.parser import SemanticParser


@pytest.fixture
def parser():
    """Create parser with auto-discovered providers."""
    registry = ProviderRegistry()
    registry.auto_discover()
    return SemanticParser(registry)


def test_exact_match(parser):
    """Test exact pattern matching."""
    match = parser.parse("open desktop")
    assert match is not None
    assert match.intent_name == "open_desktop"
    assert match.confidence == 1.0


def test_fuzzy_match(parser):
    """Test fuzzy matching with typos."""
    match = parser.parse("opn desktop")
    assert match is not None
    assert match.intent_name == "open_desktop"
    assert match.confidence > 0.6


def test_alias_match(parser):
    """Test matching via alias."""
    match = parser.parse("show desktop")
    assert match is not None
    assert match.intent_name == "open_desktop"


def test_no_match(parser):
    """Test no match for invalid input."""
    match = parser.parse("completely invalid command xyz")
    assert match is None


def test_debug_scores(parser):
    """Test debug scoring."""
    scores = parser.get_debug_scores("open desktop", top_n=5)
    assert len(scores) <= 5
    assert all(len(score) == 3 for score in scores)
    assert scores[0][2] == 1.0  # Best match should be 1.0
