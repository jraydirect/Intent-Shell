"""Rust parser backend integration for IntelliShell."""

import logging
from typing import Optional, List, Tuple, Dict, Any
from intellishell.parser import IntentMatch, AmbiguousMatch, Entity

logger = logging.getLogger(__name__)

# Try to import Rust parser core
try:
    import parser_core
    RUST_AVAILABLE = True
    logger.info("Rust parser core available")
except ImportError:
    RUST_AVAILABLE = False
    logger.debug("Rust parser core not available, using Python fallback")


class RustParserBackend:
    """Rust backend for semantic matching."""
    
    def __init__(self):
        """Initialize Rust parser backend."""
        if not RUST_AVAILABLE:
            raise ImportError("Rust parser core not available")
        
        self.matcher = parser_core.PyIntentMatcher()
        self.entity_extractor = parser_core.PyEntityExtractor()
        self._triggers_loaded = False
    
    def load_triggers(self, triggers: List[Tuple]) -> None:
        """
        Load triggers from registry.
        
        Args:
            triggers: List of (provider, trigger) tuples from registry
        """
        from intellishell.providers.base import IntentTrigger
        
        self.matcher.clear()
        
        for provider, trigger in triggers:
            if isinstance(trigger, IntentTrigger):
                # Convert Python trigger to Rust format
                self.matcher.add_trigger(
                    pattern=trigger.pattern,
                    intent_name=trigger.intent_name,
                    provider_name=provider.name,
                    weight=trigger.weight,
                    aliases=trigger.aliases,
                )
        
        self._triggers_loaded = True
        logger.debug(f"Loaded {self.matcher.len()} triggers into Rust matcher")
    
    def calculate_similarity(self, input_str: str, pattern: str) -> float:
        """
        Calculate similarity score between input and pattern.
        
        Args:
            input_str: User input
            pattern: Trigger pattern
            
        Returns:
            Similarity score (0.0-1.0)
        """
        return self.matcher.calculate(input_str, pattern)
    
    def match_intent(self, user_input: str) -> Optional[Any]:
        """
        Match user input against triggers using Rust backend.
        
        Args:
            user_input: User input to match
            
        Returns:
            Dict with match result or None
        """
        if not self._triggers_loaded:
            logger.warning("Triggers not loaded, cannot match")
            return None
        
        result = self.matcher.match_intent(user_input)
        
        return result
    
    def extract_entities(self, text: str) -> List[Entity]:
        """
        Extract entities from text using Rust backend.
        
        Args:
            text: Input text
            
        Returns:
            List of Entity objects
        """
        entities_dict = self.entity_extractor.extract(text)
        
        # Convert Rust entities to Python Entity objects
        entities = []
        for e_dict in entities_dict:
            entity = Entity(
                type=e_dict["type"],
                value=e_dict["value"],
                original=e_dict["original"],
                start=e_dict["start"],
                end=e_dict["end"],
            )
            entities.append(entity)
        
        return entities


def convert_rust_match_to_python(rust_result: Dict[str, Any], user_input: str) -> Optional[Any]:
    """
    Convert Rust match result to Python IntentMatch or AmbiguousMatch.
    
    Args:
        rust_result: Dict from Rust matcher
        user_input: Original user input
        
    Returns:
        IntentMatch, AmbiguousMatch, or None
    """
    result_type = rust_result.get("type")
    
    if result_type == "match":
        # Convert to IntentMatch
        match_data = rust_result
        entities = []
        if "entities" in match_data:
            # Convert entities if present
            for e_dict in match_data["entities"]:
                entity = Entity(
                    type=e_dict["type"],
                    value=e_dict["value"],
                    original=e_dict["original"],
                    start=e_dict["start"],
                    end=e_dict["end"],
                )
                entities.append(entity)
        
        return IntentMatch(
            intent_name=match_data["intent_name"],
            provider_name=match_data["provider_name"],
            confidence=match_data["confidence"],
            trigger_pattern=match_data["trigger_pattern"],
            original_input=match_data.get("original_input", user_input),
            entities=entities,
            source=match_data.get("source", "rule_based"),
        )
    
    elif result_type == "ambiguous":
        # Convert to AmbiguousMatch
        suggestions = []
        for sug_dict in rust_result.get("suggestions", []):
            suggestion = IntentMatch(
                intent_name=sug_dict["intent_name"],
                provider_name=sug_dict["provider_name"],
                confidence=sug_dict["confidence"],
                trigger_pattern=sug_dict["trigger_pattern"],
                original_input=user_input,
                entities=[],
                source="rule_based",
            )
            suggestions.append(suggestion)
        
        return AmbiguousMatch(
            original_input=rust_result.get("original_input", user_input),
            suggestions=suggestions,
        )
    
    elif result_type == "none":
        return None
    
    return None
