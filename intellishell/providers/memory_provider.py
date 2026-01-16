"""Memory provider for semantic search over command history."""

from typing import Optional, Dict, Any
from intellishell.providers.base import (
    BaseProvider,
    IntentTrigger,
    ExecutionResult,
    ProviderCapability
)
import logging

logger = logging.getLogger(__name__)


class MemoryProvider(BaseProvider):
    """Provider for semantic memory search and recall."""
    
    def __init__(self, semantic_memory=None):
        """
        Initialize memory provider.
        
        Args:
            semantic_memory: SemanticMemory instance
        """
        self.semantic_memory = semantic_memory
        super().__init__()
    
    @property
    def name(self) -> str:
        return "memory"
    
    @property
    def description(self) -> str:
        return "Semantic search over command history"
    
    def _initialize_triggers(self) -> None:
        """Initialize memory-related triggers."""
        self.capabilities = [
            ProviderCapability.READ_ONLY,
            ProviderCapability.ASYNC,
        ]
        
        self.triggers = [
            IntentTrigger(
                pattern="what did i",
                intent_name="recall_command",
                weight=0.9,
                aliases=[
                    "what was that",
                    "find command",
                    "search history",
                    "remember when"
                ]
            ),
            IntentTrigger(
                pattern="what folder",
                intent_name="recall_folder",
                weight=0.9,
                aliases=[
                    "which folder",
                    "what directory",
                    "find folder"
                ]
            ),
            IntentTrigger(
                pattern="recent memories",
                intent_name="show_recent",
                weight=1.0,
                aliases=[
                    "recent commands",
                    "show memories",
                    "memory list"
                ]
            ),
        ]
    
    async def execute(
        self,
        intent_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """Execute memory operation."""
        if self.semantic_memory is None or not self.semantic_memory.is_available():
            return ExecutionResult(
                success=False,
                message="Semantic memory not available. Install chromadb: pip install chromadb"
            )
        
        try:
            if intent_name == "recall_command":
                return await self._recall_command(context)
            elif intent_name == "recall_folder":
                return await self._recall_folder(context)
            elif intent_name == "show_recent":
                return await self._show_recent()
            else:
                return ExecutionResult(
                    success=False,
                    message=f"Unknown intent: {intent_name}"
                )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Memory error: {e}"
            )
    
    async def _recall_command(
        self,
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """Recall commands based on semantic search."""
        if not context or "original_input" not in context:
            return ExecutionResult(
                success=False,
                message="No query provided for memory search"
            )
        
        query = context["original_input"]
        
        # Perform semantic search
        results = self.semantic_memory.recall(query, n_results=5)
        
        if not results:
            return ExecutionResult(
                success=False,
                message=f"No matching memories found for: {query}"
            )
        
        # Format results
        message_lines = [f"Found {len(results)} similar commands:\n"]
        
        for i, result in enumerate(results, 1):
            metadata = result.get("metadata", {})
            timestamp = metadata.get("timestamp", "")[:19]
            intent = metadata.get("intent_name", "unknown")
            document = result.get("document", "")[:100]
            
            message_lines.append(f"{i}. [{timestamp}] {intent}")
            message_lines.append(f"   {document}")
            
            # Show distance/similarity if available
            if result.get("distance") is not None:
                similarity = 1.0 - result["distance"]
                message_lines.append(f"   Similarity: {similarity:.2f}")
            
            message_lines.append("")
        
        return ExecutionResult(
            success=True,
            message="\n".join(message_lines),
            data={"results": results}
        )
    
    async def _recall_folder(
        self,
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """Recall folder operations specifically."""
        if not context or "original_input" not in context:
            return ExecutionResult(
                success=False,
                message="No query provided"
            )
        
        # Search for filesystem-related operations
        query = context["original_input"] + " folder directory path"
        results = self.semantic_memory.recall(query, n_results=5)
        
        # Filter for filesystem operations
        filesystem_results = [
            r for r in results
            if r.get("metadata", {}).get("provider_name") == "filesystem"
        ]
        
        if not filesystem_results:
            return ExecutionResult(
                success=False,
                message="No folder operations found in memory"
            )
        
        # Format results
        message_lines = ["Found folder operations:\n"]
        
        for i, result in enumerate(filesystem_results, 1):
            metadata = result.get("metadata", {})
            timestamp = metadata.get("timestamp", "")[:19]
            document = result.get("document", "")
            
            message_lines.append(f"{i}. [{timestamp}] {document}")
        
        return ExecutionResult(
            success=True,
            message="\n".join(message_lines),
            data={"results": filesystem_results}
        )
    
    async def _show_recent(self) -> ExecutionResult:
        """Show recent memories."""
        memories = self.semantic_memory.get_recent_memories(limit=10)
        
        if not memories:
            return ExecutionResult(
                success=True,
                message="No memories available yet"
            )
        
        message_lines = ["Recent Memories:\n"]
        
        for i, memory in enumerate(memories, 1):
            metadata = memory.get("metadata", {})
            timestamp = metadata.get("timestamp", "")[:19]
            intent = metadata.get("intent_name", "unknown")
            document = memory.get("document", "")[:80]
            
            message_lines.append(f"{i}. [{timestamp}] {intent}")
            message_lines.append(f"   {document}")
        
        return ExecutionResult(
            success=True,
            message="\n".join(message_lines),
            data={"memories": memories}
        )
