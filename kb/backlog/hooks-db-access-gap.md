---
type: backlog_item
title: "Hooks Cannot Access DB Instance"
kind: bug
status: proposed
priority: medium
effort: M
tags: [plugins, hooks]
---

Hooks receive `(entry, context)` but context doesn't include the DB instance. This means hooks like `after_save_update_counts` (Social extension) can't actually update engagement tables.

Discovered during Social extension development. Current workaround: hooks log what should happen but can't execute it.

Options:
1. Pass DB in context dict
2. Service locator pattern
3. Callback/event bus
4. Plugin context object (see `plugin-dependency-injection.md`) — solves both DI and hook access in one design

Related: `plugin-dependency-injection.md`, `cli-bypasses-service-layer.md`
