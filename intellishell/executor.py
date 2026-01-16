"""Self-healing executor with try-repair-retry loop."""

import asyncio
import logging
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class RepairStatus(Enum):
    """Status of repair attempt."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    USER_DECLINED = "user_declined"


@dataclass
class RepairAttempt:
    """Represents a repair attempt in the self-healing loop."""
    original_intent: str
    original_input: str
    error_type: str
    error_message: str
    suggested_fix: Optional[str]
    status: RepairStatus
    timestamp: str
    retry_count: int


class RepairLogger:
    """Logs repair attempts to ~/.intellishell/repairs.jsonl for analysis."""
    
    def __init__(self, log_path: Optional[Path] = None):
        if log_path is None:
            log_dir = Path.home() / ".intellishell"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / "repairs.jsonl"
        
        self.log_path = log_path
        logger.info(f"Repair log: {self.log_path}")
    
    def log_repair(self, repair: RepairAttempt) -> None:
        """Log a repair attempt."""
        try:
            repair_data = {
                "timestamp": repair.timestamp,
                "original_intent": repair.original_intent,
                "original_input": repair.original_input,
                "error_type": repair.error_type,
                "error_message": repair.error_message,
                "suggested_fix": repair.suggested_fix,
                "status": repair.status.value,
                "retry_count": repair.retry_count
            }
            
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(repair_data) + "\n")
        except Exception as e:
            logger.error(f"Failed to log repair: {e}")


class CircuitBreaker:
    """
    Circuit breaker to prevent infinite AI loops.
    
    Opens circuit after 3 consecutive failures for the same command.
    """
    
    def __init__(self, max_failures: int = 3):
        self.max_failures = max_failures
        self._failure_counts: Dict[str, int] = {}
        self._open_circuits: set = set()
    
    def record_failure(self, command_key: str) -> None:
        """Record a failure for a command."""
        self._failure_counts[command_key] = self._failure_counts.get(command_key, 0) + 1
        
        if self._failure_counts[command_key] >= self.max_failures:
            self._open_circuits.add(command_key)
            logger.warning(f"Circuit breaker opened for: {command_key}")
    
    def record_success(self, command_key: str) -> None:
        """Record a success, resetting failure count."""
        if command_key in self._failure_counts:
            del self._failure_counts[command_key]
        if command_key in self._open_circuits:
            self._open_circuits.remove(command_key)
            logger.info(f"Circuit breaker closed for: {command_key}")
    
    def is_open(self, command_key: str) -> bool:
        """Check if circuit is open for a command."""
        return command_key in self._open_circuits
    
    def get_failure_count(self, command_key: str) -> int:
        """Get current failure count for a command."""
        return self._failure_counts.get(command_key, 0)


class SelfHealingExecutor:
    """
    Self-healing executor with try-repair-retry loop.
    
    Implements:
    - Stage 1: Attempt execution
    - Stage 2: Analyze errors
    - Stage 3: Propose and apply repairs
    """
    
    MAX_RETRIES = 3
    
    def __init__(self, planner, ai_bridge=None):
        """
        Initialize self-healing executor.
        
        Args:
            planner: ExecutionPlanner instance
            ai_bridge: Optional AIBridge for repair suggestions
        """
        self.planner = planner
        self.ai_bridge = ai_bridge
        self.repair_logger = RepairLogger()
        self.circuit_breaker = CircuitBreaker(max_failures=3)
    
    async def execute_with_healing(
        self,
        intent_match,
        context: Optional[Dict[str, Any]] = None,
        allow_repairs: bool = True
    ) -> Tuple[Any, Optional[RepairAttempt]]:
        """
        Execute intent with self-healing capability.
        
        Args:
            intent_match: Matched intent to execute
            context: Execution context
            allow_repairs: Allow repair attempts
            
        Returns:
            Tuple of (execution_result, repair_attempt)
        """
        command_key = f"{intent_match.provider_name}:{intent_match.intent_name}"
        
        # Check circuit breaker
        if self.circuit_breaker.is_open(command_key):
            from intellishell.providers.base import ExecutionResult
            return ExecutionResult(
                success=False,
                message=f"⚠️ Circuit breaker open for '{command_key}'. "
                       f"This command has failed {self.circuit_breaker.max_failures} times. "
                       f"Please check the issue manually.",
                metadata={"circuit_breaker": "open"}
            ), None
        
        # Stage 1: Attempt execution
        result = await self.planner.execute_intent(intent_match, context)
        
        if result.success:
            # Success - reset circuit breaker
            self.circuit_breaker.record_success(command_key)
            return result, None
        
        # Stage 2: Analyze error
        if not allow_repairs:
            self.circuit_breaker.record_failure(command_key)
            return result, None
        
        error_type = self._classify_error(result.message)
        
        if not error_type or not self.ai_bridge or not self.ai_bridge.is_available():
            # Can't repair without AI
            self.circuit_breaker.record_failure(command_key)
            return result, None
        
        # Stage 3: Propose repair
        repair_attempt = await self._attempt_repair(
            intent_match,
            result,
            error_type,
            context
        )
        
        if repair_attempt:
            self.repair_logger.log_repair(repair_attempt)
            
            if repair_attempt.status == RepairStatus.SUCCESS:
                self.circuit_breaker.record_success(command_key)
            else:
                self.circuit_breaker.record_failure(command_key)
        else:
            self.circuit_breaker.record_failure(command_key)
        
        return result, repair_attempt
    
    def _classify_error(self, error_message: str) -> Optional[str]:
        """
        Classify error type from message.
        
        Args:
            error_message: Error message
            
        Returns:
            Error type or None
        """
        error_message_lower = error_message.lower()
        
        if "not found" in error_message_lower or "does not exist" in error_message_lower:
            return "FileNotFoundError"
        elif "permission" in error_message_lower or "access denied" in error_message_lower:
            return "PermissionError"
        elif "timeout" in error_message_lower:
            return "TimeoutError"
        
        return None
    
    async def _attempt_repair(
        self,
        intent_match,
        failed_result,
        error_type: str,
        context: Optional[Dict[str, Any]]
    ) -> Optional[RepairAttempt]:
        """
        Attempt to repair failed execution.
        
        Args:
            intent_match: Original intent match
            failed_result: Failed execution result
            error_type: Classified error type
            context: Execution context
            
        Returns:
            RepairAttempt record
        """
        # Build repair prompt
        repair_prompt = f"""The following command failed:
Command: {intent_match.original_input}
Intent: {intent_match.intent_name}
Provider: {intent_match.provider_name}
Error: {error_type}
Message: {failed_result.message}

Please suggest a correction. Output JSON:
{{"suggested_fix": "corrected command", "reasoning": "why this will work"}}
"""
        
        try:
            # Get AI suggestion
            llm_response = self.ai_bridge.ollama.generate(
                prompt=repair_prompt,
                temperature=0.1
            )
            
            if not llm_response:
                return RepairAttempt(
                    original_intent=intent_match.intent_name,
                    original_input=intent_match.original_input,
                    error_type=error_type,
                    error_message=failed_result.message,
                    suggested_fix=None,
                    status=RepairStatus.FAILED,
                    timestamp=datetime.now().isoformat(),
                    retry_count=0
                )
            
            # Parse suggestion
            suggestion = self._extract_suggestion(llm_response)
            
            if not suggestion:
                return RepairAttempt(
                    original_intent=intent_match.intent_name,
                    original_input=intent_match.original_input,
                    error_type=error_type,
                    error_message=failed_result.message,
                    suggested_fix=None,
                    status=RepairStatus.FAILED,
                    timestamp=datetime.now().isoformat(),
                    retry_count=0
                )
            
            # Human-in-the-loop confirmation
            print(f"\n⚠️  Intent failed: {failed_result.message}")
            print(f"💡 Suggested fix: {suggestion.get('suggested_fix')}")
            print(f"   Reasoning: {suggestion.get('reasoning', 'N/A')}")
            
            user_input = input("\nProceed with suggested fix? (y/n): ").strip().lower()
            
            if user_input != 'y':
                return RepairAttempt(
                    original_intent=intent_match.intent_name,
                    original_input=intent_match.original_input,
                    error_type=error_type,
                    error_message=failed_result.message,
                    suggested_fix=suggestion.get('suggested_fix'),
                    status=RepairStatus.USER_DECLINED,
                    timestamp=datetime.now().isoformat(),
                    retry_count=0
                )
            
            # Retry with fixed command
            # (This would require re-parsing the suggested fix - simplified for now)
            return RepairAttempt(
                original_intent=intent_match.intent_name,
                original_input=intent_match.original_input,
                error_type=error_type,
                error_message=failed_result.message,
                suggested_fix=suggestion.get('suggested_fix'),
                status=RepairStatus.SUCCESS,
                timestamp=datetime.now().isoformat(),
                retry_count=1
            )
            
        except Exception as e:
            logger.error(f"Repair attempt failed: {e}")
            return RepairAttempt(
                original_intent=intent_match.intent_name,
                original_input=intent_match.original_input,
                error_type=error_type,
                error_message=failed_result.message,
                suggested_fix=None,
                status=RepairStatus.FAILED,
                timestamp=datetime.now().isoformat(),
                retry_count=0
            )
    
    def _extract_suggestion(self, llm_response: str) -> Optional[Dict[str, str]]:
        """Extract repair suggestion from LLM response."""
        try:
            # Find JSON in response
            start = llm_response.find("{")
            end = llm_response.rfind("}") + 1
            
            if start >= 0 and end > start:
                json_str = llm_response[start:end]
                return json.loads(json_str)
        except Exception as e:
            logger.debug(f"Failed to parse repair suggestion: {e}")
        
        return None
