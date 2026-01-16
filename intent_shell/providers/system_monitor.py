"""System monitoring provider for system information queries."""

import platform
import subprocess
from typing import Optional, Dict, Any
from intent_shell.providers.base import (
    BaseProvider,
    IntentTrigger,
    ExecutionResult,
    ProviderCapability
)


class SystemMonitorProvider(BaseProvider):
    """Provider for system monitoring and information queries."""
    
    @property
    def name(self) -> str:
        return "system_monitor"
    
    @property
    def description(self) -> str:
        return "System information and monitoring"
    
    def _initialize_triggers(self) -> None:
        """Initialize system monitoring triggers."""
        self.capabilities = [
            ProviderCapability.READ_ONLY,
            ProviderCapability.ASYNC,
        ]
        
        self.triggers = [
            IntentTrigger(
                pattern="system info",
                intent_name="get_system_info",
                weight=1.0,
                aliases=["show system info", "system information", "about system"]
            ),
            IntentTrigger(
                pattern="get hostname",
                intent_name="get_hostname",
                weight=1.0,
                aliases=["show hostname", "computer name", "hostname"]
            ),
            IntentTrigger(
                pattern="get username",
                intent_name="get_username",
                weight=1.0,
                aliases=["show username", "current user", "username"]
            ),
            IntentTrigger(
                pattern="disk space",
                intent_name="get_disk_space",
                weight=1.0,
                aliases=["show disk space", "storage info", "drive space"]
            ),
        ]
    
    async def execute(
        self,
        intent_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """Execute system monitoring query."""
        try:
            if intent_name == "get_system_info":
                return await self._get_system_info()
            elif intent_name == "get_hostname":
                return await self._get_hostname()
            elif intent_name == "get_username":
                return await self._get_username()
            elif intent_name == "get_disk_space":
                return await self._get_disk_space()
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
    
    async def _get_system_info(self) -> ExecutionResult:
        """Get comprehensive system information."""
        info = {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "hostname": platform.node(),
        }
        
        message = f"""System Information:
  OS: {info['system']} {info['release']}
  Machine: {info['machine']}
  Processor: {info['processor']}
  Hostname: {info['hostname']}"""
        
        return ExecutionResult(
            success=True,
            message=message,
            data=info
        )
    
    async def _get_hostname(self) -> ExecutionResult:
        """Get system hostname."""
        hostname = platform.node()
        return ExecutionResult(
            success=True,
            message=f"Hostname: {hostname}",
            data={"hostname": hostname}
        )
    
    async def _get_username(self) -> ExecutionResult:
        """Get current username."""
        import os
        username = os.getenv("USERNAME", "Unknown")
        return ExecutionResult(
            success=True,
            message=f"Current User: {username}",
            data={"username": username}
        )
    
    async def _get_disk_space(self) -> ExecutionResult:
        """Get disk space information."""
        try:
            import psutil
            partitions = psutil.disk_partitions()
            disk_info = []
            
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_info.append({
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "total_gb": usage.total / (1024**3),
                        "used_gb": usage.used / (1024**3),
                        "free_gb": usage.free / (1024**3),
                        "percent": usage.percent
                    })
                except PermissionError:
                    continue
            
            message_lines = ["Disk Space:"]
            for disk in disk_info:
                message_lines.append(
                    f"  {disk['device']} - {disk['free_gb']:.1f}GB free of "
                    f"{disk['total_gb']:.1f}GB ({disk['percent']}% used)"
                )
            
            return ExecutionResult(
                success=True,
                message="\n".join(message_lines),
                data={"disks": disk_info}
            )
        except ImportError:
            return ExecutionResult(
                success=False,
                message="psutil not installed. Install with: pip install psutil"
            )
