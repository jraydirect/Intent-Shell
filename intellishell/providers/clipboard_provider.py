"""Clipboard provider for clipboard history management."""

from typing import Optional, Dict, Any
from intellishell.providers.base import (
    BaseProvider,
    IntentTrigger,
    ExecutionResult,
    ProviderCapability
)
from intellishell.utils.clipboard import ClipboardHistory, copy_to_clipboard
from intellishell.utils.display import format_message
import logging

logger = logging.getLogger(__name__)


class ClipboardProvider(BaseProvider):
    """Provider for clipboard history management."""
    
    def __init__(self, clipboard_history: Optional[ClipboardHistory] = None):
        """
        Initialize clipboard provider.
        
        Args:
            clipboard_history: ClipboardHistory instance (creates new if None)
        """
        super().__init__()
        self.clipboard_history = clipboard_history or ClipboardHistory(auto_monitor=True)
    
    @property
    def name(self) -> str:
        return "clipboard"
    
    @property
    def description(self) -> str:
        return "Clipboard history management and search"
    
    def _initialize_triggers(self) -> None:
        """Initialize clipboard-related triggers."""
        self.capabilities = [
            ProviderCapability.READ_ONLY,
            ProviderCapability.ASYNC,
        ]
        
        self.triggers = [
            IntentTrigger(
                pattern="clipboard history",
                intent_name="show_clipboard_history",
                weight=1.0,
                aliases=[
                    "show clipboard history",
                    "clipboard list",
                    "list clipboard",
                    "show clipboard",
                    "clipboard show",
                    "my clipboard history",
                    "recent clipboard",
                    "clipboard items",
                    "show my clipboard",
                    "most recent clipboard"
                ]
            ),
            IntentTrigger(
                pattern="clipboard search",
                intent_name="search_clipboard",
                weight=1.0,
                aliases=[
                    "search clipboard",
                    "find in clipboard",
                    "clipboard find"
                ]
            ),
            IntentTrigger(
                pattern="clipboard restore",
                intent_name="restore_clipboard",
                weight=1.0,
                aliases=[
                    "restore clipboard",
                    "clipboard get",
                    "get clipboard"
                ]
            ),
            IntentTrigger(
                pattern="clipboard clear",
                intent_name="clear_clipboard_history",
                weight=1.0,
                aliases=[
                    "clear clipboard history",
                    "clipboard clear history",
                    "delete clipboard history"
                ]
            ),
            IntentTrigger(
                pattern="clipboard stats",
                intent_name="clipboard_stats",
                weight=1.0,
                aliases=[
                    "clipboard statistics",
                    "clipboard info"
                ]
            ),
            IntentTrigger(
                pattern="clipboard start monitoring",
                intent_name="start_clipboard_monitoring",
                weight=1.0,
                aliases=[
                    "start clipboard monitoring",
                    "clipboard monitor start",
                    "enable clipboard monitoring"
                ]
            ),
            IntentTrigger(
                pattern="clipboard stop monitoring",
                intent_name="stop_clipboard_monitoring",
                weight=1.0,
                aliases=[
                    "stop clipboard monitoring",
                    "clipboard monitor stop",
                    "disable clipboard monitoring"
                ]
            ),
        ]
    
    async def execute(
        self,
        intent_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """Execute clipboard intent."""
        context = context or {}
        
        try:
            if intent_name == "show_clipboard_history":
                return await self._show_history(context)
            elif intent_name == "search_clipboard":
                return await self._search_clipboard(context)
            elif intent_name == "restore_clipboard":
                return await self._restore_clipboard(context)
            elif intent_name == "clear_clipboard_history":
                return await self._clear_history(context)
            elif intent_name == "clipboard_stats":
                return await self._show_stats(context)
            elif intent_name == "start_clipboard_monitoring":
                return await self._start_monitoring(context)
            elif intent_name == "stop_clipboard_monitoring":
                return await self._stop_monitoring(context)
            else:
                return ExecutionResult(
                    success=False,
                    message=f"Unknown clipboard intent: {intent_name}"
                )
        except Exception as e:
            logger.exception(f"Clipboard provider error: {e}")
            return ExecutionResult(
                success=False,
                message=f"Clipboard operation failed: {e}"
            )
    
    async def _show_history(self, context: Dict[str, Any]) -> ExecutionResult:
        """Show clipboard history."""
        # Extract limit from entities or input text
        limit = 20  # Default
        original_input = context.get("original_input", "").lower()
        
        # Check for "most recent" or similar phrases
        if "most recent" in original_input or "latest" in original_input:
            # Check if there's a number specified
            import re
            number_match = re.search(r'\b(\d+)\b', original_input)
            if number_match:
                limit = int(number_match.group(1))
            else:
                # Just "most recent" without number means show 1-3 items
                limit = 3
        
        # Also check entities for explicit numbers
        entities = context.get("entities", [])
        for entity in entities:
            if entity.type == "number":
                try:
                    limit = int(entity.value)
                except ValueError:
                    pass
        
        entries = self.clipboard_history.get_history(limit=limit)
        
        if not entries:
            return ExecutionResult(
                success=True,
                message="Clipboard history is empty.",
                data={"entries": []}
            )
        
        # Build output (use ASCII-safe characters for Windows console)
        lines = [f"\nClipboard History (showing {len(entries)} of {len(self.clipboard_history._entries)})"]
        lines.append("=" * 70)
        
        for i, entry in enumerate(entries, 1):
            # Format timestamp
            timestamp = entry.timestamp[:19].replace("T", " ")
            
            # Color code by content type
            preview = entry.preview
            if len(entry.content) > 100:
                size_kb = len(entry.content.encode('utf-8')) / 1024
                preview += f" ({size_kb:.1f}KB)"
            
            lines.append(f"{i:3d}. [{timestamp}] {preview}")
        
        lines.append("\nTip: Use 'clipboard restore N' to restore entry N to clipboard")
        lines.append("Tip: Use 'clipboard search <query>' to search history")
        
        message = "\n".join(lines)
        
        return ExecutionResult(
            success=True,
            message=message,
            data={
                "entries": [e.to_dict() for e in entries],
                "total": len(entries)
            }
        )
    
    async def _search_clipboard(self, context: Dict[str, Any]) -> ExecutionResult:
        """Search clipboard history."""
        # Extract search query from original input
        original_input = context.get("original_input", "")
        
        # Try to extract query after "search" keyword
        query = ""
        search_keywords = ["search", "find"]
        for keyword in search_keywords:
            if keyword in original_input.lower():
                parts = original_input.lower().split(keyword, 1)
                if len(parts) > 1:
                    # Remove "clipboard" and "in" words
                    query = parts[1].strip()
                    query = query.replace("clipboard", "").replace("in", "").strip()
                    break
        
        if not query:
            return ExecutionResult(
                success=False,
                message="Please provide a search query. Example: 'clipboard search password'"
            )
        
        matches = self.clipboard_history.search(query)
        
        if not matches:
            return ExecutionResult(
                success=True,
                message=f"No clipboard entries found matching '{query}'",
                data={"matches": [], "query": query}
            )
        
        # Build output (ASCII-safe for Windows console)
        lines = [f"\nClipboard Search Results for '{query}' ({len(matches)} found)"]
        lines.append("=" * 70)
        
        for i, entry in enumerate(matches[:20], 1):  # Limit to 20 results
            timestamp = entry.timestamp[:19].replace("T", " ")
            lines.append(f"{i:3d}. [{timestamp}] {entry.preview}")
        
        if len(matches) > 20:
            lines.append(f"\n... and {len(matches) - 20} more matches")
        
        message = "\n".join(lines)
        
        return ExecutionResult(
            success=True,
            message=message,
            data={
                "matches": [e.to_dict() for e in matches[:20]],
                "total": len(matches),
                "query": query
            }
        )
    
    async def _restore_clipboard(self, context: Dict[str, Any]) -> ExecutionResult:
        """Restore clipboard entry."""
        # Extract index from entities
        index = None
        entities = context.get("entities", [])
        for entity in entities:
            if entity.type == "number":
                try:
                    index = int(entity.value)
                    break
                except ValueError:
                    pass
        
        if index is None:
            return ExecutionResult(
                success=False,
                message="Please specify an entry number. Example: 'clipboard restore 5'"
            )
        
        entry = self.clipboard_history.get_entry(index)
        if not entry:
            total = len(self.clipboard_history._entries)
            return ExecutionResult(
                success=False,
                message=f"Invalid entry number: {index}. Valid range: 1-{total}"
            )
        
        # Restore to clipboard
        if self.clipboard_history.restore_entry(index):
            success_msg = format_message(
                f"Restored entry {index} to clipboard: {entry.preview}",
                success=True
            )
            return ExecutionResult(
                success=True,
                message=success_msg,
                data={"entry": entry.to_dict(), "index": index}
            )
        else:
            return ExecutionResult(
                success=False,
                message="Failed to restore clipboard entry"
            )
    
    async def _clear_history(self, context: Dict[str, Any]) -> ExecutionResult:
        """Clear clipboard history."""
        self.clipboard_history.clear_history()
        
        success_msg = format_message("Clipboard history cleared", success=True)
        return ExecutionResult(
            success=True,
            message=success_msg
        )
    
    async def _show_stats(self, context: Dict[str, Any]) -> ExecutionResult:
        """Show clipboard statistics."""
        stats = self.clipboard_history.get_stats()
        
        lines = ["\nClipboard History Statistics"]
        lines.append("=" * 50)
        lines.append(f"Total Entries: {stats['total_entries']}")
        
        if stats['total_entries'] > 0:
            lines.append(f"Total Size: {stats['total_size_kb']:.2f} KB")
            lines.append(f"Oldest Entry: {stats['oldest_entry'][:19].replace('T', ' ')}")
            lines.append(f"Newest Entry: {stats['newest_entry'][:19].replace('T', ' ')}")
        
        monitoring_status = "Active" if stats.get('monitoring') else "Inactive"
        lines.append(f"Monitoring: {monitoring_status}")
        lines.append(f"Storage: {self.clipboard_history.storage_path}")
        
        message = "\n".join(lines)
        
        return ExecutionResult(
            success=True,
            message=message,
            data=stats
        )
    
    async def _start_monitoring(self, context: Dict[str, Any]) -> ExecutionResult:
        """Start clipboard monitoring."""
        if self.clipboard_history._monitoring:
            return ExecutionResult(
                success=True,
                message="Clipboard monitoring is already running"
            )
        
        self.clipboard_history.start_monitoring()
        
        success_msg = format_message(
            "Clipboard monitoring started (background thread active)",
            success=True
        )
        return ExecutionResult(
            success=True,
            message=success_msg
        )
    
    async def _stop_monitoring(self, context: Dict[str, Any]) -> ExecutionResult:
        """Stop clipboard monitoring."""
        if not self.clipboard_history._monitoring:
            return ExecutionResult(
                success=True,
                message="Clipboard monitoring is not running"
            )
        
        self.clipboard_history.stop_monitoring()
        
        success_msg = format_message(
            "Clipboard monitoring stopped",
            success=True
        )
        return ExecutionResult(
            success=True,
            message=success_msg
        )
