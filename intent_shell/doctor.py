"""System health diagnostics for Intent Shell."""

import sys
import logging
from typing import Dict, Any, List
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class HealthCheck:
    """Represents a health check result."""
    name: str
    status: str  # 'ok', 'warning', 'error'
    message: str
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


class SystemDoctor:
    """
    System health diagnostics module.
    
    Checks:
    - Python version and environment
    - Dependency availability
    - Ollama connectivity
    - Vector DB status
    - Admin privileges
    - File system permissions
    """
    
    def __init__(self):
        self.checks: List[HealthCheck] = []
    
    def run_all_checks(self) -> List[HealthCheck]:
        """
        Run all health checks.
        
        Returns:
            List of HealthCheck results
        """
        self.checks = []
        
        self.checks.append(self._check_python_version())
        self.checks.append(self._check_dependencies())
        self.checks.append(self._check_ollama())
        self.checks.append(self._check_chromadb())
        self.checks.append(self._check_admin_privileges())
        self.checks.append(self._check_filesystem())
        self.checks.append(self._check_log_directory())
        
        return self.checks
    
    def _check_python_version(self) -> HealthCheck:
        """Check Python version."""
        version = sys.version_info
        version_str = f"{version.major}.{version.minor}.{version.micro}"
        
        if version.major == 3 and version.minor >= 8:
            return HealthCheck(
                name="Python Version",
                status="ok",
                message=f"Python {version_str}",
                details={"version": version_str}
            )
        else:
            return HealthCheck(
                name="Python Version",
                status="warning",
                message=f"Python {version_str} (3.8+ recommended)",
                details={"version": version_str}
            )
    
    def _check_dependencies(self) -> HealthCheck:
        """Check core dependencies."""
        missing = []
        installed = []
        
        deps = {
            "pydantic": "AI bridge",
            "requests": "HTTP client",
        }
        
        for package, purpose in deps.items():
            try:
                __import__(package)
                installed.append(f"{package} ({purpose})")
            except ImportError:
                missing.append(f"{package} ({purpose})")
        
        if not missing:
            return HealthCheck(
                name="Core Dependencies",
                status="ok",
                message=f"All core dependencies installed",
                details={"installed": installed}
            )
        else:
            return HealthCheck(
                name="Core Dependencies",
                status="warning",
                message=f"Missing: {', '.join(missing)}",
                details={"missing": missing, "installed": installed}
            )
    
    def _check_ollama(self) -> HealthCheck:
        """Check Ollama availability."""
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            
            if response.status_code == 200:
                data = response.json()
                models = [m.get("name") for m in data.get("models", [])]
                
                return HealthCheck(
                    name="Ollama",
                    status="ok",
                    message=f"Ollama running with {len(models)} model(s)",
                    details={"models": models}
                )
            else:
                return HealthCheck(
                    name="Ollama",
                    status="warning",
                    message=f"Ollama responded with status {response.status_code}",
                    details={"status_code": response.status_code}
                )
        except ImportError:
            return HealthCheck(
                name="Ollama",
                status="error",
                message="requests library not installed",
                details={}
            )
        except Exception as e:
            return HealthCheck(
                name="Ollama",
                status="warning",
                message=f"Ollama not running: {e}",
                details={"error": str(e)}
            )
    
    def _check_chromadb(self) -> HealthCheck:
        """Check ChromaDB availability."""
        try:
            import chromadb
            
            # Try to create a test client
            vector_store_path = Path.home() / ".intent" / "vector_store"
            
            if vector_store_path.exists():
                return HealthCheck(
                    name="ChromaDB",
                    status="ok",
                    message="ChromaDB installed, vector store exists",
                    details={"path": str(vector_store_path)}
                )
            else:
                return HealthCheck(
                    name="ChromaDB",
                    status="ok",
                    message="ChromaDB installed (no vector store yet)",
                    details={}
                )
        except ImportError:
            return HealthCheck(
                name="ChromaDB",
                status="warning",
                message="ChromaDB not installed (semantic memory disabled)",
                details={"install": "pip install chromadb"}
            )
    
    def _check_admin_privileges(self) -> HealthCheck:
        """Check if running with admin privileges."""
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            
            if is_admin:
                return HealthCheck(
                    name="Admin Privileges",
                    status="ok",
                    message="Running with Administrator privileges",
                    details={"is_admin": True}
                )
            else:
                return HealthCheck(
                    name="Admin Privileges",
                    status="warning",
                    message="Not running as Administrator (some commands may fail)",
                    details={"is_admin": False}
                )
        except Exception as e:
            return HealthCheck(
                name="Admin Privileges",
                status="error",
                message=f"Could not check admin status: {e}",
                details={}
            )
    
    def _check_filesystem(self) -> HealthCheck:
        """Check filesystem access to common directories."""
        dirs_to_check = {
            "Desktop": Path.home() / "Desktop",
            "Downloads": Path.home() / "Downloads",
            "Documents": Path.home() / "Documents",
        }
        
        accessible = []
        inaccessible = []
        
        for name, path in dirs_to_check.items():
            if path.exists() and path.is_dir():
                accessible.append(name)
            else:
                inaccessible.append(name)
        
        if not inaccessible:
            return HealthCheck(
                name="Filesystem Access",
                status="ok",
                message="All common directories accessible",
                details={"accessible": accessible}
            )
        else:
            return HealthCheck(
                name="Filesystem Access",
                status="warning",
                message=f"Some directories not found: {', '.join(inaccessible)}",
                details={"accessible": accessible, "inaccessible": inaccessible}
            )
    
    def _check_log_directory(self) -> HealthCheck:
        """Check log directory access."""
        log_dir = Path.home() / ".intent"
        
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Try to write test file
            test_file = log_dir / ".health_check"
            test_file.write_text("test")
            test_file.unlink()
            
            return HealthCheck(
                name="Log Directory",
                status="ok",
                message=f"Log directory writable: {log_dir}",
                details={"path": str(log_dir)}
            )
        except PermissionError:
            return HealthCheck(
                name="Log Directory",
                status="error",
                message=f"Permission denied: {log_dir}",
                details={"path": str(log_dir)}
            )
        except Exception as e:
            return HealthCheck(
                name="Log Directory",
                status="error",
                message=f"Error accessing log directory: {e}",
                details={"path": str(log_dir), "error": str(e)}
            )
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of health checks."""
        if not self.checks:
            self.run_all_checks()
        
        ok_count = sum(1 for c in self.checks if c.status == "ok")
        warning_count = sum(1 for c in self.checks if c.status == "warning")
        error_count = sum(1 for c in self.checks if c.status == "error")
        
        return {
            "total_checks": len(self.checks),
            "ok": ok_count,
            "warnings": warning_count,
            "errors": error_count,
            "overall_status": "ok" if error_count == 0 else "degraded"
        }
    
    def format_report(self) -> str:
        """Format health check report as string."""
        if not self.checks:
            self.run_all_checks()
        
        lines = ["\n╔═══════════════════════════════════════════════════╗"]
        lines.append("║        Intent Shell - System Health Check        ║")
        lines.append("╚═══════════════════════════════════════════════════╝\n")
        
        for check in self.checks:
            if check.status == "ok":
                icon = "✓"
            elif check.status == "warning":
                icon = "⚠"
            else:
                icon = "✗"
            
            lines.append(f"{icon} {check.name}: {check.message}")
        
        summary = self.get_summary()
        lines.append(f"\nSummary: {summary['ok']} OK, {summary['warnings']} Warnings, {summary['errors']} Errors")
        lines.append(f"Overall Status: {summary['overall_status'].upper()}")
        
        return "\n".join(lines)
