---
id: commit-export-renderers
title: "Commit untracked export renderers package and commands"
type: backlog_item
tags: [hygiene, export]
kind: bug
status: done
effort: XS
---

## Problem

`pyrite/renderers/`, `pyrite/cli/export_commands.py`, `tests/test_collection_export.py`, and `tests/test_notebooklm_renderer.py` are untracked in git. The CLI imports `export_commands` at startup, so the application would fail on a clean clone without these files.

## Fix

Stage and commit these files. They represent completed work that should be in version control.
