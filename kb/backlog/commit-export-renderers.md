---
id: commit-export-renderers
type: backlog_item
title: "Commit untracked export renderers package and commands"
kind: bug
status: proposed
priority: medium
effort: XS
tags: [hygiene, export]
epic: epic-release-readiness-review
---

## Problem

`pyrite/renderers/`, `pyrite/cli/export_commands.py`, `tests/test_collection_export.py`, and `tests/test_notebooklm_renderer.py` are untracked in git. The CLI imports `export_commands` at startup, so the application would fail on a clean clone without these files.

## Fix

Stage and commit these files. They represent completed work that should be in version control.
