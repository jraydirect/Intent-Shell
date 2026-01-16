"""Tests for transaction logging."""

import pytest
import tempfile
from pathlib import Path
from intent_shell.utils.transaction_log import TransactionLogger


@pytest.fixture
def temp_log():
    """Create temporary log file."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonl") as f:
        log_path = Path(f.name)
    
    yield log_path
    
    # Cleanup
    if log_path.exists():
        log_path.unlink()


def test_log_transaction(temp_log):
    """Test logging a transaction."""
    logger = TransactionLogger(temp_log)
    
    logger.log_transaction(
        user_input="open desktop",
        intent_name="open_desktop",
        provider_name="filesystem",
        confidence=0.95,
        success=True,
        result_message="Opening Desktop"
    )
    
    # Verify file was written
    assert temp_log.exists()
    
    # Read and verify
    history = logger.read_history()
    assert len(history) == 1
    assert history[0]["user_input"] == "open desktop"
    assert history[0]["confidence"] == 0.95


def test_read_history_limit(temp_log):
    """Test reading history with limit."""
    logger = TransactionLogger(temp_log)
    
    # Log multiple transactions
    for i in range(10):
        logger.log_transaction(
            user_input=f"command {i}",
            intent_name="test",
            provider_name="test",
            confidence=0.9,
            success=True
        )
    
    # Read with limit
    history = logger.read_history(limit=5)
    assert len(history) == 5
    assert history[-1]["user_input"] == "command 9"  # Last one


def test_search_history(temp_log):
    """Test searching transaction history."""
    logger = TransactionLogger(temp_log)
    
    logger.log_transaction("open desktop", "open_desktop", "filesystem", 0.9, True)
    logger.log_transaction("open downloads", "open_downloads", "filesystem", 0.9, True)
    logger.log_transaction("invalid", None, None, 0.0, False)
    
    # Search by query
    results = logger.search_history(query="open")
    assert len(results) == 2
    
    # Search by success
    results = logger.search_history(success=False)
    assert len(results) == 1
    assert results[0]["user_input"] == "invalid"


def test_get_stats(temp_log):
    """Test getting statistics."""
    logger = TransactionLogger(temp_log)
    
    logger.log_transaction("cmd1", "intent1", "provider1", 0.9, True)
    logger.log_transaction("cmd2", "intent1", "provider1", 0.9, True)
    logger.log_transaction("cmd3", "intent2", "provider2", 0.8, False)
    
    stats = logger.get_stats()
    assert stats["total"] == 3
    assert stats["successful"] == 2
    assert stats["success_rate"] == pytest.approx(66.67, rel=0.1)
    assert len(stats["top_intents"]) > 0
