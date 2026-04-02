---
id: static-file-server
title: Static File Server
type: component
kind: module
path: pyrite/server/static.py
owner: core
tags:
- core
- server
---

Serves the SvelteKit web UI from the built dist/ directory. Handles SPA routing fallback for client-side navigation. Mounted as catch-all after API routes.
