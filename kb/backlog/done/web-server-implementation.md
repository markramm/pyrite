---
id: web-server-implementation
title: "Implement Web Server (pyrite serve)"
type: backlog_item
tags: [api, web]
kind: feature
status: done
priority: low
effort: L
---

The `pyrite serve` command currently shows "Web server not yet implemented." FastAPI is already a dependency and used for the REST API module. Need to wire it up as a standalone server command.

**Completed**: Phase 1 implemented — SvelteKit frontend served from FastAPI, `/api` prefix migration, static file serving with SPA fallback, dual-mode `pyrite serve` command with `--dev` and `--build` flags.
