"""Terminal styling and color utilities for Intent Shell."""

import sys
import os
from typing import Optional


class TerminalColors:
    """ANSI color codes for terminal styling."""
    
    # Reset
    RESET = "\033[0m"
    
    # Basic colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Bright colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    
    # Royal Blue (RGB: 65, 105, 225) - using 24-bit color
    ROYAL_BLUE = "\033[38;2;65;105;225m"
    
    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"
    
    # Styles
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"
    REVERSE = "\033[7m"
    
    @staticmethod
    def supports_color() -> bool:
        """Check if terminal supports color."""
        # Check if we're in a terminal
        if not sys.stdout.isatty():
            return False
        
        # Check Windows
        if os.name == 'nt':
            # Windows Terminal and modern PowerShell support ANSI
            # Check for TERM or WT_SESSION
            return os.environ.get('WT_SESSION') is not None or \
                   os.environ.get('TERM') is not None or \
                   os.environ.get('ANSICON') is not None
        
        # Unix-like systems
        return os.environ.get('TERM') != 'dumb'
    
    @staticmethod
    def colorize(text: str, color: str) -> str:
        """Apply color to text if terminal supports it."""
        if TerminalColors.supports_color():
            return f"{color}{text}{TerminalColors.RESET}"
        return text
    
    @staticmethod
    def set_terminal_color(color: str) -> None:
        """Set terminal foreground color (royal blue for Intent Shell)."""
        if TerminalColors.supports_color():
            sys.stdout.write(color)
            sys.stdout.flush()
    
    @staticmethod
    def reset_terminal_color() -> None:
        """Reset terminal color to default."""
        if TerminalColors.supports_color():
            sys.stdout.write(TerminalColors.RESET)
            sys.stdout.flush()


def enable_royal_blue_terminal() -> None:
    """Enable royal blue terminal color for Intent Shell."""
    TerminalColors.set_terminal_color(TerminalColors.ROYAL_BLUE)


def reset_terminal_color() -> None:
    """Reset terminal color when exiting Intent Shell."""
    TerminalColors.reset_terminal_color()
