"""Tab completion for IntelliShell commands."""

from typing import Optional, List, Iterable
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document


class IntelliShellCompleter(Completer):
    """Tab completion for IntelliShell commands, intents, and file paths."""
    
    def __init__(self, provider_registry=None, parser=None):
        """
        Initialize completer.
        
        Args:
            provider_registry: ProviderRegistry instance for getting available intents
            parser: SemanticParser instance for command parsing
        """
        self.provider_registry = provider_registry
        self.parser = parser
        
        # Built-in commands
        self.builtin_commands = [
            "help", "?", "manifest", "history", "hist", "stats", "session stats",
            "clear", "cls", "exit", "quit", "bye"
        ]
        
        # Special command prefixes
        self.command_prefixes = ["!", "?", "help", "open", "list", "show", "get", 
                                "check", "kill", "watch", "what", "where"]
    
    def get_completions(
        self, 
        document: Document, 
        complete_event
    ) -> Iterable[Completion]:
        """
        Get completions for current input.
        
        Args:
            document: Current document (input text)
            complete_event: Completion event
            
        Yields:
            Completion objects
        """
        text = document.text_before_cursor
        text_lower = text.lower().strip()
        
        # Collect all possible completions
        completions = set()
        
        # If empty, suggest built-in commands
        if not text or not text.strip():
            for cmd in sorted(self.builtin_commands):
                yield Completion(cmd, start_position=0)
            return
        
        # Built-in commands that match
        for cmd in self.builtin_commands:
            if cmd.lower().startswith(text_lower):
                completions.add(cmd)
        
        # Get all available intents from providers
        if self.provider_registry:
            all_intents = self._get_all_intents()
            
            # Filter intents that match current input
            for intent in all_intents:
                intent_lower = intent.lower()
                if intent_lower.startswith(text_lower):
                    completions.add(intent)
                # Also check if text is contained in intent (for partial matching)
                elif text_lower in intent_lower:
                    completions.add(intent)
        
        # Common patterns and examples
        common_patterns = [
            "open desktop", "open downloads", "open documents",
            "list downloads", "list desktop", "list files",
            "system info", "get hostname", "get username",
            "check system health", "check dependencies",
            "what did i", "what folder", "recent memories",
            "watch downloads", "watch for pdf", "stop watching",
            "list processes", "kill process"
        ]
        
        for pattern in common_patterns:
            pattern_lower = pattern.lower()
            if pattern_lower.startswith(text_lower) or text_lower in pattern_lower:
                completions.add(pattern)
        
        # Yield sorted completions
        for completion in sorted(completions):
            yield Completion(completion, start_position=0)
    
    def _get_all_intents(self) -> List[str]:
        """Get all available intents from all providers."""
        if not self.provider_registry:
            return []
        
        intents = set()
        for provider in self.provider_registry.get_all_providers():
            for trigger in provider.get_triggers():
                # Add pattern (main command)
                if trigger.pattern:
                    intents.add(trigger.pattern)
                # Add aliases
                if trigger.aliases:
                    intents.update(trigger.aliases)
        
        return sorted(list(intents))
