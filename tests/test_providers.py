"""Tests for provider architecture."""

import pytest
from intent_shell.providers.registry import ProviderRegistry
from intent_shell.providers.filesystem import FileSystemProvider
from intent_shell.providers.app import AppProvider


def test_provider_registration():
    """Test provider registration."""
    registry = ProviderRegistry()
    provider = FileSystemProvider()
    registry.register(provider)
    
    assert registry.get_provider("filesystem") is not None
    assert len(registry.get_all_providers()) == 1


def test_auto_discovery():
    """Test auto-discovery of providers."""
    registry = ProviderRegistry()
    registry.auto_discover()
    
    providers = registry.get_all_providers()
    assert len(providers) >= 3
    assert any(p.name == "filesystem" for p in providers)
    assert any(p.name == "app" for p in providers)


def test_trigger_indexing():
    """Test trigger indexing in registry."""
    registry = ProviderRegistry()
    provider = FileSystemProvider()
    registry.register(provider)
    
    triggers = registry.get_all_triggers()
    assert len(triggers) > 0


@pytest.mark.asyncio
async def test_filesystem_provider():
    """Test filesystem provider execution."""
    provider = FileSystemProvider()
    
    # Test that triggers are initialized
    assert len(provider.get_triggers()) > 0
    
    # Test intent name exists
    trigger_names = [t.intent_name for t in provider.get_triggers()]
    assert "open_desktop" in trigger_names


@pytest.mark.asyncio
async def test_app_provider():
    """Test app provider execution."""
    provider = AppProvider()
    
    # Test that triggers are initialized
    assert len(provider.get_triggers()) > 0
    
    # Test intent name exists
    trigger_names = [t.intent_name for t in provider.get_triggers()]
    assert "launch_notepad" in trigger_names
