"""Safety levels and HITL (Human-in-the-Loop) controls."""

from enum import Enum, auto
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SafetyLevel(Enum):
    """Safety categorization for intents."""
    GREEN = auto()   # Read-only, no confirmation needed
    YELLOW = auto()  # State changes, confirm if last action failed
    RED = auto()     # Destructive, always confirm + log


# Safety level registry for intents
INTENT_SAFETY_LEVELS = {
    # GREEN: Read-only operations
    "open_desktop": SafetyLevel.GREEN,
    "open_downloads": SafetyLevel.GREEN,
    "open_documents": SafetyLevel.GREEN,
    "open_home": SafetyLevel.GREEN,
    "open_recycle_bin": SafetyLevel.GREEN,
    "open_explorer": SafetyLevel.GREEN,
    "list_files": SafetyLevel.GREEN,
    "list_downloads": SafetyLevel.GREEN,
    "list_desktop": SafetyLevel.GREEN,
    "get_system_info": SafetyLevel.GREEN,
    "get_hostname": SafetyLevel.GREEN,
    "get_username": SafetyLevel.GREEN,
    "get_disk_space": SafetyLevel.GREEN,
    "list_processes": SafetyLevel.GREEN,
    "check_admin": SafetyLevel.GREEN,
    "recall_command": SafetyLevel.GREEN,
    "recall_folder": SafetyLevel.GREEN,
    "show_recent": SafetyLevel.GREEN,
    "list_watches": SafetyLevel.GREEN,
    
    # Clipboard operations
    "show_clipboard_history": SafetyLevel.GREEN,
    "search_clipboard": SafetyLevel.GREEN,
    "restore_clipboard": SafetyLevel.GREEN,
    "clipboard_stats": SafetyLevel.GREEN,
    "start_clipboard_monitoring": SafetyLevel.YELLOW,
    "stop_clipboard_monitoring": SafetyLevel.YELLOW,
    "clear_clipboard_history": SafetyLevel.YELLOW,
    
    # YELLOW: State-changing operations
    "launch_notepad": SafetyLevel.YELLOW,
    "launch_calculator": SafetyLevel.YELLOW,
    "launch_settings": SafetyLevel.YELLOW,
    "launch_task_manager": SafetyLevel.YELLOW,
    "launch_control_panel": SafetyLevel.YELLOW,
    "open_startup": SafetyLevel.YELLOW,
    "watch_downloads": SafetyLevel.YELLOW,
    "watch_for_file_type": SafetyLevel.YELLOW,
    "stop_watch": SafetyLevel.YELLOW,
    
    # RED: Potentially destructive operations
    "kill_process": SafetyLevel.RED,
    "kill_by_name": SafetyLevel.RED,
    "kill_most_memory": SafetyLevel.RED,
}


class SafetyController:
    """
    Human-in-the-loop safety controller.
    
    Enforces confirmation requirements based on safety levels.
    """
    
    def __init__(self):
        self.last_action_failed = False
        self._red_action_log = []
    
    def get_safety_level(self, intent_name: str) -> SafetyLevel:
        """
        Get safety level for an intent.
        
        Args:
            intent_name: Intent name
            
        Returns:
            SafetyLevel (defaults to YELLOW if unknown)
        """
        return INTENT_SAFETY_LEVELS.get(intent_name, SafetyLevel.YELLOW)
    
    def requires_confirmation(
        self,
        intent_name: str,
        force: bool = False
    ) -> bool:
        """
        Check if intent requires user confirmation.
        
        Args:
            intent_name: Intent to check
            force: Force confirmation regardless of rules
            
        Returns:
            True if confirmation required
        """
        if force:
            return True
        
        safety_level = self.get_safety_level(intent_name)
        
        if safety_level == SafetyLevel.GREEN:
            return False
        elif safety_level == SafetyLevel.YELLOW:
            # Require confirmation only if last action failed
            return self.last_action_failed
        elif safety_level == SafetyLevel.RED:
            # Always require confirmation
            return True
        
        return False
    
    def request_confirmation(
        self,
        intent_name: str,
        provider_name: str,
        description: str,
        safety_level: SafetyLevel
    ) -> bool:
        """
        Request user confirmation for an action.
        
        Args:
            intent_name: Intent name
            provider_name: Provider name
            description: Action description
            safety_level: Safety level
            
        Returns:
            True if user confirmed, False otherwise
        """
        # Color code by safety level
        if safety_level == SafetyLevel.RED:
            icon = "🔴"
            level_str = "DESTRUCTIVE"
        elif safety_level == SafetyLevel.YELLOW:
            icon = "🟡"
            level_str = "STATE-CHANGING"
        else:
            icon = "🟢"
            level_str = "READ-ONLY"
        
        print(f"\n{icon} Safety Check - {level_str}")
        print(f"Intent: {intent_name}")
        print(f"Provider: {provider_name}")
        print(f"Action: {description}")
        
        if safety_level == SafetyLevel.RED:
            print("⚠️  This action is potentially DESTRUCTIVE")
        
        response = input("\nProceed? (y/n): ").strip().lower()
        
        confirmed = response == 'y'
        
        # Log RED actions
        if safety_level == SafetyLevel.RED:
            from datetime import datetime
            self._red_action_log.append({
                "timestamp": datetime.now().isoformat(),
                "intent": intent_name,
                "provider": provider_name,
                "confirmed": confirmed
            })
            logger.warning(
                f"RED action {'CONFIRMED' if confirmed else 'DECLINED'}: "
                f"{intent_name}"
            )
        
        return confirmed
    
    def record_action_result(self, success: bool) -> None:
        """
        Record result of last action.
        
        Args:
            success: Whether action succeeded
        """
        self.last_action_failed = not success
    
    def get_red_action_log(self) -> list:
        """Get log of all RED actions attempted."""
        return self._red_action_log.copy()
