---
id: protocol-versioning-implementation
type: backlog_item
title: "Implement protocol versioning and satisfaction checking (ADR-0014)"
kind: feature
status: done
priority: medium
effort: M
tags: [protocols, extensions, schema]
links:
- extension-type-protocols
- entry-protocol-mixins
---

# Implement protocol versioning and satisfaction checking (ADR-0014)

## Problem

ADR-0014 designs a structural protocol system where extensions declare protocol requirements (e.g., `claimable/1.0`, `decomposable/1.0`) and the platform verifies satisfaction. Currently, protocols are documentation-only — there's no runtime or CLI validation that an entry type actually satisfies the protocols it claims.

## Solution

Implement the satisfaction checking described in ADR-0014:

1. **Protocol registry** — register protocol definitions with version and required fields
2. **`pyrite protocol check`** CLI command — validates that entry types satisfy their declared protocols
3. **`pyrite ci` integration** — protocol satisfaction as a CI check
4. **Schema extension** — `requires_protocols` field in type schema, validated during `pyrite index sync`

## Prerequisites

- Entry protocol mixins (done — ADR-0017)
- Extension type protocols Phase 1 (0.17)

## Files

- `pyrite/models/protocols.py` — protocol definitions
- `pyrite/services/schema_service.py` — satisfaction checking logic
- `pyrite/cli/schema_commands.py` — `protocol check` command
