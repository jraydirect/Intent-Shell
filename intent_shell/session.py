"""Session state management for stateful context tracking."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path


@dataclass
class CommandEntry:
    """Represents a single command in history."""
    timestamp: datetime
    command: str
    intent_name: Optional[str]
    success: bool
    confidence: float = 0.0


@dataclass
class SessionState:
    """
    Tracks stateful context across commands.
    
    Maintains:
    - Command history
    - Last accessed directory
    - Last queried process
    - Session metadata
    """
    
    session_id: str
    start_time: datetime = field(default_factory=datetime.now)
    command_history: List[CommandEntry] = field(default_factory=list)
    last_directory: Optional[Path] = None
    last_process_queried: Optional[str] = None
    context_data: Dict[str, Any] = field(default_factory=dict)
    
    def add_command(
        self,
        command: str,
        intent_name: Optional[str] = None,
        success: bool = True,
        confidence: float = 0.0
    ) -> None:
        """Add a command to history."""
        entry = CommandEntry(
            timestamp=datetime.now(),
            command=command,
            intent_name=intent_name,
            success=success,
            confidence=confidence
        )
        self.command_history.append(entry)
    
    def get_recent_commands(self, count: int = 10) -> List[CommandEntry]:
        """Get most recent commands."""
        return self.command_history[-count:]
    
    def update_context(self, key: str, value: Any) -> None:
        """Update context data."""
        self.context_data[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context data."""
        return self.context_data.get(key, default)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        total_commands = len(self.command_history)
        successful_commands = sum(1 for cmd in self.command_history if cmd.success)
        
        return {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "duration": (datetime.now() - self.start_time).total_seconds(),
            "total_commands": total_commands,
            "successful_commands": successful_commands,
            "success_rate": (successful_commands / total_commands * 100) if total_commands > 0 else 0,
        }
