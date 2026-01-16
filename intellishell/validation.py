"""Self-correction and validation module."""

import os
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from difflib import get_close_matches
import logging

logger = logging.getLogger(__name__)


class PathValidator:
    """
    Validates and auto-corrects paths.
    
    Provides typo correction and existence checking.
    """
    
    # Common Windows paths
    COMMON_PATHS = {
        "desktop": lambda: Path.home() / "Desktop",
        "downloads": lambda: Path.home() / "Downloads",
        "documents": lambda: Path.home() / "Documents",
        "pictures": lambda: Path.home() / "Pictures",
        "videos": lambda: Path.home() / "Videos",
        "music": lambda: Path.home() / "Music",
        "temp": lambda: Path(os.environ.get("TEMP", "")),
        "appdata": lambda: Path(os.environ.get("APPDATA", "")),
        "programfiles": lambda: Path(os.environ.get("PROGRAMFILES", "")),
    }
    
    def validate_path(self, path: str | Path) -> Tuple[bool, Optional[Path]]:
        """
        Validate if path exists.
        
        Args:
            path: Path to validate
            
        Returns:
            Tuple of (exists, resolved_path)
        """
        try:
            p = Path(path)
            exists = p.exists()
            return exists, p if exists else None
        except Exception as e:
            logger.debug(f"Path validation error: {e}")
            return False, None
    
    def auto_correct_path(
        self,
        path_input: str,
        threshold: float = 0.6
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Auto-correct common path typos.
        
        Args:
            path_input: User's path input (may have typos)
            threshold: Similarity threshold for correction
            
        Returns:
            Tuple of (corrected, original_intent, corrected_path, message)
        """
        path_lower = path_input.lower().strip()
        
        # Check for close matches with common paths
        matches = get_close_matches(
            path_lower,
            self.COMMON_PATHS.keys(),
            n=1,
            cutoff=threshold
        )
        
        if matches:
            matched_key = matches[0]
            corrected_path = str(self.COMMON_PATHS[matched_key]())
            
            if matched_key != path_lower:
                message = f"Found typo: '{path_input}' → '{matched_key}'"
                return True, matched_key, corrected_path, message
        
        return False, None, None, None
    
    def suggest_similar_files(
        self,
        filename: str,
        directory: Path,
        limit: int = 3
    ) -> List[str]:
        """
        Suggest similar files in directory.
        
        Args:
            filename: Target filename
            directory: Directory to search
            limit: Max suggestions
            
        Returns:
            List of similar filenames
        """
        if not directory.exists() or not directory.is_dir():
            return []
        
        try:
            files = [f.name for f in directory.iterdir()]
            matches = get_close_matches(filename, files, n=limit, cutoff=0.6)
            return matches
        except Exception as e:
            logger.debug(f"File suggestion error: {e}")
            return []


class ProcessValidator:
    """
    Validates process names and provides corrections.
    """
    
    # Common process names
    COMMON_PROCESSES = [
        "notepad.exe", "calculator.exe", "chrome.exe", "firefox.exe",
        "edge.exe", "explorer.exe", "cmd.exe", "powershell.exe",
        "code.exe", "outlook.exe", "excel.exe", "word.exe"
    ]
    
    def auto_correct_process(
        self,
        process_input: str,
        threshold: float = 0.7
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Auto-correct process name typos.
        
        Args:
            process_input: User's process input
            threshold: Similarity threshold
            
        Returns:
            Tuple of (corrected, corrected_name, message)
        """
        process_lower = process_input.lower().strip()
        
        # Ensure .exe extension
        if not process_lower.endswith(".exe"):
            process_lower += ".exe"
        
        # Check for close matches
        matches = get_close_matches(
            process_lower,
            self.COMMON_PROCESSES,
            n=1,
            cutoff=threshold
        )
        
        if matches:
            corrected = matches[0]
            if corrected != process_lower:
                message = f"Auto-corrected: '{process_input}' → '{corrected}'"
                return True, corrected, message
        
        return False, None, None


class SelfCorrection:
    """
    High-level self-correction interface.
    
    Validates and corrects user inputs before execution.
    """
    
    def __init__(self):
        """Initialize self-correction module."""
        self.path_validator = PathValidator()
        self.process_validator = ProcessValidator()
    
    def validate_and_correct(
        self,
        user_input: str,
        intent_name: str,
        entities: List[Dict] = None
    ) -> Tuple[bool, Optional[str], List[str]]:
        """
        Validate and correct user input.
        
        Args:
            user_input: Original user input
            intent_name: Matched intent
            entities: Extracted entities
            
        Returns:
            Tuple of (needs_correction, corrected_input, messages)
        """
        messages = []
        corrected_input = user_input
        needs_correction = False
        
        # Path-related intents
        if intent_name in ["open_desktop", "open_downloads", "open_documents"]:
            # Extract path reference from input
            for path_name in ["desktop", "downloads", "documents"]:
                if path_name in user_input.lower():
                    corrected, _, corrected_path, msg = self.path_validator.auto_correct_path(
                        path_name
                    )
                    if corrected:
                        needs_correction = True
                        messages.append(msg)
        
        # Process-related intents
        if intent_name in ["kill_by_name", "kill_process"]:
            # Try to extract process name
            words = user_input.lower().split()
            for word in words:
                if word not in ["kill", "stop", "close", "terminate"]:
                    corrected, corrected_name, msg = self.process_validator.auto_correct_process(
                        word
                    )
                    if corrected:
                        needs_correction = True
                        messages.append(msg)
                        corrected_input = user_input.replace(word, corrected_name)
                        break
        
        return needs_correction, corrected_input if needs_correction else None, messages
