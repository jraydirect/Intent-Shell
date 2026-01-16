# Changelog

## v0.1.0 - Stateful Intelligence (2026-01-16)

### Advanced Features

#### Ambiguity Resolver
- Commands with 0.6-0.8 confidence show "Did you mean...?" suggestions
- Prevents accidental execution of uncertain commands
- Guides user to rephrase for better matching

#### Entity Extraction
- **Environment Variables**: Automatic expansion of `%TEMP%`, `%APPDATA%`, `%USERPROFILE%`
- **Clipboard Context**: Reference clipboard content with "clipboard" or "that"
- **File Detection**: Extracts file paths and extensions from natural language
- **Global Context**: Tracks clipboard changes for contextual commands

#### Watch Provider (Active Observer)
- Monitor folders for file changes using watchdog
- Filter by file type (e.g., "watch downloads for pdf")
- Windows native notifications on file detection
- List and stop active watches

#### System Provider (Process Management)
- List top processes by memory usage
- Kill processes by PID or name
- Safety checks prevent killing critical system processes
- Admin privilege detection and helpful elevation messages
- "Most memory" shows top consumer with safety confirmation

#### Native Notifications
- Windows Toast notifications for long-running tasks
- Support for plyer, win10toast, and windows-toasts
- Graceful fallback if no notification library available

#### Transaction Logging
- Every command logged to `~/.intent/history.jsonl`
- ML-ready format with timestamps, confidence scores, entities
- History command shows last 20 commands
- Replay history with `!N` syntax (e.g., `!5`)
- Search and statistics from transaction log

#### System Manifest
- Dynamic registry view of all commands
- Shows safety levels (READ_ONLY vs WRITE)
- Lists aliases and patterns per command
- Exportable manifest.json format

### Performance
- Parser optimized to <50ms (zero latency goal)
- Fast path for exact matches
- Token-based pre-filtering before sequence matching
- Entity extraction <10ms

### Engineering
- **Dependency Isolation**: Shell boots even if optional libraries missing
- **Admin-Aware Error Handling**: Catches PermissionError with helpful messages
- **Structured Logging**: All operations logged to `~/.intent/logs/shell.log`
- **Type Hints**: Strict typing throughout
- **Async/Await**: Non-blocking execution model

### Commands Added
- `watch downloads [for TYPE]` - Monitor folder
- `stop watching` - Stop all watches
- `list watches` - Show active watches
- `list processes` - Top processes by memory
- `kill process PID` - Kill by PID
- `kill APPNAME` - Kill by name
- `most memory` - Show top memory consumer
- `check admin` - Check privilege level
- `manifest` - Show system manifest
- `history` - Show command history
- `!N` - Replay history command

### Files Added
- `intent_shell/providers/watch_provider.py` - Filesystem monitoring
- `intent_shell/providers/system_provider.py` - Process management
- `intent_shell/utils/notifications.py` - Native notifications
- `intent_shell/utils/transaction_log.py` - JSONL transaction logger
- `intent_shell/utils/clipboard.py` - Enhanced with GlobalContext
- `CHANGELOG.md` - This file

### Files Modified
- `intent_shell/parser.py` - Added entity extraction, ambiguity resolution, env var expansion
- `intent_shell/main.py` - Added history replay, manifest, transaction logging
- `intent_shell/providers/registry.py` - Added manifest generation
- `pyproject.toml` - Added watchdog, plyer, win10toast dependencies
- `README.md` - Comprehensive documentation update

### Dependencies (Optional)
- `watchdog>=3.0.0` - Filesystem monitoring
- `plyer>=2.1.0` - Cross-platform notifications
- `win10toast>=0.9` - Windows-specific notifications

## v0.1.0-beta - Kernel Refactor (2026-01-16)

### Architecture
- Provider-based architecture with BaseProvider ABC
- ProviderRegistry for auto-discovery
- Async execution model with asyncio
- Fuzzy semantic matching with confidence scoring

### Core Providers
- FileSystemProvider (desktop, downloads, documents, etc.)
- AppProvider (notepad, calculator, settings, etc.)
- SystemMonitorProvider (system info, disk space, etc.)

### Features
- Fuzzy matching with 80% confidence threshold
- Clipboard piping ("to clipboard")
- Session state tracking
- Structured logging to `~/.intent/logs/shell.log`
- Debug mode with intent scoring telemetry
- Deep links (shell:RecycleBinFolder, shell:Startup, etc.)

### Performance
- O(n) parser complexity where n = triggers
- O(1) provider lookup
- <10MB memory footprint
- Non-blocking async operations

## v0.0.1 - Initial Release

### Basic Features
- Simple REPL loop
- Static command mapping
- Basic Windows operations (open desktop, downloads, etc.)
- Application launching (notepad, calculator)
