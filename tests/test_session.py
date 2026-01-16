"""Tests for session state management."""

import pytest
from intent_shell.session import SessionState, CommandEntry
from datetime import datetime


def test_session_creation():
    """Test session state creation."""
    session = SessionState(session_id="test123")
    assert session.session_id == "test123"
    assert len(session.command_history) == 0


def test_add_command():
    """Test adding command to history."""
    session = SessionState(session_id="test123")
    session.add_command("open desktop", "open_desktop", True, 0.95)
    
    assert len(session.command_history) == 1
    assert session.command_history[0].command == "open desktop"
    assert session.command_history[0].success is True


def test_get_recent_commands():
    """Test getting recent commands."""
    session = SessionState(session_id="test123")
    
    for i in range(15):
        session.add_command(f"command {i}", f"intent_{i}", True, 0.9)
    
    recent = session.get_recent_commands(5)
    assert len(recent) == 5
    assert recent[-1].command == "command 14"


def test_context_management():
    """Test context data management."""
    session = SessionState(session_id="test123")
    
    session.update_context("last_path", "/home/user")
    assert session.get_context("last_path") == "/home/user"
    assert session.get_context("nonexistent", "default") == "default"


def test_session_stats():
    """Test session statistics."""
    session = SessionState(session_id="test123")
    
    session.add_command("cmd1", "intent1", True, 0.9)
    session.add_command("cmd2", "intent2", False, 0.8)
    session.add_command("cmd3", "intent3", True, 0.95)
    
    stats = session.get_stats()
    assert stats["total_commands"] == 3
    assert stats["successful_commands"] == 2
    assert stats["success_rate"] == pytest.approx(66.67, rel=0.1)
