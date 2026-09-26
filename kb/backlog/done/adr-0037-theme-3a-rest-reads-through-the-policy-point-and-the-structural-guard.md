---
id: adr-0037-theme-3a-rest-reads-through-the-policy-point-and-the-structural-guard
title: 'ADR-0037 theme 3a: REST reads through the policy point, and the structural guard lands'
type: backlog_item
tags:
- architecture
- security
importance: 5
kind: tech_debt
status: done
priority: high
effort: L
rank: 0
assignee: agent:pyrite-worker
---

Source: ADR-0037, migration theme 3a. Milestone 0.26 (maintainer, 2026-09-25). Meets the 0.26 definition-of-done structural guard.

## Groom 2026-09-25
- **Acceptance:**
  - `server/authz.authorize(...)` exists.
  - The 44 `requires_kb_read()` and 22 `get_readable_kbs` declarations are converted.
  - Cross-KB handlers take `ReadScope`.
  - The ADR §5 guard test enumerates every REST route and MCP tool and fails when one skips the policy; its allowlist can only shrink.
  - The theme-0 goldens are unchanged.
- **Footprint:** `server/authz.py` (new); `endpoints/{tags,tasks,reviews,timeline,kbs,git_ops,graph,links,ai_ep,templates,collections,search,versions,daily,blocks,entries,qa,starred,repos,admin}.py` (declarations only); the new guard test.
- **Sequence:** after themes 1 and 2.
- **Model:** Sonnet (mechanical once 1 and 2 land).
- **Cold read:** yes.
