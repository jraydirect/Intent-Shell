# Intent Shell - AI & Semantic Memory Guide

## Overview

Intent Shell v0.1 now features **Semantic Memory** with vector storage and **Agentic Reasoning** via local LLM integration.

## Architecture

```
User Input → Hybrid Parser (Rule+AI)
                ↓
          [Rule-Based]
        Confidence ≥ 0.8? → Execute
        0.6 ≤ conf < 0.8? → Suggest
        conf < 0.5? → Try LLM
                ↓
          [LLM Fallback]
        Ollama API → JSON Intent
                ↓
          Validate (Pydantic)
                ↓
          Execute → Store in Vector DB
```

## Features

### 1. Semantic Memory (ChromaDB)

**Auto-Indexing**: Every successful command stored as vector embedding in `~/.intent/vector_store`.

**Commands**:
```bash
intent> what folder did I open yesterday?
# Performs semantic search over command history

intent> what did I do with desktop?
# Finds desktop-related commands

intent> recent memories
# Shows last 10 indexed commands
```

### 2. LLM Integration (Ollama)

**Setup Ollama**:
```bash
# Install Ollama: https://ollama.ai
ollama pull llama3:8b
ollama serve
```

**Usage**:
```bash
intent> show me my computer name
# Rule-based score: 0.45 (low)
# LLM interprets → {"intent": "get_hostname", "provider": "system_monitor"}
```

### 3. Self-Correction

**Typo Correction**:
```bash
intent> open downlods
ℹ Found typo: 'downlods' → 'downloads'
Opening Downloads: C:\Users\...\Downloads
```

### 4. Context Manager

**Short-Term Memory** (last 5 interactions):
```bash
intent> open desktop
intent> what did I just open?
# LLM uses context: "User just opened desktop"
```

## Installation

```bash
# Full installation
pip install -e ".[full]"

# AI only
pip install -e ".[ai]"

# Memory only
pip install -e ".[memory]"
```

## CLI Options

```bash
# Full features (default)
intent

# Disable AI
intent --no-ai

# Disable semantic memory
intent --no-memory

# Debug mode
intent --debug
```

## Requirements

### Semantic Memory
- **chromadb** >= 0.4.0
- Disk space: ~100MB for vector store

### AI Bridge
- **pydantic** >= 2.0.0
- **requests** >= 2.28.0
- **Ollama** running on localhost:11434

## Performance

- **Background Indexing**: Non-blocking vector writes (separate thread)
- **Hardware Awareness**: Graceful degradation if Ollama/ChromaDB unavailable
- **LLM Fallback**: Only triggers for confidence < 0.5

## Examples

### Semantic Search
```bash
intent> what was that folder I opened yesterday?

Found 3 similar commands:

1. [2026-01-16 10:30:45] open_desktop
   open desktop Opening Desktop: C:\Users\...\Desktop
   Similarity: 0.87

2. [2026-01-16 09:15:22] open_downloads
   open downloads Opening Downloads
   Similarity: 0.75
```

### LLM Reasoning
```bash
intent> clean up my desktop mess
[DEBUG] Rule-based score: 0.42 (low)
[DEBUG] Trying LLM fallback...
[LLM] Intent: list_directory (confidence: 0.85)
[LLM] Reasoning: User wants to see desktop contents

# Executes: list_directory on desktop
```

### Context-Aware
```bash
intent> open desktop
Opening Desktop...

intent> what's in it?
# LLM uses context: "User just opened desktop, wants to list contents"
# Maps to: list_directory intent
```

## Troubleshooting

### ChromaDB Not Available
```
Status: ✗ Semantic Memory (install chromadb)
```
**Fix**: `pip install chromadb`

### Ollama Not Running
```
Status: ✗ AI Bridge (Ollama not running)
```
**Fix**: `ollama serve` in separate terminal

### LLM Timeout
```python
# In ai_bridge.py, increase timeout:
OllamaClient(timeout=60)  # Default: 30
```

## Data Storage

```
~/.intent/
├── vector_store/        # ChromaDB persistent storage
│   ├── chroma.sqlite3   # SQLite index
│   └── embeddings/      # Vector embeddings
├── logs/
│   └── shell.log        # Structured logs
└── history.jsonl        # Transaction log (ML training)
```

## Advanced Usage

### Custom Ollama Model
```bash
ollama pull phi3:mini
```

Then in code:
```python
ai_bridge = AIBridge(ollama_model="phi3:mini")
```

### Clear Vector Store
```python
from intent_shell.memory import SemanticMemory
memory = SemanticMemory()
memory.vector_store.clear()
```

## License

MIT
