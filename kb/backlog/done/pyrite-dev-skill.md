---
type: backlog_item
title: "Pyrite Development Workflow Skill"
kind: feature
status: completed
priority: medium
effort: M
tags: [ai, claude-code, dx, workflow]
---

A Claude Code skill for contributing to Pyrite itself. Enforces project conventions:

**Covers:**
- TDD workflow (pytest, vitest, playwright)
- Backlog management process (complete → done/ → update BACKLOG.md)
- Architecture patterns (plugin protocol, service layer, DB migrations)
- Pre-commit hook expectations (ruff, ruff-format, pytest)
- PR workflow

**Implementation:**
- `skills/pyrite-dev/SKILL.md` — main skill with project conventions
- `skills/pyrite-dev/testing.md` — test patterns (backend pytest, frontend vitest/playwright)
- `skills/pyrite-dev/backlog-process.md` — the backlog management workflow
- References existing ADRs and standards in `kb/`

**Inspired by:** Superpowers' TDD + verification-before-completion skills, adapted for Pyrite's specific toolchain and conventions.
