"""Provider registry and base classes for IntelliShell."""

from intellishell.providers.base import BaseProvider, ProviderCapability
from intellishell.providers.registry import ProviderRegistry

__all__ = ["BaseProvider", "ProviderCapability", "ProviderRegistry"]
