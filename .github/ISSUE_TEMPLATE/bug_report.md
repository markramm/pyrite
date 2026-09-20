---
name: Bug report
about: Something is broken. Crashes, wrong results, a command that does not do what the docs say.
title: ""
labels: bug
assignees: ''
---

## What happened

What you ran, what you expected, what you got. Paste the exact command and the
error or traceback — the text, not a screenshot.

## Steps to reproduce

1.
2.

## Environment

- Pyrite version: `python -c "import pyrite; print(pyrite.__version__)"`
- Installed how: source checkout / `pip install "pyrite[...] @ git+...@vX.Y.Z"` / Docker
- Interface: CLI / `pyrite-server` REST / MCP (stdio or SSE) / web UI
- OS and Python version:

## Anything else

If this involves a knowledge base you cannot share, describe its shape (entry
types, rough size) rather than pasting content. Security problems go to the
[private report form](https://github.com/markramm/pyrite/security/advisories/new),
not here.

---

*Want to fix this yourself?* Before you spend more than an hour on it, say so
in a comment: two or three lines on how you'll fix it and what test proves it
(see [CONTRIBUTING.md](../../CONTRIBUTING.md#branches-hooks-and-pull-requests)).
