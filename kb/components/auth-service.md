---
id: auth-service
title: Auth Service
type: component
kind: service
path: pyrite/services/auth_service.py
owner: core
dependencies:
- pyrite.storage
- bcrypt
tags:
- core
- service
- auth
---

Local username/password authentication with session tokens for the web UI. Uses bcrypt for password hashing and SHA-256 hashed opaque tokens for sessions.

## Key Methods

- `register(username, password)` — creates a new user, returns user dict
- `login(username, password)` — validates credentials, creates session token
- `logout(token)` — invalidates a session
- `get_session(token)` — returns user info if token is valid

## REST Endpoints

Mounted at `/auth` (outside `/api` prefix) via `auth_endpoints.py`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/register` | POST | Create new user |
| `/auth/login` | POST | Login, returns session token |
| `/auth/logout` | POST | Invalidate session |
| `/auth/me` | GET | Session introspection |

## Related

- [[rest-api]] — auth endpoints are mounted at root level
- [[web-frontend]] — web UI consumes auth endpoints
