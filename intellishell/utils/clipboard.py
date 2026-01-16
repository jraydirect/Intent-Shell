"""Clipboard utilities for piping output and reading global context."""

from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
import json
import threading
import time
import logging

logger = logging.getLogger(__name__)


def copy_to_clipboard(text: str) -> bool:
    """
    Copy text to system clipboard.
    
    Args:
        text: Text to copy
        
    Returns:
        True if successful, False otherwise
    """
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except ImportError:
        logger.warning("pyperclip not installed. Install with: pip install pyperclip")
        return False
    except Exception as e:
        logger.error(f"Failed to copy to clipboard: {e}")
        return False


def get_clipboard_content() -> Optional[str]:
    """
    Read content from system clipboard.
    
    Returns:
        Clipboard content or None if unavailable
    """
    try:
        import pyperclip
        content = pyperclip.paste()
        return content if content else None
    except ImportError:
        logger.debug("pyperclip not installed for clipboard reading")
        return None
    except Exception as e:
        logger.debug(f"Failed to read clipboard: {e}")
        return None


def should_pipe_to_clipboard(user_input: str) -> tuple[bool, str]:
    """
    Check if command should pipe output to clipboard.
    
    Args:
        user_input: Raw user input
        
    Returns:
        Tuple of (should_pipe, cleaned_input)
    """
    normalized = user_input.lower().strip()
    
    clipboard_triggers = [
        "to clipboard",
        "copy to clipboard",
        "| clipboard",
        "pipe to clipboard",
        "> clipboard",
    ]
    
    for trigger in clipboard_triggers:
        if normalized.endswith(trigger):
            # Remove the trigger from input
            cleaned = user_input[:-(len(trigger))].strip()
            return True, cleaned
    
    return False, user_input


class ClipboardHistoryEntry:
    """Represents a single clipboard history entry."""
    
    def __init__(self, content: str, timestamp: str, content_type: str = "text"):
        self.content = content
        self.timestamp = timestamp
        self.content_type = content_type
        self.preview = self._generate_preview()
    
    def _generate_preview(self) -> str:
        """Generate a preview of the content."""
        if len(self.content) <= 60:
            return self.content
        return self.content[:60] + "..."
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "content": self.content,
            "timestamp": self.timestamp,
            "content_type": self.content_type,
            "preview": self.preview
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ClipboardHistoryEntry':
        """Create from dictionary."""
        return ClipboardHistoryEntry(
            content=data["content"],
            timestamp=data["timestamp"],
            content_type=data.get("content_type", "text")
        )


class ClipboardHistory:
    """
    Persistent clipboard history manager.
    
    Features:
    - Stores clipboard history to disk
    - Background monitoring thread
    - Search and filtering
    - Deduplication
    - Size limits
    """
    
    DEFAULT_MAX_ENTRIES = 100
    DEFAULT_MAX_SIZE_MB = 10
    MONITOR_INTERVAL = 1.0  # seconds
    
    def __init__(
        self,
        storage_path: Optional[Path] = None,
        max_entries: int = DEFAULT_MAX_ENTRIES,
        max_size_mb: int = DEFAULT_MAX_SIZE_MB,
        auto_monitor: bool = False
    ):
        """
        Initialize clipboard history manager.
        
        Args:
            storage_path: Path to store history (default: ~/.intellishell/clipboard_history.jsonl)
            max_entries: Maximum number of entries to keep
            max_size_mb: Maximum size of history file in MB
            auto_monitor: Start background monitoring automatically
        """
        if storage_path is None:
            storage_dir = Path.home() / ".intellishell"
            storage_dir.mkdir(parents=True, exist_ok=True)
            storage_path = storage_dir / "clipboard_history.jsonl"
        
        self.storage_path = storage_path
        self.max_entries = max_entries
        self.max_size_mb = max_size_mb
        self._entries: List[ClipboardHistoryEntry] = []
        self._last_content: Optional[str] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitoring = False
        self._lock = threading.Lock()
        
        # Load existing history
        self._load_history()
        
        if auto_monitor:
            self.start_monitoring()
        
        logger.info(f"Clipboard history initialized: {self.storage_path}")
    
    def _load_history(self) -> None:
        """Load history from disk."""
        if not self.storage_path.exists():
            return
        
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        entry = ClipboardHistoryEntry.from_dict(data)
                        self._entries.append(entry)
            
            # Keep only max_entries
            if len(self._entries) > self.max_entries:
                self._entries = self._entries[-self.max_entries:]
            
            logger.info(f"Loaded {len(self._entries)} clipboard history entries")
        except Exception as e:
            logger.error(f"Failed to load clipboard history: {e}")
    
    def _save_history(self) -> None:
        """Save history to disk."""
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                for entry in self._entries:
                    f.write(json.dumps(entry.to_dict()) + "\n")
        except Exception as e:
            logger.error(f"Failed to save clipboard history: {e}")
    
    def add_entry(self, content: str, content_type: str = "text") -> bool:
        """
        Add a new clipboard entry.
        
        Args:
            content: Clipboard content
            content_type: Type of content (text, path, url, etc.)
            
        Returns:
            True if added, False if duplicate or error
        """
        if not content or not content.strip():
            return False
        
        # Skip if same as last entry (deduplication)
        if self._last_content == content:
            return False
        
        with self._lock:
            # Check size limit (approximate)
            content_size_mb = len(content.encode('utf-8')) / (1024 * 1024)
            if content_size_mb > self.max_size_mb:
                logger.warning(f"Clipboard content too large: {content_size_mb:.2f}MB")
                return False
            
            # Create entry
            entry = ClipboardHistoryEntry(
                content=content,
                timestamp=datetime.now().isoformat(),
                content_type=content_type
            )
            
            self._entries.append(entry)
            self._last_content = content
            
            # Enforce max entries
            if len(self._entries) > self.max_entries:
                self._entries.pop(0)
            
            # Save to disk
            self._save_history()
            
            logger.debug(f"Added clipboard entry: {entry.preview}")
            return True
    
    def get_history(self, limit: Optional[int] = None) -> List[ClipboardHistoryEntry]:
        """
        Get clipboard history.
        
        Args:
            limit: Maximum number of entries to return (None = all)
            
        Returns:
            List of clipboard entries (newest first)
        """
        with self._lock:
            entries = self._entries[::-1]  # Reverse for newest first
            if limit:
                entries = entries[:limit]
            return entries
    
    def search(self, query: str, case_sensitive: bool = False) -> List[ClipboardHistoryEntry]:
        """
        Search clipboard history.
        
        Args:
            query: Search query
            case_sensitive: Whether to match case
            
        Returns:
            Matching entries (newest first)
        """
        with self._lock:
            if not case_sensitive:
                query = query.lower()
            
            matches = []
            for entry in reversed(self._entries):
                content = entry.content if case_sensitive else entry.content.lower()
                if query in content:
                    matches.append(entry)
            
            return matches
    
    def get_entry(self, index: int) -> Optional[ClipboardHistoryEntry]:
        """
        Get entry by index (1-based, 1 = most recent).
        
        Args:
            index: Entry index (1-based)
            
        Returns:
            Entry or None if out of range
        """
        with self._lock:
            if index < 1 or index > len(self._entries):
                return None
            # Convert to 0-based index from end
            return self._entries[-(index)]
    
    def restore_entry(self, index: int) -> bool:
        """
        Restore an entry to clipboard.
        
        Args:
            index: Entry index (1-based, 1 = most recent)
            
        Returns:
            True if successful
        """
        entry = self.get_entry(index)
        if not entry:
            return False
        
        return copy_to_clipboard(entry.content)
    
    def clear_history(self) -> None:
        """Clear all clipboard history."""
        with self._lock:
            self._entries.clear()
            self._last_content = None
            self._save_history()
        logger.info("Clipboard history cleared")
    
    def start_monitoring(self) -> None:
        """Start background clipboard monitoring."""
        if self._monitoring:
            logger.warning("Clipboard monitoring already running")
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="ClipboardMonitor"
        )
        self._monitor_thread.start()
        logger.info("Clipboard monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop background clipboard monitoring."""
        if not self._monitoring:
            return
        
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
        logger.info("Clipboard monitoring stopped")
    
    def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self._monitoring:
            try:
                content = get_clipboard_content()
                if content:
                    self.add_entry(content)
            except Exception as e:
                logger.debug(f"Clipboard monitor error: {e}")
            
            time.sleep(self.MONITOR_INTERVAL)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get clipboard history statistics."""
        with self._lock:
            if not self._entries:
                return {
                    "total_entries": 0,
                    "oldest_entry": None,
                    "newest_entry": None,
                    "total_size_kb": 0
                }
            
            total_size = sum(len(e.content.encode('utf-8')) for e in self._entries)
            
            return {
                "total_entries": len(self._entries),
                "oldest_entry": self._entries[0].timestamp,
                "newest_entry": self._entries[-1].timestamp,
                "total_size_kb": total_size / 1024,
                "monitoring": self._monitoring
            }


class GlobalContext:
    """
    Global context manager for clipboard-aware operations.
    
    Tracks clipboard content and provides context for commands
    like "open that" or "move the clipboard".
    """
    
    def __init__(self):
        self._last_clipboard: Optional[str] = None
        self._clipboard_history: list[str] = []
    
    def update(self) -> None:
        """Update clipboard tracking."""
        current = get_clipboard_content()
        if current and current != self._last_clipboard:
            self._last_clipboard = current
            self._clipboard_history.append(current)
            
            # Keep only last 10
            if len(self._clipboard_history) > 10:
                self._clipboard_history.pop(0)
            
            logger.debug(f"Clipboard updated: {current[:50]}...")
    
    def get_current(self) -> Optional[str]:
        """Get current clipboard content."""
        return self._last_clipboard
    
    def get_history(self) -> list[str]:
        """Get clipboard history."""
        return self._clipboard_history.copy()
    
    def resolve_reference(self, text: str) -> Optional[str]:
        """
        Resolve clipboard references in text.
        
        Examples:
        - "that" -> last clipboard
        - "the clipboard" -> last clipboard
        - "clipboard" -> last clipboard
        
        Args:
            text: Input text
            
        Returns:
            Resolved path or None
        """
        text_lower = text.lower()
        
        clipboard_refs = ['that', 'the clipboard', 'clipboard', 'this']
        
        for ref in clipboard_refs:
            if ref in text_lower:
                return self._last_clipboard
        
        return None
