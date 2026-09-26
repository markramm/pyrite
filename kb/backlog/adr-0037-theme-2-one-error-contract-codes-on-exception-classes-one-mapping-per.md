---
id: adr-0037-theme-2-one-error-contract-codes-on-exception-classes-one-mapping-per
title: 'ADR-0037 theme 2: one error contract (codes on exception classes, one mapping per transport)'
type: backlog_item
tags:
- architecture
- security
importance: 5
kind: tech_debt
status: in_progress
priority: high
effort: M
rank: 0
assignee: agent:pyrite-worker
---

Source: ADR-0037, migration theme 2. Milestone 0.26 (maintainer, 2026-09-25).

## Groom 2026-09-25
- **Acceptance:**
  - Every `PyriteError` class carries `error_code` and a safe default `public_message`.
  - An `AccessDenied` family exists.
  - `server/errors.py` is the single REST handler.
  - MCP `_refusal` reads the class codes and keeps `legacy_error_code` for one release.
  - `cli_error_from` exists.
  - The REST wire shape stays `{detail: {code, message, retryable, hint?}}`, and `docs/json-contracts.md` is corrected to match.
  - Endpoint `HTTPException` sites are NOT converted here.
- **Footprint:** `exceptions.py`, `server/api.py` (handler only), `server/errors.py` (new), `server/mcp_server.py` (`_refusal`, `_DOMAIN_ERROR_CODES`), `utils/errors.py`, `docs/json-contracts.md`, `kb/standards/api-design.md`.
- **Sequence:** after theme 0; runs in parallel with theme 1 (#383).
- **Model:** Sonnet.
- **Cold read:** yes.
