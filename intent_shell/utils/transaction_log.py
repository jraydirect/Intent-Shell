"""Transaction logging for intent-action pairs."""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class TransactionLogger:
    """
    Logs every intent-action pair to JSONL for future analysis.
    
    Log format: One JSON object per line
    Location: ~/.intent/history.jsonl
    """
    
    def __init__(self, log_path: Optional[Path] = None):
        """
        Initialize transaction logger.
        
        Args:
            log_path: Optional custom log path
        """
        if log_path is None:
            log_dir = Path.home() / ".intent"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / "history.jsonl"
        
        self.log_path = log_path
        logger.info(f"Transaction log: {self.log_path}")
    
    def log_transaction(
        self,
        user_input: str,
        intent_name: Optional[str],
        provider_name: Optional[str],
        confidence: float,
        success: bool,
        result_message: Optional[str] = None,
        entities: Optional[list] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a transaction to JSONL.
        
        Args:
            user_input: Original user input
            intent_name: Matched intent name
            provider_name: Provider that executed the intent
            confidence: Confidence score
            success: Whether execution succeeded
            result_message: Result message
            entities: Extracted entities
            metadata: Additional metadata
        """
        transaction = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "intent_name": intent_name,
            "provider_name": provider_name,
            "confidence": confidence,
            "success": success,
            "result_message": result_message,
            "entities": entities or [],
            "metadata": metadata or {}
        }
        
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(transaction) + "\n")
        except Exception as e:
            logger.error(f"Failed to write transaction log: {e}")
    
    def read_history(self, limit: int = 100) -> list[Dict]:
        """
        Read transaction history.
        
        Args:
            limit: Maximum number of transactions to read (from end)
            
        Returns:
            List of transaction dictionaries
        """
        if not self.log_path.exists():
            return []
        
        try:
            transactions = []
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        transactions.append(json.loads(line))
            
            # Return last N transactions
            return transactions[-limit:]
        except Exception as e:
            logger.error(f"Failed to read transaction log: {e}")
            return []
    
    def search_history(
        self,
        query: str = None,
        intent_name: str = None,
        success: Optional[bool] = None,
        limit: int = 50
    ) -> list[Dict]:
        """
        Search transaction history.
        
        Args:
            query: Search in user_input
            intent_name: Filter by intent name
            success: Filter by success status
            limit: Maximum results
            
        Returns:
            Filtered list of transactions
        """
        history = self.read_history(limit=1000)  # Read more for filtering
        
        filtered = []
        for tx in history:
            # Apply filters
            if query and query.lower() not in tx.get("user_input", "").lower():
                continue
            if intent_name and tx.get("intent_name") != intent_name:
                continue
            if success is not None and tx.get("success") != success:
                continue
            
            filtered.append(tx)
        
        return filtered[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics from transaction log.
        
        Returns:
            Statistics dictionary
        """
        history = self.read_history(limit=10000)
        
        if not history:
            return {"total": 0}
        
        total = len(history)
        successful = sum(1 for tx in history if tx.get("success"))
        
        # Intent frequency
        intent_counts = {}
        for tx in history:
            intent = tx.get("intent_name")
            if intent:
                intent_counts[intent] = intent_counts.get(intent, 0) + 1
        
        # Provider frequency
        provider_counts = {}
        for tx in history:
            provider = tx.get("provider_name")
            if provider:
                provider_counts[provider] = provider_counts.get(provider, 0) + 1
        
        return {
            "total": total,
            "successful": successful,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "top_intents": sorted(intent_counts.items(), key=lambda x: x[1], reverse=True)[:5],
            "top_providers": sorted(provider_counts.items(), key=lambda x: x[1], reverse=True)[:5],
        }
