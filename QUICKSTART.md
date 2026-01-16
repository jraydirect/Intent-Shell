# Intent Shell - Quick Start Guide

## Installation

```bash
# Navigate to project
cd intent

# Install in development mode
pip install -e .

# Or install with all features
pip install -e ".[full]"
```

## Basic Commands

### Open Folders
```bash
intent> open desktop
intent> open downloads
intent> open documents
```

### List Files
```bash
intent> list downloads
intent> recent files in downloads
intent> files in desktop
intent> show me files in downloads
```

### Applications
```bash
intent> open notepad
intent> open calculator
intent> open settings
intent> open task manager
```

### System Info
```bash
intent> system info
intent> get hostname
intent> disk space
```

### Process Management
```bash
intent> list processes
intent> kill notepad
intent> check admin
```

### History & Memory
```bash
intent> history                  # Show command history
intent> !5                        # Replay command 5
intent> stats                     # Session statistics
intent> what did I open yesterday # Semantic search (requires chromadb)
```

## Optional: AI Features

### Setup Ollama (Optional)

1. **Download Ollama**: https://ollama.ai
2. **Install a model**:
```bash
# Recommended: Small, fast model
ollama pull phi3:mini

# Or: Larger, more capable model
ollama pull llama3:8b
```

3. **Start Ollama**:
```bash
ollama serve
```

4. **Restart Intent Shell**:
```bash
intent
```

Now the shell will use AI for ambiguous commands!

### Using AI Features

Once Ollama is running:
```bash
# Natural language queries (AI interprets)
intent> show me my computer name
intent> what processes are using memory
intent> help me find that folder
```

## Optional: Semantic Memory

Install ChromaDB for semantic search:
```bash
pip install chromadb
```

Then you can use:
```bash
intent> what folder did I open yesterday?
intent> what did I do with downloads?
intent> recent memories
```

## Disable Features

Don't want AI or memory? Disable them:
```bash
intent --no-ai          # Disable LLM fallback
intent --no-memory      # Disable vector storage
intent --no-ai --no-memory  # Pure rule-based
```

## Troubleshooting

### Command Not Recognized?

Try:
- More specific phrasing: `list downloads` instead of `show downloads`
- Use `help` to see available commands
- Check with `--debug` to see confidence scores

### Ollama Timeout?

The AI features are **optional**. The shell works great without them!

To disable AI fallback:
```bash
intent --no-ai
```

### Model Not Found?

```bash
# Check available models
ollama list

# Pull a model
ollama pull phi3:mini
```

## Common Patterns

### File Management
```
list downloads → Show recent files
open downloads → Open folder in Explorer
```

### Quick Navigation
```
open desktop
open documents  
open downloads
```

### Process Control
```
list processes → Top 10 by memory
kill notepad → Terminate all instances
```

### Search History
```
history → Last 20 commands
!5 → Replay command 5
stats → Session statistics
```

## Tips

1. **Tab complete** - Type partial commands (coming soon)
2. **Pipe to clipboard** - Add `to clipboard` to any command
3. **Use debug mode** - `intent --debug` shows confidence scores
4. **History replay** - Use `!N` to quickly repeat commands

## Getting Help

```bash
intent> help          # List all commands
intent> manifest      # Show detailed command list
intent> stats         # Check feature status
```

## Next Steps

- Explore `help` to see all providers
- Try `manifest` for complete command reference  
- Check `README_AI.md` for advanced AI features
- See `ARCHITECTURE.md` for technical details

Enjoy Intent Shell! 🚀
