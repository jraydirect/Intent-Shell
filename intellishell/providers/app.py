"""Application provider for launching Windows applications."""

import os
import subprocess
from typing import Optional, Dict, Any
from intellishell.providers.base import (
    BaseProvider,
    IntentTrigger,
    ExecutionResult,
    ProviderCapability
)


class AppProvider(BaseProvider):
    """Provider for launching Windows applications."""
    
    @property
    def name(self) -> str:
        return "app"
    
    @property
    def description(self) -> str:
        return "Application launcher for Windows programs"
    
    def _initialize_triggers(self) -> None:
        """Initialize app-related triggers."""
        self.capabilities = [
            ProviderCapability.READ_ONLY,
            ProviderCapability.ASYNC,
        ]
        
        self.triggers = [
            IntentTrigger(
                pattern="open notepad",
                intent_name="launch_notepad",
                weight=1.0,
                aliases=["start notepad", "notepad", "text editor"]
            ),
            IntentTrigger(
                pattern="open calculator",
                intent_name="launch_calculator",
                weight=1.0,
                aliases=["start calculator", "calculator", "calc"]
            ),
            IntentTrigger(
                pattern="open settings",
                intent_name="launch_settings",
                weight=1.0,
                aliases=["windows settings", "system settings", "settings"]
            ),
            IntentTrigger(
                pattern="open task manager",
                intent_name="launch_task_manager",
                weight=1.0,
                aliases=["task manager", "taskmgr"]
            ),
            IntentTrigger(
                pattern="open control panel",
                intent_name="launch_control_panel",
                weight=1.0,
                aliases=["control panel", "control"]
            ),
            IntentTrigger(
                pattern="open startup folder",
                intent_name="open_startup",
                weight=1.0,
                aliases=["startup folder", "startup apps"]
            ),
        ]
    
    async def execute(
        self,
        intent_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """Execute application launch."""
        try:
            if intent_name == "launch_notepad":
                return await self._launch_notepad()
            elif intent_name == "launch_calculator":
                return await self._launch_calculator()
            elif intent_name == "launch_settings":
                return await self._launch_settings()
            elif intent_name == "launch_task_manager":
                return await self._launch_task_manager()
            elif intent_name == "launch_control_panel":
                return await self._launch_control_panel()
            elif intent_name == "open_startup":
                return await self._open_startup()
            else:
                return ExecutionResult(
                    success=False,
                    message=f"Unknown intent: {intent_name}"
                )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Execution error: {e}"
            )
    
    async def _launch_notepad(self) -> ExecutionResult:
        """Launch Notepad."""
        os.startfile("notepad")
        return ExecutionResult(
            success=True,
            message="Opening Notepad...",
            data={"app": "notepad"}
        )
    
    async def _launch_calculator(self) -> ExecutionResult:
        """Launch Calculator."""
        os.startfile("calc")
        return ExecutionResult(
            success=True,
            message="Opening Calculator...",
            data={"app": "calc"}
        )
    
    async def _launch_settings(self) -> ExecutionResult:
        """Launch Windows Settings."""
        os.startfile("ms-settings:")
        return ExecutionResult(
            success=True,
            message="Opening Windows Settings...",
            data={"app": "ms-settings:"}
        )
    
    async def _launch_task_manager(self) -> ExecutionResult:
        """Launch Task Manager."""
        subprocess.Popen(["taskmgr"])
        return ExecutionResult(
            success=True,
            message="Opening Task Manager...",
            data={"app": "taskmgr"}
        )
    
    async def _launch_control_panel(self) -> ExecutionResult:
        """Launch Control Panel."""
        os.startfile("control")
        return ExecutionResult(
            success=True,
            message="Opening Control Panel...",
            data={"app": "control"}
        )
    
    async def _open_startup(self) -> ExecutionResult:
        """Open Startup folder."""
        subprocess.run(["explorer", "shell:Startup"], check=True)
        return ExecutionResult(
            success=True,
            message="Opening Startup folder...",
            data={"shell_path": "shell:Startup"}
        )
