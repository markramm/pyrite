---
type: backlog_item
title: "Detect Plugin Name Collisions in Registry"
kind: bug
status: done
priority: medium
effort: S
tags: [plugins, registry]
---

`get_all_mcp_tools()` and `get_all_entry_types()` in the plugin registry build dicts via `.update()`. If two plugins register a tool or entry type with the same name, the last one loaded silently wins.

The test `test_no_tool_name_collisions` only verifies the three known extensions don't collide — it doesn't protect against future or third-party collisions.

Fix: check for key existence before `.update()` and either raise an error or log a warning with both plugin names. Consider namespacing plugin tools (e.g., `social:vote`, `zettel:inbox`).
