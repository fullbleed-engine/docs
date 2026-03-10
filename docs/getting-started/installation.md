# Installation

## Requirements

- **Python 3.8+** (3.11 recommended)
- **64-bit OS**: Windows, macOS, or Linux
- No other system dependencies required

## Install via pip

```bash
pip install fullbleed
```

That's it. No browser binaries, no system font packages, no native compilation required. The package includes pre-built Rust binaries for all major platforms.

## Verify Installation

```bash
fullbleed --help
```

If `fullbleed` is not found in your PATH, try:

```bash
python -m fullbleed --help
```

You should see the CLI help output with available commands.

## Platform Notes

=== "Windows"

    ```bash
    python -m pip install --upgrade pip
    python -m pip install fullbleed
    ```

    Use `python` (not `python3`) on Windows. Make sure you have the 64-bit version of Python.

=== "macOS"

    ```bash
    python3 -m pip install --upgrade pip
    python3 -m pip install fullbleed
    ```

=== "Linux"

    ```bash
    python3 -m pip install --upgrade pip
    python3 -m pip install fullbleed
    ```

    On Ubuntu/Debian, you may need `python3-pip`:

    ```bash
    sudo apt install -y python3-pip
    ```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `python: command not found` | Use `python3`, or re-install Python with "Add to PATH" checked |
| `No module named pip` | Run `python -m ensurepip --upgrade` |
| Error mentions Rust/cargo/wheel | Upgrade pip first: `pip install --upgrade pip` then retry |
| Permission errors | Use `pip install --user fullbleed` or a virtual environment |

## Virtual Environment (Recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
pip install fullbleed
```

## What's Next?

- [Quick Start →](quickstart.md) — Generate your first PDF in 3 commands
- [PdfEngine API →](../engine/pdf-engine.md) — Full API reference
