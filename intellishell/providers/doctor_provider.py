"""Doctor provider for system health diagnostics."""

from typing import Optional, Dict, Any
from intellishell.providers.base import (
    BaseProvider,
    IntentTrigger,
    ExecutionResult,
    ProviderCapability
)
from intellishell.doctor import SystemDoctor
import logging

logger = logging.getLogger(__name__)


class DoctorProvider(BaseProvider):
    """Provider for system health checks and diagnostics."""
    
    def __init__(self):
        super().__init__()
        self.doctor = SystemDoctor()
    
    @property
    def name(self) -> str:
        return "doctor"
    
    @property
    def description(self) -> str:
        return "System health diagnostics and checks"
    
    def _initialize_triggers(self) -> None:
        """Initialize doctor-related triggers."""
        self.capabilities = [
            ProviderCapability.READ_ONLY,
            ProviderCapability.ASYNC,
        ]
        
        self.triggers = [
            IntentTrigger(
                pattern="check system health",
                intent_name="system_health",
                weight=1.0,
                aliases=[
                    "health check",
                    "system status",
                    "diagnose system",
                    "doctor check"
                ]
            ),
            IntentTrigger(
                pattern="check dependencies",
                intent_name="check_deps",
                weight=1.0,
                aliases=[
                    "dependency check",
                    "what's installed",
                    "check packages"
                ]
            ),
        ]
    
    async def execute(
        self,
        intent_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """Execute doctor operation."""
        try:
            if intent_name == "system_health":
                return await self._system_health()
            elif intent_name == "check_deps":
                return await self._check_dependencies()
            else:
                return ExecutionResult(
                    success=False,
                    message=f"Unknown intent: {intent_name}"
                )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Doctor error: {e}"
            )
    
    async def _system_health(self) -> ExecutionResult:
        """Run complete system health check."""
        self.doctor.run_all_checks()
        report = self.doctor.format_report()
        summary = self.doctor.get_summary()
        
        return ExecutionResult(
            success=summary["overall_status"] == "ok",
            message=report,
            data={"summary": summary, "checks": self.doctor.checks}
        )
    
    async def _check_dependencies(self) -> ExecutionResult:
        """Check dependency status."""
        checks = self.doctor.run_all_checks()
        
        # Filter for dependency-related checks
        dep_checks = [c for c in checks if "Depend" in c.name or "Ollama" in c.name or "ChromaDB" in c.name]
        
        lines = ["Dependency Status:\n"]
        
        for check in dep_checks:
            if check.status == "ok":
                icon = "✓"
            elif check.status == "warning":
                icon = "⚠"
            else:
                icon = "✗"
            
            lines.append(f"{icon} {check.name}: {check.message}")
        
        return ExecutionResult(
            success=True,
            message="\n".join(lines),
            data={"checks": dep_checks}
        )
