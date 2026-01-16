# Clipboard History Manager - Feature Documentation

## Overview

The Clipboard History Manager is a powerful new feature for IntelliShell that provides persistent clipboard tracking, search, and restore capabilities. It automatically monitors clipboard changes in the background and stores them for later retrieval.

## Features

### ✅ Core Functionality
- **Persistent Storage**: All clipboard entries saved to `~/.intellishell/clipboard_history.jsonl`
- **Background Monitoring**: Optional automatic clipboard tracking via background thread
- **Search**: Full-text search across clipboard history
- **Restore**: Restore any previous clipboard entry with a single command
- **Deduplication**: Automatically skips consecutive duplicate entries
- **Size Limits**: Configurable limits (default: 100 entries, 10MB max)
- **Thread-Safe**: All operations are thread-safe for concurrent access

### 🎯 Commands

| Command | Description | Example |
|---------|-------------|---------|
| `clipboard history` | Show clipboard history (last 20 entries) | `ishell -c "clipboard history"` |
| `clipboard search <query>` | Search clipboard history | `ishell -c "clipboard search password"` |
| `clipboard restore N` | Restore entry N to clipboard | `ishell -c "clipboard restore 5"` |
| `clipboard stats` | Show clipboard statistics | `ishell -c "clipboard stats"` |
| `clipboard start monitoring` | Start background monitoring | `ishell -c "clipboard start monitoring"` |
| `clipboard stop monitoring` | Stop background monitoring | `ishell -c "clipboard stop monitoring"` |
| `clipboard clear` | Clear clipboard history | `ishell -c "clipboard clear"` |

## Architecture

### Components

1. **ClipboardHistoryEntry** (`intellishell/utils/clipboard.py`)
   - Represents a single clipboard entry
   - Stores content, timestamp, content type, and preview
   - Serializable to/from JSON

2. **ClipboardHistory** (`intellishell/utils/clipboard.py`)
   - Core clipboard history manager
   - Handles persistent storage (JSONL format)
   - Background monitoring thread
   - Search and filtering
   - Thread-safe operations

3. **ClipboardProvider** (`intellishell/providers/clipboard_provider.py`)
   - IntelliShell provider for clipboard commands
   - Exposes clipboard functionality via intents
   - Integrates with safety system

### Data Flow

```
User Copies Text
    ↓
System Clipboard
    ↓
Background Monitor Thread (if enabled)
    ↓
ClipboardHistory.add_entry()
    ↓
Deduplication Check
    ↓
Size Limit Check
    ↓
Append to _entries list
    ↓
Save to clipboard_history.jsonl
```

### Storage Format

Clipboard history is stored in JSONL (JSON Lines) format at `~/.intellishell/clipboard_history.jsonl`:

```json
{"content": "Hello World", "timestamp": "2026-01-16T10:00:00", "content_type": "text", "preview": "Hello World"}
{"content": "https://github.com/...", "timestamp": "2026-01-16T10:01:00", "content_type": "text", "preview": "https://github.com/..."}
```

## Usage Examples

### Interactive Mode

```bash
# Start IntelliShell
ishell

# View clipboard history
intellishell> clipboard history

# Search for specific content
intellishell> clipboard search "API key"

# Restore a previous entry
intellishell> clipboard restore 3

# Check statistics
intellishell> clipboard stats
```

### Single Command Mode

```bash
# View history
ishell -c "clipboard history"

# Search
ishell -c "clipboard search password"

# Restore
ishell -c "clipboard restore 5"
```

### Programmatic Usage

```python
from intellishell.utils.clipboard import ClipboardHistory

# Create clipboard history
history = ClipboardHistory(auto_monitor=True)

# Add entry manually
history.add_entry("Some text")

# Search
results = history.search("text")

# Get recent entries
entries = history.get_history(limit=10)

# Restore entry
history.restore_entry(1)  # Restore most recent

# Get statistics
stats = history.get_stats()
print(f"Total entries: {stats['total_entries']}")
```

## Configuration

### Default Settings

```python
DEFAULT_MAX_ENTRIES = 100      # Maximum number of entries to keep
DEFAULT_MAX_SIZE_MB = 10       # Maximum size of history file
MONITOR_INTERVAL = 1.0         # Clipboard check interval (seconds)
```

### Custom Configuration

```python
from intellishell.utils.clipboard import ClipboardHistory
from pathlib import Path

history = ClipboardHistory(
    storage_path=Path("~/my_clipboard.jsonl"),
    max_entries=200,
    max_size_mb=20,
    auto_monitor=True
)
```

## Safety Levels

All clipboard operations are categorized by safety level:

| Intent | Safety Level | Confirmation Required |
|--------|--------------|----------------------|
| `show_clipboard_history` | GREEN | No |
| `search_clipboard` | GREEN | No |
| `restore_clipboard` | GREEN | No |
| `clipboard_stats` | GREEN | No |
| `start_clipboard_monitoring` | YELLOW | Only if last action failed |
| `stop_clipboard_monitoring` | YELLOW | Only if last action failed |
| `clear_clipboard_history` | YELLOW | Only if last action failed |

## Testing

Comprehensive test suite included in `tests/test_clipboard_history.py`:

```bash
# Run all clipboard tests
pytest tests/test_clipboard_history.py -v

# Run specific test
pytest tests/test_clipboard_history.py::test_add_entry -v
```

### Test Coverage

- ✅ Initialization
- ✅ Adding entries
- ✅ Retrieving history
- ✅ Searching
- ✅ Entry indexing
- ✅ Max entries limit
- ✅ Clearing history
- ✅ Persistence (save/load)
- ✅ Statistics
- ✅ Entry serialization
- ✅ Empty content handling
- ✅ Provider integration
- ✅ Search functionality

**All 14 tests passing** ✅

## Performance

- **Add Entry**: O(1) - Constant time append
- **Get History**: O(n) - Linear scan (n = limit)
- **Search**: O(n) - Linear scan through all entries
- **Restore**: O(1) - Direct index access
- **Memory**: ~1KB per entry (typical)
- **Disk I/O**: Append-only writes (fast)

## Dependencies

### Required
- `json` (stdlib)
- `threading` (stdlib)
- `pathlib` (stdlib)

### Optional
- `pyperclip` - For clipboard read/write operations (recommended)

## Limitations

1. **Windows Console Encoding**: Emojis removed from output for Windows console compatibility
2. **Clipboard Access**: Requires `pyperclip` for actual clipboard operations
3. **Memory**: All entries kept in RAM (limited by max_entries)
4. **Search**: Simple substring matching (no fuzzy search yet)
5. **Content Types**: Currently only tracks "text" type

## Future Enhancements

### Planned Features
- [ ] Fuzzy search with similarity scoring
- [ ] Content type detection (URL, path, code, etc.)
- [ ] Clipboard image support
- [ ] Encryption for sensitive data
- [ ] Cloud sync across devices
- [ ] Smart categorization (auto-tagging)
- [ ] Clipboard templates/snippets
- [ ] Integration with password managers

### Possible Improvements
- [ ] Compression for large entries
- [ ] Indexed search for faster queries
- [ ] Export to CSV/JSON
- [ ] Import from other clipboard managers
- [ ] Keyboard shortcuts for quick access
- [ ] Visual preview for images/files

## Troubleshooting

### Issue: Clipboard monitoring not working

**Solution**: Ensure pyperclip is installed and clipboard access is not blocked:
```bash
pip install pyperclip
```

### Issue: "UnicodeEncodeError" on Windows

**Solution**: This has been fixed by removing emojis from output. Update to latest version.

### Issue: History file too large

**Solution**: Reduce max_entries or clear old history:
```bash
ishell -c "clipboard clear"
```

### Issue: Entries not persisting

**Solution**: Check file permissions on `~/.intellishell/clipboard_history.jsonl`:
```bash
ls -la ~/.intellishell/
```

## Security Considerations

1. **Sensitive Data**: Clipboard history may contain passwords, API keys, etc.
   - Consider encrypting the history file
   - Be cautious when sharing logs or backups

2. **File Permissions**: History file should be readable only by owner:
   ```bash
   chmod 600 ~/.intellishell/clipboard_history.jsonl
   ```

3. **Clear Regularly**: For security-sensitive environments, clear history periodically:
   ```bash
   ishell -c "clipboard clear"
   ```

## Contributing

To extend the clipboard functionality:

1. Add new intents to `ClipboardProvider`
2. Implement handler methods
3. Add safety levels to `safety.py`
4. Write tests in `test_clipboard_history.py`
5. Update documentation

## License

MIT License - Same as IntelliShell

## Credits

- Implemented as part of IntelliShell v0.1.0
- Feature request: Clipboard History Manager from engineering audit
- Inspired by clipboard managers like Ditto, CopyQ, and Flycut

---

**Version**: 1.0.0  
**Date**: 2026-01-16  
**Status**: ✅ Production Ready
