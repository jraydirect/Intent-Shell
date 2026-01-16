"""Intent to action mapping with safety controls."""

from typing import Optional
from intellishell.providers.registry import ProviderRegistry
from intellishell.providers.base import ExecutionResult
from intellishell.parser import IntentMatch
from intellishell.safety import SafetyController, SafetyLevel
import logging

logger = logging.getLogger(__name__)


class ExecutionPlanner:
    """
    Maps intents to executable actions with safety controls.
    
    Implements:
    - Provider dispatch via registry
    - Safety level enforcement
    - Human-in-the-loop confirmations
    """
    
    def __init__(self, registry: ProviderRegistry, safety_controller: Optional[SafetyController] = None):
        """
        Initialize planner with provider registry.
        
        Args:
            registry: ProviderRegistry instance
            safety_controller: Optional SafetyController for HITL
        """
        self.registry = registry
        self.safety_controller = safety_controller or SafetyController()
    
    async def execute_intent(
        self,
        intent_match: IntentMatch,
        context: Optional[dict] = None,
        skip_safety_check: bool = False
    ) -> ExecutionResult:
        """
        Execute a matched intent through the appropriate provider.
        
        Args:
            intent_match: Matched intent with confidence score
            context: Optional execution context
            skip_safety_check: Skip safety confirmation (use with caution)
            
        Returns:
            ExecutionResult from provider
        """
        provider = self.registry.get_provider(intent_match.provider_name)
        
        if provider is None:
            logger.error(f"Provider not found: {intent_match.provider_name}")
            result = ExecutionResult(
                success=False,
                message=f"Provider '{intent_match.provider_name}' not found"
            )
            self.safety_controller.record_action_result(False)
            return result
        
        # Safety check
        if not skip_safety_check:
            safety_level = self.safety_controller.get_safety_level(intent_match.intent_name)
            
            if self.safety_controller.requires_confirmation(intent_match.intent_name):
                confirmed = self.safety_controller.request_confirmation(
                    intent_name=intent_match.intent_name,
                    provider_name=intent_match.provider_name,
                    description=intent_match.trigger_pattern,
                    safety_level=safety_level
                )
                
                if not confirmed:
                    result = ExecutionResult(
                        success=False,
                        message="Action cancelled by user",
                        metadata={"cancelled": True, "safety_level": safety_level.name}
                    )
                    self.safety_controller.record_action_result(False)
                    return result
        
        logger.info(
            f"Executing intent '{intent_match.intent_name}' "
            f"via provider '{provider.name}' "
            f"(confidence: {intent_match.confidence:.2f})"
        )
        
        # Execute through provider
        result = await provider.execute(
            intent_name=intent_match.intent_name,
            context=context
        )
        
        # Attach metadata
        if result.metadata is None:
            result.metadata = {}
        
        result.metadata.update({
            "provider": provider.name,
            "intent": intent_match.intent_name,
            "confidence": intent_match.confidence,
            "safety_level": self.safety_controller.get_safety_level(intent_match.intent_name).name
        })
        
        # Record result for safety controller
        self.safety_controller.record_action_result(result.success)
        
        return result
    
    def get_safety_summary(self) -> dict:
        """Get safety summary including RED action log."""
        return {
            "last_action_failed": self.safety_controller.last_action_failed,
            "red_actions": len(self.safety_controller.get_red_action_log()),
            "red_action_log": self.safety_controller.get_red_action_log()
        }
