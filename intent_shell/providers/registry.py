"""Provider registry for dynamic provider discovery."""

from typing import Dict, List, Optional, Type
from intent_shell.providers.base import BaseProvider, IntentTrigger
import logging

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """
    Central registry for provider auto-discovery and management.
    
    Implements the Registry pattern for dynamic provider loading.
    """
    
    def __init__(self):
        self._providers: Dict[str, BaseProvider] = {}
        self._trigger_index: Dict[str, tuple] = {}
    
    def register(self, provider: BaseProvider) -> None:
        """
        Register a provider and index its triggers.
        
        Args:
            provider: Provider instance to register
        """
        provider_name = provider.name
        
        if provider_name in self._providers:
            logger.warning(f"Provider {provider_name} already registered, overwriting")
        
        self._providers[provider_name] = provider
        
        # Index all triggers
        for trigger in provider.get_triggers():
            self._trigger_index[trigger.pattern] = (provider, trigger)
            for alias in trigger.aliases:
                self._trigger_index[alias] = (provider, trigger)
        
        logger.info(f"Registered provider: {provider_name}")
    
    def get_provider(self, name: str) -> Optional[BaseProvider]:
        """Get a provider by name."""
        return self._providers.get(name)
    
    def get_all_providers(self) -> List[BaseProvider]:
        """Get all registered providers."""
        return list(self._providers.values())
    
    def get_all_triggers(self) -> List[tuple]:
        """Get all triggers with their associated providers."""
        return list(self._trigger_index.values())
    
    def find_provider_for_trigger(self, pattern: str) -> Optional[tuple]:
        """
        Find provider and trigger for a specific pattern.
        
        Returns:
            Tuple of (provider, trigger) or None
        """
        return self._trigger_index.get(pattern)
    
    def auto_discover(self, semantic_memory=None) -> None:
        """
        Auto-discover and register all available providers.
        
        Args:
            semantic_memory: Optional SemanticMemory instance for MemoryProvider
        """
        from intent_shell.providers.filesystem import FileSystemProvider
        from intent_shell.providers.system_monitor import SystemMonitorProvider
        from intent_shell.providers.app import AppProvider
        
        providers = [
            FileSystemProvider(),
            SystemMonitorProvider(),
            AppProvider(),
        ]
        
        # Conditionally import advanced providers
        try:
            from intent_shell.providers.watch_provider import WatchProvider
            providers.append(WatchProvider())
        except ImportError as e:
            logger.debug(f"WatchProvider not available: {e}")
        
        try:
            from intent_shell.providers.system_provider import SystemProvider
            providers.append(SystemProvider())
        except ImportError as e:
            logger.debug(f"SystemProvider not available: {e}")
        
        try:
            from intent_shell.providers.doctor_provider import DoctorProvider
            providers.append(DoctorProvider())
        except ImportError as e:
            logger.debug(f"DoctorProvider not available: {e}")
        
        # Memory provider (requires semantic_memory)
        if semantic_memory:
            try:
                from intent_shell.providers.memory_provider import MemoryProvider
                providers.append(MemoryProvider(semantic_memory=semantic_memory))
                logger.info("MemoryProvider registered with semantic memory")
            except ImportError as e:
                logger.debug(f"MemoryProvider not available: {e}")
        
        for provider in providers:
            self.register(provider)
        
        logger.info(f"Auto-discovered {len(providers)} providers")
    
    def generate_manifest(self) -> Dict:
        """
        Generate a manifest of all registered commands.
        
        Returns:
            Dictionary containing provider and command information
        """
        manifest = {
            "version": "0.1.0",
            "providers": [],
            "total_commands": 0
        }
        
        for provider in self.get_all_providers():
            provider_info = {
                "name": provider.name,
                "description": provider.description,
                "capabilities": [cap.name for cap in provider.capabilities],
                "commands": []
            }
            
            for trigger in provider.get_triggers():
                # Determine safety level
                safety_level = "READ_ONLY"
                if hasattr(provider.capabilities, '__iter__'):
                    from intent_shell.providers.base import ProviderCapability
                    if ProviderCapability.WRITE in provider.capabilities:
                        safety_level = "WRITE"
                
                command_info = {
                    "intent": trigger.intent_name,
                    "pattern": trigger.pattern,
                    "aliases": trigger.aliases,
                    "weight": trigger.weight,
                    "safety_level": safety_level
                }
                provider_info["commands"].append(command_info)
                manifest["total_commands"] += 1
            
            manifest["providers"].append(provider_info)
        
        return manifest
