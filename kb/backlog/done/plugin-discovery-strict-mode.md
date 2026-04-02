---
id: plugin-discovery-strict-mode
title: "Add strict mode for plugin discovery to surface load failures"
type: backlog_item
tags: [plugins, developer-experience]
links:
- target: plugin-system
  relation: related
kind: improvement
status: done
effort: XS
---

# Add strict mode for plugin discovery to surface load failures

## Problem

`PluginRegistry.discover()` logs warnings when a plugin fails to load but doesn't prevent app startup. This is correct for production resilience, but during development it silently hides import errors, missing dependencies, and broken plugins.

## Solution

Add a `--strict` flag (CLI) / `PYRITE_STRICT_PLUGINS=true` (env) that causes plugin discovery to raise on any load failure. Enable by default in `pyrite ci` and test runs.

## Files

- `pyrite/plugins/registry.py` — `discover(strict=False)` parameter
- `pyrite/cli/__init__.py` — `--strict` global flag
- `pyrite/config.py` — config option
