---
type: backlog_item
title: "Move Unused/Premature Dependencies to Optional Groups"
kind: improvement
status: done
priority: low
effort: S
tags: [packaging, dx]
---

Several packages are in required dependencies but aren't needed for core functionality:

- **`fastapi` + `uvicorn`** — `pyrite serve` prints "not yet implemented"; no user needs these until the web server ships
- **`alembic`** — an `alembic/` folder exists with migration files, but the app uses a custom `MigrationManager`. Alembic is never called. Either integrate it or remove the dependency
- **`watchdog`** — unclear where it's used in the current codebase
- **`jinja2`** — may only be needed for the UI or future templating

Moving these to optional groups (e.g., `[web]`, `[dev]`) would reduce install size and avoid pulling in unnecessary transitive deps for CLI/MCP-only users.
