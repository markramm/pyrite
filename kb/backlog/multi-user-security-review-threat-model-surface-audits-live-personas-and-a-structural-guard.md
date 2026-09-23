---
id: multi-user-security-review-threat-model-surface-audits-live-personas-and-a-structural-guard
title: 'Multi-user security review: threat model, per-surface audits, live multi-persona testing, and a structural authorization guard'
type: backlog_item
kind: epic
tags:
- security
- multi-user
status: proposed
priority: high
effort: L
---

## Why (maintainer, 2026-09-23)

The multi-user path has had little manual testing, and the automated tests are
not catching everything. On 2026-09-23 a worker securing `/ws` (#218) found
that with auth enabled and no API keys configured, **any** `X-API-Key` or
`Bearer` value was answered "admin" on REST and `/mcp`. Every release from
v0.6.0 through v0.25.0 is affected. The conductor confirmed an anonymous
visitor could list, read and write private KBs. The fix
(`fix/api-key-role-requires-configured-keys`) also exposed a second bug:
`/mcp` session auth crashed.

Before this, 0.25 had already fixed read scoping across six extensions, `/ws`
(#218) and export paths (#221). Each was found one at a time.

## When

**After** the in-flight security fixes land: the key-role fix, #323 (`/ws`)
and #324 (export paths). The review should audit current code, not a moving
target (maintainer's call).

## Shape

1. **Threat model**: one Opus pass, read-only.
   - **Actors:** anonymous visitor, registered user, user with a KB grant, KB
     admin, instance admin, operator API key, and an outside contributor's PR
     (see `outside-prs-screen-before-anything-runs-review-after-ci-one-daily-routine`).
   - **Assets:** private KB content, write access, the server filesystem,
     stored GitHub tokens, sessions.
   - **Entry points:** REST routes, ~120 MCP tools (core and extensions),
     `/ws`, `/auth/*`, export/import, git and GitHub operations, and the
     clipper's URL fetch (SSRF).
   - **Output:** a threat-model document in `kb/designs/`, and the audit
     briefs below.
2. **Per-surface audits**: read-only reviewers, one surface each, taking no
   suite slots.
   - Authentication: sessions, cookies, CSRF, registration, API keys.
   - Authorization of every route and tool, **writes especially**. Reads were
     made structural in 0.25; writes still use per-endpoint checks.
   - Paths and injection: export/import, git, templates, FTS queries.
   - Outbound requests: SSRF through the clipper and the GitHub integration.
   - Extension tools.
   - Triage of the 56 open CodeQL alerts
     (`codeql-triage-and-close-the-56-open-code-scanning-alerts-on-dev`).

   **Every finding needs a reproduction on `dev`, or it is not a finding.**
3. **Live multi-persona testing**: `pyrite-explorer` against a live server
   with auth enabled. Three personas each try to reach the others' private
   KBs through the UI and the API. This takes two suite slots; nothing else
   heavy runs beside it.
4. **Structural guard**: extend `tests/test_read_scoping_is_structural.py` to
   writes and to authentication. The test enumerates every REST route and MCP
   tool, and fails when one lacks a covering read **and** write authorization
   test, so a new route cannot ship unguarded.

## Acceptance

- A threat-model document and a findings document in `kb/`. Each finding is
  reproduced, has a severity, and has a disposition: fixed, issue, or
  accepted with a reason.
- Exploitable findings are fixed forward (alpha; maintainer 2026-09-23), with
  regression tests that fail without the fix. Hardening items go in as issues.
- The structural guard is on `dev`.
- The README states the multi-user status honestly, e.g. "multi-user: alpha,
  security-reviewed <date>, known gaps: <list>".
