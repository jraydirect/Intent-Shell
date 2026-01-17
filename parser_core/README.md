# Parser Core - Rust Implementation

High-performance Rust implementation of IntelliShell's semantic parser.

## Building

### Prerequisites

- Rust toolchain (install from https://rustup.rs/)
- Python development headers

### Development Build

```bash
cd parser_core
cargo build --release
```

### Python Extension Build

The Rust extension is built automatically when installing the Python package using `maturin` or `setuptools-rust`.

For development:

```bash
# Install maturin
pip install maturin

# Build in development mode
cd parser_core
maturin develop

# Or build wheel
maturin build --release
```

### Using with IntelliShell

The Rust parser is automatically used if available. To disable:

```python
parser = SemanticParser(registry, ai_bridge=ai_bridge, use_rust=False)
```

## Architecture

- `types.rs` - Core data types (IntentMatch, Entity, etc.)
- `similarity.rs` - Fast string similarity calculation
- `matcher.rs` - Intent matching logic
- `entities.rs` - Entity extraction
- `py.rs` - Python bindings using PyO3

## Performance

Expected performance improvements:
- Similarity calculation: 10-50x faster
- Intent matching: 5-20x faster
- Memory usage: 50% reduction

## Testing

```bash
cd parser_core
cargo test
```
