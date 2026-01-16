"""Clipboard utilities for piping output and reading global context."""

from typing import Optional
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
