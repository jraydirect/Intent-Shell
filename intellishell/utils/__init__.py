"""Utility modules for IntelliShell."""

from intellishell.utils.clipboard import (
    copy_to_clipboard,
    should_pipe_to_clipboard,
    get_clipboard_content,
    GlobalContext
)
from intellishell.utils.logging import setup_logging
from intellishell.utils.notifications import send_notification, check_notification_support

__all__ = [
    "copy_to_clipboard",
    "should_pipe_to_clipboard",
    "get_clipboard_content",
    "GlobalContext",
    "setup_logging",
    "send_notification",
    "check_notification_support"
]
