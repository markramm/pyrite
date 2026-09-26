---
id: access-policy
title: Access Policy
type: component
tags:
- core
- service
- auth
- authorization
importance: 5
kind: service
path: pyrite/services/access_policy.py
owner: core
links:
- target: adr-0037
  relation: related_to
  kb: pyrite
dependencies:
- pyrite.services.auth_service
- pyrite.services.kb_registry_service
---

The one place an access decision is made (ADR-0037 §1, #383). Framework-free: it imports nothing from FastAPI, Starlette, MCP or Typer. REST (through `pyrite/server/authz.py` and the dependencies in `api.py`), MCP (`mcp_routes.py`) and the live-update socket (`websocket.py`) build a `Principal` and ask it; none compares roles itself.

## What it owns

- **The role ladder**: `ROLES`, `ROLE_LEVELS`, `role_at_least`, `lower_role`. Written out nowhere else under `pyrite/` (`tests/test_role_ladder_has_one_home.py`).
- **The API-key role**: `resolve_api_key_role`.
- **A KB's default role**: config first, then the index registry (`KBRegistryService.registered_default_role`), honoured only as far as `PyriteConfig.confined_default_role` allows under an untrusted config.
- **The per-KB rule**: `kb_role` (global admin, grant, KB default role with the self-registered read cap, global role only with `global_access`, anonymous ceiling). `AuthService.get_kb_role` fetches the rows and asks it.
- **The effective role and the readable/writable sets**: `AccessPolicy.effective_kb_role`, `kbs_at_tier`, `read_scope`, `write_scope` (a `ReadScope`/`WriteScope` only the policy constructs).
- **Concealment**: `authorize(p, action, KB(k) | Row(k))` checks existence before role, so an unreadable KB answers `NOT_FOUND` exactly like a missing one; `FORBIDDEN` when readable but below the rung; `UNAUTHENTICATED` with no principal.

## Vocabulary

`Principal` (user, anonymous, operator_key, local), `Action` (the ADR's closed list; theme 1 decides the KB rungs and `INSTANCE_ADMIN`), `Resource` (`KB`, `Row`, `Instance`, `User`, `AnyKB`), `Decision`. `require` raises `KBNotFoundError` for a concealed or missing KB and `PolicyDeniedError` otherwise (folds into theme 2's `AccessDenied` family).

Services do not take a principal (ADR-0037, decision 3). The API helpers in `api.py` (`resolve_kb_default_role`, `kb_exists`, `effective_kb_role_for_user`, `kbs_for_user_at_tier`, `readable_kbs_for_user`) are delegates kept for their callers.
