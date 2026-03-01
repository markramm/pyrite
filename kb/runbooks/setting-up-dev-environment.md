---
type: runbook
title: "Setting Up the Development Environment"
runbook_kind: setup
audience: "developers"
tags: [setup, development]
---

## Prerequisites
- Python 3.11+ (3.13 recommended)
- git

## Steps

### 1. Clone and create venv
```bash
git clone <repo-url>
cd pyrite
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install pyrite with dev dependencies
```bash
pip install -e ".[dev]"
```

### 3. Install all extensions
```bash
pip install -e extensions/zettelkasten
pip install -e extensions/social
pip install -e extensions/encyclopedia
pip install -e extensions/software-kb
pip install -e extensions/task
```

### 4. Install pre-commit hooks
```bash
pre-commit install
```

### 5. Verify
```bash
python -m pytest tests/ extensions/*/tests/ -q
```
Expected: 1780+ tests passing.

## Troubleshooting
- If pre-commit pytest fails: ensure extensions are installed in `.venv/` not just system Python
- If ruff-format modifies files: re-stage and commit again (hooks run twice on failure)
- If `generate_entry_id()` errors: it takes only 1 arg (title), not 3
