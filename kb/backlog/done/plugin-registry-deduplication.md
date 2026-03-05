---
id: plugin-registry-deduplication
type: backlog_item
title: "Deduplicate PluginRegistry aggregation methods"
kind: improvement
status: completed
milestone: "0.17"
priority: medium
effort: S
tags: [architecture, plugins, code-quality]
links:
- plugin-system
---

# Deduplicate PluginRegistry aggregation methods

## Problem

`PluginRegistry` has 16 `get_all_*()` methods that follow an identical pattern:

```python
def get_all_X(self):
    self.discover()
    result = {}  # or []
    for plugin in self._plugins.values():
        if hasattr(plugin, "get_X"):
            try:
                plugin_X = plugin.get_X()
                if plugin_X:
                    self._merge_dict(result, plugin_X, ...)  # or result.extend()
            except Exception as e:
                logger.warning(...)
    return result
```

This is ~300 lines of copy-paste with only two variations: the method name called on each plugin, and the merge strategy (dict merge vs list extend). Adding a new plugin capability requires copying the entire block.

Additionally, `validate_transition()` puts workflow business logic inside what should be a pure registry/aggregation class.

## Solution

### 1. Generic aggregation helper

```python
def _aggregate_dict(self, method_name: str, kind: str) -> dict:
    """Aggregate dict results from all plugins, warning on key collisions."""
    self.discover()
    result = {}
    for plugin in self._plugins.values():
        if hasattr(plugin, method_name):
            try:
                items = getattr(plugin, method_name)()
                if items:
                    self._merge_dict(result, items, plugin.name, kind)
            except Exception as e:
                logger.warning("Plugin %s %s failed: %s", plugin.name, method_name, e)
    return result

def _aggregate_list(self, method_name: str) -> list:
    """Aggregate list results from all plugins."""
    self.discover()
    result = []
    for plugin in self._plugins.values():
        if hasattr(plugin, method_name):
            try:
                items = getattr(plugin, method_name)()
                if items:
                    result.extend(items)
            except Exception as e:
                logger.warning("Plugin %s %s failed: %s", plugin.name, method_name, e)
    return result
```

Then each public method becomes a one-liner:

```python
def get_all_entry_types(self) -> dict[str, type]:
    return self._aggregate_dict("get_entry_types", "entry type")

def get_all_kb_types(self) -> list[str]:
    return self._aggregate_list("get_kb_types")
```

### 2. Move `validate_transition` out

Move workflow validation to a `WorkflowService` or into the workflow plugin itself.

## Files likely affected

- `pyrite/plugins/registry.py` — refactor aggregation methods
- Tests that mock specific aggregation methods (if any)

## Success criteria

- Registry code reduced by ~250 lines
- All 16 `get_all_*()` methods use the generic helper
- `validate_transition` moved out of registry
- All existing plugin tests pass
