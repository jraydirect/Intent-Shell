"""Provider registry and base classes for Intent Shell."""

from intent_shell.providers.base import BaseProvider, ProviderCapability
from intent_shell.providers.registry import ProviderRegistry

__all__ = ["BaseProvider", "ProviderCapability", "ProviderRegistry"]
