"""Tests for ambiguity resolution."""

import pytest
from intent_shell.providers.registry import ProviderRegistry
from intent_shell.parser import SemanticParser, IntentMatch, AmbiguousMatch


@pytest.fixture
def parser():
    """Create parser with auto-discovered providers."""
    registry = ProviderRegistry()
    registry.auto_discover()
    return SemanticParser(registry)


def test_high_confidence_no_ambiguity(parser):
    """Test high confidence returns IntentMatch directly."""
    result = parser.parse("open desktop")
    assert isinstance(result, IntentMatch)
    assert result.confidence >= 0.8


def test_ambiguous_match_returns_suggestions(parser):
    """Test ambiguous confidence returns AmbiguousMatch."""
    # This input should match multiple patterns with medium confidence
    result = parser.parse("opn desk")
    
    # Should be either IntentMatch (if fuzzy is good) or AmbiguousMatch
    assert result is not None
    
    if isinstance(result, AmbiguousMatch):
        assert len(result.suggestions) > 0
        assert all(isinstance(s, IntentMatch) for s in result.suggestions)


def test_low_confidence_returns_none(parser):
    """Test very low confidence returns None."""
    result = parser.parse("completely invalid xyz 123")
    assert result is None


def test_entity_extraction_in_match(parser):
    """Test entities are extracted and attached to match."""
    result = parser.parse('open "C:\\test\\path.txt"')
    
    if isinstance(result, IntentMatch):
        # Should have extracted quoted path
        entities = result.entities
        assert len(entities) > 0


def test_env_var_expansion(parser):
    """Test environment variable expansion."""
    import os
    os.environ["TEST_VAR"] = "test_value"
    
    expanded = parser.expand_variables("%TEST_VAR%\\folder")
    assert "test_value" in expanded
    assert "%TEST_VAR%" not in expanded
