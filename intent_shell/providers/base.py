"""Base provider protocol and abstract classes."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Any, Dict
from enum import Enum, auto


class ProviderCapability(Enum):
    """Provider capability flags."""
    READ_ONLY = auto()
    WRITE = auto()
    ASYNC = auto()
    STATEFUL = auto()


@dataclass
class IntentTrigger:
    """Represents a trigger pattern for intent matching."""
    pattern: str
    intent_name: str
    weight: float = 1.0
    aliases: List[str] = None
    
    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []


@dataclass
class ExecutionResult:
    """Result of a provider execution."""
    success: bool
    message: str
    data: Optional[Any] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseProvider(ABC):
    """
    Abstract base class for all Intent Shell providers.
    
    Providers are modular components that handle specific domains
    of system interaction (filesystem, apps, monitoring, etc.).
    """
    
    def __init__(self):
        self.capabilities: List[ProviderCapability] = []
        self.triggers: List[IntentTrigger] = []
        self._initialize_triggers()
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider name."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable provider description."""
        pass
    
    @abstractmethod
    def _initialize_triggers(self) -> None:
        """Initialize intent triggers for this provider."""
        pass
    
    @abstractmethod
    async def execute(
        self,
        intent_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """
        Execute an intent action.
        
        Args:
            intent_name: The intent to execute
            context: Optional execution context
            
        Returns:
            ExecutionResult with status and data
        """
        pass
    
    def get_triggers(self) -> List[IntentTrigger]:
        """Get all registered triggers for this provider."""
        return self.triggers
    
    def supports_capability(self, capability: ProviderCapability) -> bool:
        """Check if provider supports a specific capability."""
        return capability in self.capabilities
