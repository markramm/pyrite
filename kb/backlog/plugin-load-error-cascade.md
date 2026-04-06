---
id: plugin-load-error-cascade
type: backlog_item
title: "Fix or remove 'cascade' plugin reference that fails on every command"
kind: bug
status: proposed
priority: high
effort: S
tags: [cli, plugins, ux]
---

## Problem

Every `pyrite` invocation prints:

```
Failed to load plugin cascade: No module named 'pyrite_journalism_investigation'
```

This does not block functionality but adds noise to every command output and will confuse other users of a shared Pyrite instance. It also breaks JSON parsing when piping output programmatically (the error line precedes the JSON).

## Expected Behavior

Either the `pyrite_journalism_investigation` module should be installed, or the plugin reference should be removed from the config so the error stops appearing.

## Reproduction

Run any pyrite command:
```bash
pyrite kb list
pyrite search "test"
```
