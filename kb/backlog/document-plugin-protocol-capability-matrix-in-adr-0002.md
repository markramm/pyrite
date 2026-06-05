---
id: document-plugin-protocol-capability-matrix-in-adr-0002
type: backlog_item
title: "Document plugin-Protocol capability matrix in ADR-0002 — which extensions implement which methods"
kind: documentation
status: proposed
priority: low
effort: XS
tags: [adr, documentation, plugins, protocol]
---

## Problem

ADR-0002's 2026-03-26 addendum honestly documents the plugin Protocol's
growth from 11 to 19 methods (it's 20 today). But the addendum does not record
**which extensions actually implement which methods.** Without that matrix,
every future "should we add another `get_X()` to the Protocol?" question lacks
a concrete answer to "how many extensions even use the existing methods?"

The modularity report found that ~12 of 20 Protocol methods return empty in
most plugins. That's exactly the kind of fact that an ADR addendum should
capture — it makes the next protocol-growth conversation concrete.

A capability matrix also makes the case for [[split-plugin-protocol-into-capability-protocols]]
self-evident: if the matrix is sparse, the Protocol is too wide.

## Solution

Add a section to ADR-0002 (third addendum, dated when this ticket is worked)
with a capability matrix:

| Method | cascade | encyclopedia | journalism-investigation | social | software-kb | zettelkasten |
|---|---|---|---|---|---|---|
| `get_entry_types` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `get_type_metadata` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `get_cli_commands` | ✓ | — | ✓ | — | ✓ | — |
| `get_mcp_tools` | ✓ | — | ✓ | — | ✓ | — |
| `get_db_columns` | — | — | ✓ | — | ✓ | — |
| `get_db_tables` | — | — | ✓ | — | — | — |
| ... | | | | | | |

Filled in by inspecting each extension's plugin class (a 30-minute pass —
`grep -n "def get_" extensions/*/src/*/plugin.py`). The matrix lives in the
ADR addendum as a structural snapshot of the protocol-extension relationship
at the date of the addendum.

The matrix forces an explicit answer to: "do we need 20 methods, or do most
plugins only use the same 4–6?"

## Acceptance criteria

- A third addendum on ADR-0002 with a complete method-by-extension matrix
  covering all 6 in-tree extensions.
- Each ✓ row counted; rows with ≤1 ✓ flagged for review (candidates for
  removal or for moving to a narrower protocol per
  [[split-plugin-protocol-into-capability-protocols]]).
- One paragraph at the bottom of the addendum recording the matrix-level
  observation: sparsity, hot methods, cold methods.

## Related

- [[split-plugin-protocol-into-capability-protocols]] — the matrix is the
  evidence base for that ticket's "Option A vs Option B" decision.
- ADR-0002 — the home of this addendum.
- [[plugin-developer-guide]] (done) — adjacent docs deliverable but at a
  different layer (user-facing how-to, not architectural snapshot).
- The modularity report committed alongside this ticket.
