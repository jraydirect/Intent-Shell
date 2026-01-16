# Intent Shell - Production Safety Guide

## Self-Healing Loop

### Try-Repair-Retry Flow

```
Stage 1: Attempt Execution
    ↓
  Error?
    ↓
Stage 2: Analyze Error (classify: FileNotFound, Permission, etc.)
    ↓
Stage 3: AI Proposes Fix
    ↓
User Confirms
    ↓
Retry with Fix
```

### Example Session

```bash
intent> open downlods
⚠️  Intent failed: Downloads path not found: C:\Users\...\Downlods
💡 Suggested fix: open downloads
   Reasoning: User likely misspelled 'Downloads'

Proceed with suggested fix? (y/n): y
Opening Downloads: C:\Users\...\Downloads
```

## Safety Levels

### GREEN (Read-Only)
- **No confirmation** needed
- Examples: `list files`, `system info`, `get hostname`
- Safe for automation

### YELLOW (State-Changing)
- **Confirmation required** if last action failed
- Examples: `open notepad`, `watch downloads`
- Moderate risk

### RED (Destructive)
- **Always requires confirmation** + logged
- Examples: `kill process`, `kill notepad`
- High risk, audit trail maintained

### Safety Check Example

```bash
intent> kill notepad

🔴 Safety Check - DESTRUCTIVE
Intent: kill_by_name
Provider: system
Action: kill notepad
⚠️  This action is potentially DESTRUCTIVE

Proceed? (y/n): y
Terminated 2 instance(s) of 'notepad.exe'
```

## Circuit Breaker

### Purpose
Prevents infinite AI repair loops for consistently failing commands.

### Behavior
- Tracks failures per command
- Opens circuit after **3 consecutive failures**
- Provides clear error message when open
- Resets on first success

### Example

```bash
intent> broken command
# Attempt 1 fails
# Attempt 2 fails  
# Attempt 3 fails

⚠️ Circuit breaker open for 'provider:intent'. 
This command has failed 3 times. 
Please check the issue manually.
```

## Shadow Logging

### Repair Log (`~/.intent/repairs.jsonl`)

Every self-correction attempt logged for analysis:

```json
{
  "timestamp": "2026-01-16T10:30:45",
  "original_intent": "open_desktop",
  "original_input": "opn desktp",
  "error_type": "FileNotFoundError",
  "error_message": "Path not found",
  "suggested_fix": "open desktop",
  "status": "success",
  "retry_count": 1
}
```

**Use Cases**:
- Improve fuzzy matching
- Train better LLM prompts
- Identify common user errors
- Monitor system reliability

## System Health Checks

### Doctor Provider

```bash
intent> check system health

╔═══════════════════════════════════════════════════╗
║        Intent Shell - System Health Check        ║
╚═══════════════════════════════════════════════════╝

✓ Python Version: Python 3.12.0
✓ Core Dependencies: All core dependencies installed
⚠ Ollama: Ollama not running
✓ ChromaDB: ChromaDB installed, vector store exists
⚠ Admin Privileges: Not running as Administrator
✓ Filesystem Access: All common directories accessible
✓ Log Directory: Log directory writable

Summary: 5 OK, 2 Warnings, 0 Errors
Overall Status: OK
```

### Diagnostic Commands

```bash
# Full health check
intent> check system health

# Dependency check only
intent> check dependencies

# Quick status
intent> stats
```

## Production Deployment

### Recommended Settings

```bash
# Production (safe, no AI)
intent --no-ai --no-memory

# Development (all features)
intent --debug

# Automation (skip confirmations for GREEN only)
# Note: YELLOW/RED still require confirmation
```

### Environment Variables

```bash
# Disable AI fallback
export INTENT_NO_AI=1

# Disable semantic memory
export INTENT_NO_MEMORY=1

# Custom Ollama host
export OLLAMA_HOST=http://localhost:11434
```

### Monitoring

Check these logs:
- `~/.intent/logs/shell.log` - Structured logs
- `~/.intent/history.jsonl` - Transaction log
- `~/.intent/repairs.jsonl` - Self-healing attempts

### Metrics to Track

```python
# From repairs.jsonl
- Repair success rate
- Common error types
- Circuit breaker triggers

# From history.jsonl
- Command success rate
- Average confidence scores
- Intent distribution
```

## Safety Best Practices

### 1. Test in Non-Production First
```bash
# Create test user
# Run all commands
# Verify safety controls work
```

### 2. Monitor Repair Logs
```bash
# Check for patterns
cat ~/.intent/repairs.jsonl | grep '"status":"failed"' | wc -l

# Analyze error types
cat ~/.intent/repairs.jsonl | jq '.error_type' | sort | uniq -c
```

### 3. Configure Circuit Breaker
```python
# In executor.py, adjust threshold
CircuitBreaker(max_failures=3)  # Default

# For stricter control
CircuitBreaker(max_failures=1)  # Fail fast
```

### 4. Audit RED Actions
```bash
# Check RED action log
intent> stats
# Look at: RED Actions: N

# In code
safety_controller.get_red_action_log()
```

## Graceful Degradation

### If Ollama Unavailable
- Self-healing disabled
- Falls back to rule-based parser
- All core commands work

### If ChromaDB Unavailable
- Semantic memory disabled
- History commands unavailable
- All other features work

### If Admin Rights Missing
- Process kill commands fail gracefully
- Clear error messages
- Suggestion to run as admin

## Error Recovery

### FileNotFoundError
1. AI suggests typo correction
2. User confirms
3. Retry with corrected path

### PermissionError
1. Check if admin required
2. Suggest elevation: `Run as Administrator`
3. Circuit breaker prevents retry loops

### TimeoutError
1. Log timeout
2. Don't retry (timeout unlikely to resolve)
3. Suggest checking network/Ollama

## Advanced Features

### Custom Safety Levels

```python
# In safety.py
INTENT_SAFETY_LEVELS = {
    "my_intent": SafetyLevel.RED,  # Force confirmation
}
```

### Disable Self-Healing

```python
# In main.py
shell = IntentShell(enable_self_healing=False)
```

### Custom Circuit Breaker

```python
# In executor.py
CircuitBreaker(max_failures=5)  # More lenient
```

## Troubleshooting

### Circuit Breaker Won't Reset
- Check if command is actually succeeding
- Verify provider returns `success=True`
- Check logs: `~/.intent/logs/shell.log`

### Safety Confirmations Not Appearing
- Verify safety level is YELLOW or RED
- Check `INTENT_SAFETY_LEVELS` mapping
- Ensure `skip_safety_check=False`

### Repairs Not Logging
- Check write permissions on `~/.intent/`
- Verify `RepairLogger` initialized
- Check disk space

## Security Considerations

### Data Privacy
- All logs stored locally (`~/.intent/`)
- No data sent to external services (except Ollama if enabled)
- Vector embeddings remain on device

### Command Injection
- All commands go through provider validation
- No direct shell execution
- Entity extraction sanitizes inputs

### Privilege Escalation
- Admin check before privileged operations
- Clear warnings for RED actions
- Audit log for accountability

## Performance

### Self-Healing Overhead
- ~100ms for error classification
- ~2-5s for AI repair suggestion (if Ollama enabled)
- Zero overhead for successful commands

### Circuit Breaker
- O(1) lookup
- Minimal memory footprint
- Automatic cleanup on success

## License

MIT
