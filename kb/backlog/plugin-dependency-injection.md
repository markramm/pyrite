---
type: backlog_item
title: "Replace Manual Plugin DI with Injected Dependencies"
kind: improvement
status: proposed
priority: medium
effort: M
tags: [plugins, architecture]
---

Extensions currently load config/DB by importing and calling global functions (e.g., `get_registry()`, constructing their own `PyriteDB`). This is manual dependency injection that:
- Creates tight coupling to specific global entry points
- Makes testing harder (must patch globals)
- Prevents the core from controlling lifecycle (e.g., connection pooling)

A plugin context object passed to plugin methods would be cleaner:

```python
class PluginContext:
    db: PyriteDB
    config: PyriteConfig
    logger: logging.Logger
    # etc.
```

This also addresses the hooks-db-access gap (see `hooks-db-access-gap.md`) — hooks could receive context with DB access included.
