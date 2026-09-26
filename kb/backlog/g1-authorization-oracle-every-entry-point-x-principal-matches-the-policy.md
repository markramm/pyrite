---
id: g1-authorization-oracle-every-entry-point-x-principal-matches-the-policy
title: 'G1: authorization oracle — every entry point x principal matches the policy'
type: backlog_item
tags:
- security
- architecture
importance: 5
kind: tech_debt
status: proposed
priority: high
effort: L
rank: 0
---

Maintainer decision 2026-09-26: in 0.26, first after security batch 3b.

Groomed in the security-review item's '## Groom 2026-09-26' (G1). Goal state: for every REST operation and MCP tool, and for every principal in the characterization world (including a per-KB write grant, a KB admin and an instance-admin session), the answer class equals what the policy decides for the operation's effect. A mismatch toward refusal may be pinned in a shrinking list; a mismatch toward access is never pinned. Covers derived data (links, titles, counts, lookups) by construction, so a new path cannot leak silently. Dispatch as a mission, plan first (dispatch.md).
