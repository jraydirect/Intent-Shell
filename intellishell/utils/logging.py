"""Structured logging configuration."""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


def setup_logging(
    debug: bool = False,
    log_file: Optional[Path] = None
) -> None:
    """
    Configure structured logging for IntelliShell.
    
    Args:
        debug: Enable debug logging
        log_file: Optional log file path (defaults to ~/.intellishell/logs/shell.log)
    """
    # Determine log level
    log_level = logging.DEBUG if debug else logging.INFO
    
    # Create log directory
    if log_file is None:
        log_dir = Path.home() / ".intellishell" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "shell.log"
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler (only INFO and above unless debug)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_format = logging.Formatter(
        "%(levelname)s: %(message)s"
    )
    console_handler.setFormatter(console_format)
    
    # File handler (rotating)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_format)
    
    # Add handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Log startup
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized (level={logging.getLevelName(log_level)})")
    logger.debug(f"Log file: {log_file}")
