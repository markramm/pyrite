---
type: backlog_item
title: "Plugin UI Extension Points"
kind: feature
status: proposed
priority: medium
effort: M
tags: [web, plugins, phase-4]
---

Allow plugins to extend the web UI:

**Backend:**
- `GET /api/plugins` — list registered plugins with entry types and capabilities

**Frontend:**
- `plugins/registry.ts` — plugin UI extension registry
- Plugins can register: sidebar items, command palette actions, entry type renderers
- Extension point system for custom entry type views

This bridges the existing backend plugin system with the web frontend.
