---
id: auth-endpoints
title: Auth Endpoints
type: component
kind: endpoint
path: pyrite/server/auth_endpoints.py
owner: core
tags:
- core
- auth
- endpoint
---

FastAPI auth routes: login, logout, register, session management, OAuth callbacks. Mounted outside /api prefix (no verify_api_key dependency). Handles cookie-based session auth for web UI.
