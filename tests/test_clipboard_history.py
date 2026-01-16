"""Tests for clipboard history functionality."""

import pytest
import tempfile
from pathlib import Path
from intellishell.utils.clipboard import ClipboardHistory, ClipboardHistoryEntry


@pytest.fixture
def temp_storage():
    """Create temporary storage for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "clipboard_test.jsonl"
        yield storage_path


@pytest.fixture
def clipboard_history(temp_storage):
    """Create clipboard history instance for testing."""
    return ClipboardHistory(
        storage_path=temp_storage,
        max_entries=10,
        auto_monitor=False
    )


def test_clipboard_history_initialization(clipboard_history):
    """Test clipboard history initialization."""
    assert clipboard_history is not None
    assert clipboard_history.max_entries == 10
    assert len(clipboard_history._entries) == 0


def test_add_entry(clipboard_history):
    """Test adding clipboard entries."""
    # Add first entry
    result = clipboard_history.add_entry("Hello World")
    assert result is True
    assert len(clipboard_history._entries) == 1
    
    # Add second entry
    result = clipboard_history.add_entry("Second entry")
    assert result is True
    assert len(clipboard_history._entries) == 2
    
    # Try to add duplicate (should be skipped)
    result = clipboard_history.add_entry("Second entry")
    assert result is False
    assert len(clipboard_history._entries) == 2


def test_get_history(clipboard_history):
    """Test retrieving clipboard history."""
    # Add some entries
    clipboard_history.add_entry("Entry 1")
    clipboard_history.add_entry("Entry 2")
    clipboard_history.add_entry("Entry 3")
    
    # Get all history (newest first)
    history = clipboard_history.get_history()
    assert len(history) == 3
    assert history[0].content == "Entry 3"
    assert history[1].content == "Entry 2"
    assert history[2].content == "Entry 1"
    
    # Get limited history
    history = clipboard_history.get_history(limit=2)
    assert len(history) == 2
    assert history[0].content == "Entry 3"


def test_search(clipboard_history):
    """Test searching clipboard history."""
    # Add entries
    clipboard_history.add_entry("Hello World")
    clipboard_history.add_entry("Python is awesome")
    clipboard_history.add_entry("Hello Python")
    clipboard_history.add_entry("Goodbye World")
    
    # Search for "Hello"
    results = clipboard_history.search("Hello")
    assert len(results) == 2
    assert all("hello" in r.content.lower() for r in results)
    
    # Search for "Python"
    results = clipboard_history.search("Python")
    assert len(results) == 2
    
    # Search for non-existent
    results = clipboard_history.search("nonexistent")
    assert len(results) == 0


def test_get_entry_by_index(clipboard_history):
    """Test getting entry by index."""
    clipboard_history.add_entry("Entry 1")
    clipboard_history.add_entry("Entry 2")
    clipboard_history.add_entry("Entry 3")
    
    # Get most recent (index 1)
    entry = clipboard_history.get_entry(1)
    assert entry is not None
    assert entry.content == "Entry 3"
    
    # Get second most recent (index 2)
    entry = clipboard_history.get_entry(2)
    assert entry is not None
    assert entry.content == "Entry 2"
    
    # Get oldest (index 3)
    entry = clipboard_history.get_entry(3)
    assert entry is not None
    assert entry.content == "Entry 1"
    
    # Invalid index
    entry = clipboard_history.get_entry(10)
    assert entry is None


def test_max_entries_limit(clipboard_history):
    """Test that max entries limit is enforced."""
    # Add more than max_entries
    for i in range(15):
        clipboard_history.add_entry(f"Entry {i}")
    
    # Should only keep last 10
    assert len(clipboard_history._entries) == 10
    
    # Oldest should be Entry 5
    oldest = clipboard_history._entries[0]
    assert "Entry 5" in oldest.content


def test_clear_history(clipboard_history):
    """Test clearing clipboard history."""
    # Add entries
    clipboard_history.add_entry("Entry 1")
    clipboard_history.add_entry("Entry 2")
    assert len(clipboard_history._entries) == 2
    
    # Clear
    clipboard_history.clear_history()
    assert len(clipboard_history._entries) == 0
    assert clipboard_history._last_content is None


def test_persistence(temp_storage):
    """Test that history persists to disk."""
    # Create first instance and add entries
    history1 = ClipboardHistory(storage_path=temp_storage, auto_monitor=False)
    history1.add_entry("Persistent Entry 1")
    history1.add_entry("Persistent Entry 2")
    
    # Create second instance (should load from disk)
    history2 = ClipboardHistory(storage_path=temp_storage, auto_monitor=False)
    assert len(history2._entries) == 2
    assert history2._entries[0].content == "Persistent Entry 1"
    assert history2._entries[1].content == "Persistent Entry 2"


def test_stats(clipboard_history):
    """Test clipboard statistics."""
    # Empty stats
    stats = clipboard_history.get_stats()
    assert stats["total_entries"] == 0
    
    # Add entries
    clipboard_history.add_entry("Entry 1")
    clipboard_history.add_entry("Entry 2")
    
    # Check stats
    stats = clipboard_history.get_stats()
    assert stats["total_entries"] == 2
    assert stats["total_size_kb"] > 0
    assert stats["oldest_entry"] is not None
    assert stats["newest_entry"] is not None


def test_clipboard_history_entry():
    """Test ClipboardHistoryEntry class."""
    entry = ClipboardHistoryEntry(
        content="Test content",
        timestamp="2026-01-16T10:00:00",
        content_type="text"
    )
    
    assert entry.content == "Test content"
    assert entry.timestamp == "2026-01-16T10:00:00"
    assert entry.content_type == "text"
    assert entry.preview == "Test content"
    
    # Test long content preview
    long_content = "A" * 100
    entry2 = ClipboardHistoryEntry(
        content=long_content,
        timestamp="2026-01-16T10:00:00"
    )
    assert len(entry2.preview) == 63  # 60 chars + "..."
    assert entry2.preview.endswith("...")


def test_clipboard_history_entry_serialization():
    """Test entry serialization/deserialization."""
    entry = ClipboardHistoryEntry(
        content="Test content",
        timestamp="2026-01-16T10:00:00",
        content_type="text"
    )
    
    # Serialize
    data = entry.to_dict()
    assert data["content"] == "Test content"
    assert data["timestamp"] == "2026-01-16T10:00:00"
    
    # Deserialize
    entry2 = ClipboardHistoryEntry.from_dict(data)
    assert entry2.content == entry.content
    assert entry2.timestamp == entry.timestamp
    assert entry2.content_type == entry.content_type


def test_empty_content_handling(clipboard_history):
    """Test that empty content is rejected."""
    result = clipboard_history.add_entry("")
    assert result is False
    
    result = clipboard_history.add_entry("   ")
    assert result is False
    
    assert len(clipboard_history._entries) == 0


@pytest.mark.asyncio
async def test_clipboard_provider_integration():
    """Test ClipboardProvider integration."""
    from intellishell.providers.clipboard_provider import ClipboardProvider
    
    # Create provider
    provider = ClipboardProvider()
    
    assert provider.name == "clipboard"
    assert len(provider.get_triggers()) > 0
    
    # Test show history (empty)
    result = await provider.execute("show_clipboard_history", {})
    assert result.success is True
    assert "empty" in result.message.lower()
    
    # Add some entries
    provider.clipboard_history.add_entry("Test 1")
    provider.clipboard_history.add_entry("Test 2")
    
    # Test show history (with entries)
    result = await provider.execute("show_clipboard_history", {})
    assert result.success is True
    assert "Test 1" in result.message or "Test 2" in result.message
    
    # Test stats
    result = await provider.execute("clipboard_stats", {})
    assert result.success is True
    assert "Statistics" in result.message


@pytest.mark.asyncio
async def test_clipboard_provider_search():
    """Test clipboard search functionality."""
    from intellishell.providers.clipboard_provider import ClipboardProvider
    
    provider = ClipboardProvider()
    
    # Add entries
    provider.clipboard_history.add_entry("Python programming")
    provider.clipboard_history.add_entry("JavaScript code")
    provider.clipboard_history.add_entry("Python tutorial")
    
    # Search
    context = {
        "original_input": "clipboard search Python",
        "entities": []
    }
    result = await provider.execute("search_clipboard", context)
    assert result.success is True
    assert "Python" in result.message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
