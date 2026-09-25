---
id: adr-0037-theme-0-characterization-harness-for-every-rest-operation-and-mcp-tool
title: 'ADR-0037 theme 0: characterization harness for every REST operation and MCP tool'
type: backlog_item
tags:
- architecture
- security
importance: 5
kind: tech_debt
status: proposed
priority: high
effort: M
rank: 0
---

Source: ADR-0037, migration theme 0. Milestone 0.26 (maintainer, 2026-09-25).

## Groom 2026-09-25
- **Acceptance:**
  - Golden `(status, body)` pairs are recorded for the ADR §5 principal matrix × {readable, private, missing} KB, over every REST operation (enumerated from `create_app().openapi()`) and every MCP tool that takes a KB or row resource.
  - The error bodies of each `PyriteError` subclass are recorded per transport.
  - A shared surface inventory (`tests/_surface_inventory.py`) is what #380's ratchet and the ADR-0037 guard both walk.
  - No production change.
- **Footprint:** new `tests/characterization/`, `tests/_surface_inventory.py`. Fixtures come from `tests/test_api_tiers._build_client`.
- **Sequence:** after #380.
- **Model:** Sonnet.
- **Heavy:** yes (full route matrix).
- **Cold read:** yes (the goldens must pin real behaviour, not assert it).
- **Out of scope:** changing any response.
