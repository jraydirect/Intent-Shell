"""Watch provider for filesystem monitoring."""

import os
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from intellishell.providers.base import (
    BaseProvider,
    IntentTrigger,
    ExecutionResult,
    ProviderCapability
)
import logging

logger = logging.getLogger(__name__)


class WatchProvider(BaseProvider):
    """Provider for filesystem watching with watchdog integration."""
    
    def __init__(self):
        super().__init__()
        self._active_watches: Dict[str, Any] = {}
        self._watch_tasks: Dict[str, asyncio.Task] = {}
    
    @property
    def name(self) -> str:
        return "watch"
    
    @property
    def description(self) -> str:
        return "Filesystem monitoring and alerts"
    
    def _initialize_triggers(self) -> None:
        """Initialize watch-related triggers."""
        self.capabilities = [
            ProviderCapability.READ_ONLY,
            ProviderCapability.ASYNC,
            ProviderCapability.STATEFUL,
        ]
        
        self.triggers = [
            IntentTrigger(
                pattern="watch downloads",
                intent_name="watch_downloads",
                weight=1.0,
                aliases=["monitor downloads", "watch my downloads"]
            ),
            IntentTrigger(
                pattern="watch for pdf",
                intent_name="watch_for_file_type",
                weight=1.0,
                aliases=["watch for pdfs", "monitor for pdf"]
            ),
            IntentTrigger(
                pattern="stop watching",
                intent_name="stop_watch",
                weight=1.0,
                aliases=["stop watch", "stop monitoring"]
            ),
            IntentTrigger(
                pattern="list watches",
                intent_name="list_watches",
                weight=1.0,
                aliases=["show watches", "active watches"]
            ),
        ]
    
    async def execute(
        self,
        intent_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """Execute watch operation."""
        try:
            if intent_name == "watch_downloads":
                return await self._watch_downloads(context)
            elif intent_name == "watch_for_file_type":
                return await self._watch_for_file_type(context)
            elif intent_name == "stop_watch":
                return await self._stop_watch(context)
            elif intent_name == "list_watches":
                return await self._list_watches()
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
    
    async def _watch_downloads(
        self,
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """Start watching downloads folder."""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
        except ImportError:
            return ExecutionResult(
                success=False,
                message="watchdog not installed. Install with: pip install watchdog"
            )
        
        downloads_path = Path.home() / "Downloads"
        
        if not downloads_path.exists():
            return ExecutionResult(
                success=False,
                message=f"Downloads folder not found: {downloads_path}"
            )
        
        # Extract file type filter from entities if present
        file_extension = None
        if context and "entities" in context:
            for entity in context["entities"]:
                if entity.type == "file":
                    file_extension = Path(entity.value).suffix
                    break
        
        # Create event handler
        class DownloadsHandler(FileSystemEventHandler):
            def __init__(self, extension_filter=None, notification_callback=None):
                self.extension_filter = extension_filter
                self.callback = notification_callback
            
            def on_created(self, event):
                if not event.is_directory:
                    file_path = Path(event.src_path)
                    if self.extension_filter:
                        if file_path.suffix.lower() == self.extension_filter.lower():
                            msg = f"New {self.extension_filter} file detected: {file_path.name}"
                            logger.info(msg)
                            if self.callback:
                                self.callback(msg)
                    else:
                        msg = f"New file detected: {file_path.name}"
                        logger.info(msg)
                        if self.callback:
                            self.callback(msg)
        
        # Notification callback
        def notify(message: str):
            from intellishell.utils.notifications import send_notification
            send_notification("IntelliShell", message)
        
        handler = DownloadsHandler(file_extension, notify)
        observer = Observer()
        observer.schedule(handler, str(downloads_path), recursive=False)
        observer.start()
        
        # Store observer
        watch_id = f"downloads_{file_extension or 'all'}"
        self._active_watches[watch_id] = observer
        
        filter_msg = f" for {file_extension} files" if file_extension else ""
        return ExecutionResult(
            success=True,
            message=f"Watching Downloads folder{filter_msg}. Type 'stop watching' to stop.",
            data={"watch_id": watch_id, "path": str(downloads_path)}
        )
    
    async def _watch_for_file_type(
        self,
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """Watch for specific file type."""
        # Delegate to _watch_downloads with entity context
        return await self._watch_downloads(context)
    
    async def _stop_watch(
        self,
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """Stop active watches."""
        if not self._active_watches:
            return ExecutionResult(
                success=False,
                message="No active watches to stop"
            )
        
        # Stop all observers
        stopped = []
        for watch_id, observer in self._active_watches.items():
            try:
                observer.stop()
                observer.join(timeout=2)
                stopped.append(watch_id)
            except Exception as e:
                logger.error(f"Failed to stop watch {watch_id}: {e}")
        
        # Clear active watches
        self._active_watches.clear()
        
        return ExecutionResult(
            success=True,
            message=f"Stopped {len(stopped)} watch(es): {', '.join(stopped)}"
        )
    
    async def _list_watches(self) -> ExecutionResult:
        """List active watches."""
        if not self._active_watches:
            return ExecutionResult(
                success=True,
                message="No active watches"
            )
        
        watches_info = []
        for watch_id, observer in self._active_watches.items():
            status = "running" if observer.is_alive() else "stopped"
            watches_info.append(f"  • {watch_id} ({status})")
        
        message = "Active Watches:\n" + "\n".join(watches_info)
        
        return ExecutionResult(
            success=True,
            message=message,
            data={"watches": list(self._active_watches.keys())}
        )
