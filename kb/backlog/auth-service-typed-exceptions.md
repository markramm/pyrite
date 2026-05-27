---
id: auth-service-typed-exceptions
type: backlog_item
title: "Retype auth_service ValueError raises to typed exceptions with correct HTTP status mapping"
kind: improvement
status: proposed
priority: medium
effort: M
tags: [auth, errors, exception-hierarchy, security, rest-api]
---

## Problem

`pyrite/services/auth_service.py` raises bare `ValueError` for ~16 distinct
domain conditions — disabled registration, missing/invalid invite code, bad
credentials, weak password, duplicate username, disallowed GitHub org, invalid
role, ephemeral-KB limit reached, etc. (sites around lines 93, 111, 117, 120,
124, 127, 135, 194, 207, 210, 252, 441, 545, 768, 776, 782).

The project's exception hierarchy (`pyrite/exceptions.py`) exists specifically
to replace generic `ValueError`/`PermissionError` with typed `PyriteError`
subclasses, and a central REST handler now maps that hierarchy to HTTP status
codes (see commit `c348087`, `register_pyrite_exception_handler`). Auth was
**deliberately excluded** from the typed-exception sweep because these errors
carry different HTTP semantics that a blind conversion would get wrong:

- "invalid username or password" → **401 Unauthorized**, not 422.
- "registration is disabled" / "not a member of an allowed org" → **403
  Forbidden**.
- "username already taken" → **409 Conflict**.
- "password must be at least 8 characters" / "invalid role" → **400/422
  validation**.
- "ephemeral KB limit reached" → **429 / 403 quota**.

Mapping all of these to `ValidationError` (→ 422 under the central handler)
would silently change auth status codes that clients and the web UI depend on.

## Solution

1. Audit each `raise ValueError` in `auth_service.py` and classify its intended
   HTTP semantics (401 / 403 / 409 / 422 / 429).
2. Introduce auth-specific typed exceptions, e.g. `AuthError(PyriteError)` with
   subclasses `InvalidCredentialsError` (401), `RegistrationDisabledError` /
   `ForbiddenError` (403), `DuplicateUserError` (409), `QuotaExceededError`
   (429). Reuse `ValidationError` only for genuine input-format failures.
3. Extend the central handler's `_PYRITE_ERROR_STATUS` mapping in
   `pyrite/server/api.py` to cover the new types with their correct codes.
4. Update the auth endpoints that currently catch `ValueError` and hand-map to
   status codes so they either rely on the central handler or catch the new
   typed errors. Verify the existing auth endpoint status codes are unchanged.
5. Update auth tests that assert `ValueError` / specific status codes.

## Acceptance criteria

- No bare `raise ValueError` remains in `auth_service.py` for domain conditions.
- Each auth failure maps to the same HTTP status it returns today (no behavior
  change for clients) — verified by REST auth tests.
- New auth exception types live in the hierarchy and are covered by the central
  handler mapping.
- Login/register/invite/role/quota paths each have a test asserting the typed
  error and the HTTP status.

## Related

- Commit `c348087` — added `register_pyrite_exception_handler` and swept the
  non-auth services; this is the explicitly-deferred auth follow-up.
- `cli-error-shape-consistency` — adjacent error-shape work on the CLI side.
- `schema-constraints-in-mcp-and-rest`, `mcp-rest-tool-parity` — related
  REST/MCP consistency tickets.
