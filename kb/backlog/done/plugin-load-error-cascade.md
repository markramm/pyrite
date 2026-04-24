---
id: plugin-load-error-cascade
title: "pyrite extension list: AttributeError on every plugin, silently reports 0 types/tools"
type: backlog_item
tags: [cli, plugins, ux]
importance: 5
kind: bug
status: completed
priority: high
effort: S
rank: 0
---

## Problem

`pyrite/cli/extension_commands.py:395` calls `get_registry().get(name)`
but the `PluginRegistry` class exposes the plugin via `get_plugin(name)`
— there is no `get` method. Every `pyrite extension list` invocation
therefore raises `AttributeError: 'PluginRegistry' object has no
attribute 'get'` once per installed plugin, which the `except Exception`
block catches and logs as a full traceback to stderr.

Two visible symptoms:

1. **Noise on stderr** — six tracebacks (one per plugin) printed
   before the JSON output. Breaks programmatic consumers that aren't
   separating stderr.
2. **Silently wrong data** — because `plugin` ends up being the bound
   method `get` (thanks to `getattr` fallback through typer/click's
   dynamic attribute handling) or raises before `entry_types` /
   `tool_count` are filled, the command reports `entry_types: []` and
   `tool_count: 0` for every real plugin, even though
   `journalism_investigation`, `cascade`, etc. have many types and
   MCP tools.

## Historical note

The originally-filed symptom for this ticket was
`Failed to load plugin cascade: No module named
'pyrite_journalism_investigation'` on every command. That was a stale
install state — the JI plugin is now installed and loads cleanly. The
AttributeError above is the real, still-present bug in the same code
path, so this ticket is being repurposed rather than closed+reopened.

## Reproduction

```bash
.venv/bin/pyrite extension list 2>&1 | head -10
# Prints:
# Failed to inspect plugin encyclopedia
# Traceback (most recent call last):
#   File ".../cli/extension_commands.py", line 395, in extension_list
#     plugin = get_registry().get(name)
# AttributeError: 'PluginRegistry' object has no attribute 'get'
# ...
```

Then:

```bash
.venv/bin/pyrite extension list --format json | jq '.plugins[] | {name, entry_types: (.entry_types | length), tool_count}'
# Every plugin shows entry_types: 0, tool_count: 0 — wrong.
```

## Fix

One-line change: `get_registry().get(name)` → `get_registry().get_plugin(name)`
in `extension_commands.py:395`. Also drop the redundant second
`from ..plugins import get_registry` import at line 393-394 (already
imported at line 373).

## Test gap

`tests/test_extension_commands.py::TestExtensionList::test_list_with_plugins`
currently uses a bare `MagicMock()` as the registry, so
`mock_registry.get.return_value = mock_plugin` silently succeeds even
though `PluginRegistry` has no `get` method. Change to
`MagicMock(spec=PluginRegistry)` so the attribute mismatch fails loudly.
