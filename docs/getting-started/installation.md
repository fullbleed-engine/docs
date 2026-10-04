---
title: Install Fullbleed for Python
description: Install Fullbleed on Python 3.10–3.14 for Windows, macOS, or Linux using a prebuilt wheel.
---
# Install Fullbleed for Python

Fullbleed supports Python 3.10–3.14. Published wheels cover Windows, macOS, and Linux, including the architectures listed below.

```bash
python -m pip install fullbleed
python -m fullbleed --version
python -m fullbleed doctor --strict --json
```

Use `python3` if that is your Python command. The wheel bundles the engine and fonts; the core package has no required third-party Python runtime dependencies.

## Use a virtual environment

```bash
python -m venv .venv
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install fullbleed
```

On macOS or Linux:

```bash
source .venv/bin/activate
python -m pip install fullbleed
```

## Published platforms

| Platform | Wheel targets |
| --- | --- |
| Windows | x86-64, x86, ARM64 |
| macOS | Intel, Apple silicon |
| Linux, manylinux2014 | x86-64, x86, ARM64, ARMv7, s390x, ppc64le |
| Linux, musllinux 1.2 | x86-64, x86, ARM64, ARMv7 |

The stable-ABI wheels cover supported CPython versions. For an unsupported target, a source build requires Rust; [source build instructions](https://github.com/fullbleed-engine/fullbleed-official#install) are in the engine repository.

## Troubleshooting

| Symptom | Next step |
| --- | --- |
| `fullbleed` command is not found | Use `python -m fullbleed` from the environment where you installed it. |
| pip starts a Rust build | Upgrade pip and check that your Python/platform has a published wheel. |
| Permission or externally managed environment error | Install inside a virtual environment. |
| Missing characters | Register a font containing those characters; see [fonts and assets](../engine/assets.md). |

[Create your first PDF →](quickstart.md)
