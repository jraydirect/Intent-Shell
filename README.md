# Intent Shell v0.1 (Stateful Intelligence)

Advanced provider-based semantic command shell with fuzzy matching, entity extraction, ambiguity resolution, and ML-ready transaction logging.

## Architecture Highlights

```
┌─────────────────────────────────────────────────┐
│    Ambiguity Resolver (0.6-0.8 → Suggestions)   │
│    Entity Extractor (%TEMP%, clipboard, files)  │
│    Transaction Logger (~/.intent/history.jsonl) │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│           Async REPL Loop                       │
│    Global Context (Clipboard Tracking)          │
└────┬───────────────────────────┬────────────────┘
     │                           │
┌────▼──────────┐       ┌────────▼────────┐
│ Semantic      │       │  Execution      │
│ Parser        │──────▶│  Planner        │
│ (<50ms)       │       │  (Strategy)     │
└───────────────┘       └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │  Provider       │
                        │  Registry       │
                        └────────┬────────┘
                                 │
    ┌────────────────────────────┼────────────────────────────┐
    │                            │                            │
┌───▼──────────┐  ┌──────────────▼──────────┐  ┌─────────────▼─────────┐
│  FileSystem  │  │  WatchProvider          │  │  SystemProvider       │
│  Provider    │  │  (watchdog monitoring)  │  │  (Process mgmt/Admin) │
└──────────────┘  └─────────────────────────┘  └───────────────────────┘
```

## Advanced Features (v0.1)

### 1. Ambiguity Resolver
Commands with 0.6-0.8 confidence show "Did you mean...?" suggestions:

```
intent> opn desktp
Did you mean...?

  1. open desktop (0.75 confidence)
     → open_desktop via filesystem
  2. open downloads (0.62 confidence)
     → open_downloads via filesystem

Please rephrase your command to be more specific.
```

### 2. Entity Extraction

**Environment Variables**:
```bash
intent> open %TEMP%
# Automatically expands to C:\Users\...\AppData\Local\Temp
```

**Clipboard Context**:
```bash
# Copy a path in Windows Explorer (Ctrl+C)
intent> open clipboard
# Opens the copied path
```

**File Detection**:
```bash
intent> watch downloads for report.pdf
# Extracts "report.pdf" as entity
```

### 3. Watch Provider (Active Observer)

Monitor folders for file changes:

```bash
intent> watch downloads for pdf
# Sends Windows notification when new PDF appears

intent> list watches
# Shows active monitors

intent> stop watching
# Stops all watches
```

### 4. System Provider (Process Management)

**List Processes**:
```bash
intent> list processes
Top 10 Processes by Memory:
  1. chrome.exe - 512.3 MB (PID: 1234)
  2. code.exe - 387.1 MB (PID: 5678)
  ...
```

**Kill Processes** (with safety):
```bash
intent> kill notepad
Terminated 2 instance(s) of 'notepad.exe' (PIDs: [1234, 5678])

intent> most memory
Top 5 memory consumers:
  1. chrome.exe - 512.3 MB (PID: 1234)
...
To kill 'chrome.exe', run: kill process 1234
```

**Admin Detection**:
```bash
intent> check admin
✗ Not running as Administrator

To run as admin: Right-click terminal → Run as Administrator
```

### 5. Native Notifications

Long-running tasks trigger Windows Toast notifications:

```bash
intent> watch downloads for pdf
# When PDF appears: Windows notification pops up
```

Supports: `plyer`, `win10toast`, `windows-toasts`

### 6. Transaction Logging

Every command logged to `~/.intent/history.jsonl` for ML training:

```json
{
  "timestamp": "2026-01-16T10:30:45.123456",
  "user_input": "open desktop",
  "intent_name": "open_desktop",
  "provider_name": "filesystem",
  "confidence": 0.95,
  "success": true,
  "entities": [],
  "metadata": {}
}
```

### 7. System Manifest

Generate command documentation:

```bash
intent> manifest
Intent Shell Manifest:
==================================================
Version: 0.1.0
Total Commands: 25
Providers: 5

FILESYSTEM
Description: Filesystem navigation and directory access
Capabilities: READ_ONLY, ASYNC
Commands: 6
  🔒 open desktop → open_desktop
  🔒 open downloads → open_downloads
  ...
```

### 8. History Replay

```bash
intent> history
Command History (last 20):
==================================================
  1. ✓ [2026-01-16 10:30:45] open desktop (0.95)
  2. ✓ [2026-01-16 10:31:12] system info (0.88)
  3. ✗ [2026-01-16 10:32:01] invalid command (0.00)

Use !N to replay a command (e.g., !5)

intent> !1
Replaying: open desktop
Opening Desktop: C:\Users\...\Desktop
```

## Installation

```bash
# Basic installation
pip install -e .

# Full installation (all features)
pip install -e ".[full]"

# Development
pip install -e ".[dev]"
```

## Usage

### Interactive Mode

```bash
intent
```

### Debug Mode (shows entity extraction)

```bash
intent --debug
[DEBUG] Intent: open_desktop
[DEBUG] Provider: filesystem
[DEBUG] Confidence: 0.95
[DEBUG] Entities: [('special_path', 'C:\Users\...\Desktop')]
```

### Single Command

```bash
intent -c "open desktop"
intent -c "watch downloads for pdf"
```

## Available Commands

### FileSystem Provider
- `open desktop` - Desktop folder
- `open downloads` - Downloads folder
- `open documents` - Documents folder
- `open recycle bin` - Recycle Bin
- `open explorer` - File Explorer
- `open home` - Home directory
- `open %TEMP%` - Environment variable expansion

### App Provider
- `open notepad` - Notepad
- `open calculator` - Calculator
- `open settings` - Windows Settings
- `open task manager` - Task Manager
- `open control panel` - Control Panel
- `open startup folder` - Startup folder

### SystemMonitor Provider
- `system info` - System information
- `get hostname` - Computer name
- `get username` - Current user
- `disk space` - Disk usage (requires psutil)

### Watch Provider (requires watchdog)
- `watch downloads` - Monitor Downloads folder
- `watch downloads for pdf` - Monitor for PDFs
- `list watches` - Show active watches
- `stop watching` - Stop all watches

### System Provider (requires psutil)
- `list processes` - Top 10 by memory
- `kill process 1234` - Kill by PID
- `kill notepad` - Kill by name
- `most memory` - Show top memory consumer
- `check admin` - Admin privilege status

### Special Commands
- `help` - Show help
- `stats` - Session statistics
- `manifest` - System manifest
- `history` - Command history
- `!N` - Replay command N
- `exit` - Exit shell

## Performance

- **Parser**: <50ms matching (optimized fast path)
- **Entity Extraction**: <10ms
- **Registry Lookup**: O(1)
- **Ambiguity Check**: Automatic (0.6-0.8 range)

## Dependencies

### Core (No Dependencies)
Basic functionality works out of the box.

### Optional (Full Install)
- `psutil` - Process management, disk space
- `pyperclip` - Clipboard integration
- `watchdog` - Filesystem monitoring
- `plyer` or `win10toast` - Native notifications
- `rich` - Enhanced UI (future)

**Dependency Isolation**: Shell boots even if libraries missing (graceful degradation).

## File Locations

```
~/.intent/
├── logs/
│   └── shell.log          # Structured logs
└── history.jsonl          # Transaction log (ML training)
```

## Engineering Standards

### Zero Latency Parser
- Optimized token matching
- Fast path for exact matches
- Sub-50ms guarantee

### Admin Elevation Handling

```python
try:
    # Protected operation
    kill_process(pid)
except PermissionError:
    print("This requires Admin privileges. Run intent as Administrator?")
```

### Transaction Logging

Every intent-action pair logged for:
- ML fine-tuning
- Usage analytics
- Debugging
- Command replay

### Safety Checks

```python
critical_processes = ['csrss.exe', 'winlogon.exe', 'services.exe']
if process_name in critical_processes:
    raise SafetyError("Cannot kill critical system process")
```

## Creating Custom Providers

```python
from intent_shell.providers.base import BaseProvider, IntentTrigger, ExecutionResult

class MyProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "my_provider"
    
    def _initialize_triggers(self) -> None:
        self.triggers = [
            IntentTrigger("my command", "do_thing", 1.0)
        ]
    
    async def execute(self, intent_name, context=None):
        # Access entities
        entities = context.get("entities", [])
        
        # Access clipboard
        clipboard = context.get("clipboard")
        
        return ExecutionResult(True, "Done!")
```

## Testing

```bash
pytest tests/ -v
pytest tests/test_parser.py -v  # Parser tests
pytest tests/test_ambiguity.py -v  # Ambiguity resolution
```

## Advanced Examples

### Environment Variable Expansion

```bash
intent> open %APPDATA%\Microsoft
# Expands to C:\Users\...\AppData\Roaming\Microsoft

intent> open %USERPROFILE%\Desktop
# Expands to C:\Users\...\Desktop
```

### Clipboard Pipeline

```bash
# In Windows Explorer, copy a path (Ctrl+C)
# Then:
intent> open clipboard
# Opens the copied path

intent> system info to clipboard
# Copies system info to clipboard
```

### Watch + Notify

```bash
intent> watch downloads for report.pdf
Watching Downloads folder for .pdf files.

# When report.pdf appears:
# → Windows notification: "New .pdf file detected: report.pdf"
```

### Process Management

```bash
intent> list processes
# Shows top 10

intent> most memory
# Shows top 5 with safety check

intent> kill notepad
# Kills all notepad instances

intent> kill process 1234
# Kills specific PID
```

## Security & Safety

- **Read-Only by Default**: Most providers are READ_ONLY
- **Critical Process Protection**: Cannot kill system processes
- **Admin Detection**: Warns if privileges needed
- **Safety Confirmations**: Destructive actions require explicit PID

## License

MIT

## Contributing

1. Create provider in `intent_shell/providers/`
2. Implement `BaseProvider` ABC
3. Register in `ProviderRegistry.auto_discover()`
4. Add tests
5. Update manifest

## Future Roadmap

- [ ] Trie-based parser (O(m) instead of O(n))
- [ ] Plugin system for external providers
- [ ] Rich TUI with autocomplete
- [ ] Cross-platform support (Linux, macOS)
- [ ] ML-powered intent prediction using history.jsonl
- [ ] Remote providers via RPC
- [ ] Voice command integration
- [ ] Multi-language support
