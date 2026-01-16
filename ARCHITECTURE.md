# Intent Shell - Architecture Documentation

## Overview

Intent Shell v0.1 (Kernel) implements a **provider-based architecture** for semantic command processing. The system follows SOLID principles and uses modern Python patterns (async/await, ABC, dependency injection).

## Design Patterns

### 1. Provider Pattern (Strategy + Registry)

**Purpose**: Enable pluggable domain handlers without modifying core logic.

```
BaseProvider (ABC)
├── FileSystemProvider
├── AppProvider
└── SystemMonitorProvider
```

**Key Components**:
- `BaseProvider`: Abstract base class defining provider contract
- `ProviderRegistry`: Central registry for provider discovery and lookup
- `IntentTrigger`: Declarative intent-to-pattern mapping

**Benefits**:
- Loose coupling between shell and domain logic
- Easy extensibility (just add new providers)
- Testability (mock providers)

### 2. Fuzzy Semantic Matching

**Algorithm**: Multi-stage scoring system

```python
score = (token_overlap * 0.6) + (sequence_similarity * 0.4)
```

**Stages**:
1. Exact substring match → 1.0
2. Token-based overlap → 0.0-1.0
3. Sequence similarity (SequenceMatcher) → 0.0-1.0

**Threshold**: 0.60 minimum, 0.80 recommended for high confidence

### 3. Async Execution Model

**Problem**: Windows shell operations (`os.startfile`, `subprocess`) can block.

**Solution**: Async/await with non-blocking REPL

```python
async def execute(intent_name, context) -> ExecutionResult:
    # Non-blocking execution
    os.startfile(path)
    return ExecutionResult(...)
```

**Benefits**:
- Responsive REPL even during long operations
- Future-proof for network operations
- Natural composition of async providers

### 4. Stateful Context

**SessionState** tracks:
- Command history with timestamps
- Last accessed directory
- Last queried process
- Arbitrary context data

**Use Cases**:
- "Go back" navigation
- Context-aware suggestions
- Session analytics

## Component Architecture

### Parser Layer

```
User Input → SemanticParser → IntentMatch
                ↓
          ProviderRegistry
                ↓
          [Provider Triggers]
```

**Responsibilities**:
- Normalize input
- Score against all triggers
- Return best match with confidence

### Planner Layer

```
IntentMatch → ExecutionPlanner → Provider.execute()
                                      ↓
                                ExecutionResult
```

**Responsibilities**:
- Resolve provider from match
- Inject execution context
- Attach metadata

### Provider Layer

```
BaseProvider
├── name: str (unique identifier)
├── description: str
├── capabilities: List[ProviderCapability]
├── triggers: List[IntentTrigger]
└── execute(intent_name, context) → ExecutionResult
```

**Contract**:
- Must implement `execute()` as async
- Must register triggers in `_initialize_triggers()`
- Must return `ExecutionResult`

## Data Flow

### Interactive Command Flow

```
1. User types command
2. SessionState.add_command()
3. SemanticParser.parse() → IntentMatch
4. ExecutionPlanner.execute_intent() → ExecutionResult
5. Display result + update context
6. Optional: pipe to clipboard
```

### Single Command Flow

```
1. CLI receives -c flag
2. Setup registry + parser
3. Parse → Plan → Execute
4. Exit with code (0=success, 1=failure)
```

## Extensibility Points

### Adding a New Provider

1. Create `intent_shell/providers/my_provider.py`:

```python
from intent_shell.providers.base import BaseProvider, IntentTrigger, ExecutionResult

class MyProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "my_provider"
    
    @property
    def description(self) -> str:
        return "My domain"
    
    def _initialize_triggers(self) -> None:
        self.triggers = [
            IntentTrigger("my command", "do_thing", 1.0)
        ]
    
    async def execute(self, intent_name, context=None):
        # Implementation
        return ExecutionResult(True, "Done")
```

2. Register in `registry.py`:

```python
def auto_discover(self):
    providers = [
        # ... existing
        MyProvider(),
    ]
```

3. Done! No changes to core code needed.

### Adding New Features to Existing Providers

Providers are isolated. Modify the specific provider file:

```python
def _initialize_triggers(self) -> None:
    self.triggers.append(
        IntentTrigger("new command", "new_intent", 1.0)
    )

async def execute(self, intent_name, context):
    if intent_name == "new_intent":
        return await self._new_handler()
```

## Performance Considerations

### Parser Complexity
- **Trigger Lookup**: O(n) where n = total triggers
- **Optimization**: Trigger cache rebuilt on registry changes only
- **Future**: Implement trie for O(m) lookup (m = input length)

### Registry Lookup
- **Provider Lookup**: O(1) via dict
- **Trigger Index**: O(1) for exact matches

### Memory Usage
- **Trigger Cache**: ~100 bytes per trigger
- **Session History**: ~200 bytes per command
- **Typical Memory**: < 10MB for extended session

## Security Model

### Read-Only by Default
All providers use `ProviderCapability.READ_ONLY` flag.

### No Destructive Actions
- No file deletion
- No process termination (except via Task Manager UI)
- No system modifications

### Input Sanitization
- All inputs normalized (lowercase, strip)
- No shell injection (uses `os.startfile`, not `os.system`)

## Testing Strategy

### Unit Tests
- `test_parser.py`: Fuzzy matching logic
- `test_providers.py`: Provider contract compliance
- `test_session.py`: State management

### Integration Tests
- End-to-end command flow
- Provider registry auto-discovery

### Run Tests
```bash
pytest tests/ -v
pytest tests/ --asyncio-mode=auto
```

## Logging Architecture

### Structured Logging

```
~/.intent/logs/shell.log
```

**Format**: `timestamp - logger - level - message`

**Levels**:
- DEBUG: Intent scoring, trigger matching
- INFO: Command execution, provider dispatch
- WARNING: Missing providers, failed matches
- ERROR: Execution failures

### Log Rotation
- Max size: 10MB per file
- Backups: 5 files
- Total: 50MB max

## Future Enhancements

### Planned Features
1. **Trie-based matching** for O(m) parser performance
2. **Plugin system** for external provider loading
3. **Rich TUI** with autocomplete and syntax highlighting
4. **Cross-platform** support (Linux, macOS)
5. **Remote providers** via RPC/HTTP

### Architectural Improvements
1. **Provider versioning** for backward compatibility
2. **Event bus** for inter-provider communication
3. **Caching layer** for expensive operations
4. **Config files** for user preferences

## Dependencies

### Core (Zero Dependencies)
All core functionality works without external packages.

### Optional Dependencies
- `psutil`: System monitoring (disk space, processes)
- `pyperclip`: Clipboard integration
- `rich`: Enhanced terminal UI

**Philosophy**: Gracefully degrade if optional deps missing.

## SOLID Principles Applied

### Single Responsibility
- Each provider handles one domain
- Parser only does intent extraction
- Planner only does dispatch

### Open/Closed
- Add new providers without modifying registry
- Extend capabilities via new IntentTrigger patterns

### Liskov Substitution
- All providers implement BaseProvider contract
- Interchangeable via registry

### Interface Segregation
- BaseProvider has minimal required methods
- Capabilities flag optional features

### Dependency Inversion
- Core depends on BaseProvider abstraction
- Concrete providers injected via registry

## Conclusion

Intent Shell's architecture prioritizes:
1. **Extensibility**: Easy to add providers
2. **Performance**: O(1) lookups, async execution
3. **Maintainability**: Clear separation of concerns
4. **Testability**: Mockable providers, isolated components
5. **User Experience**: Fast fuzzy matching, helpful debug info

The provider pattern enables scaling to hundreds of intents without core code changes.
