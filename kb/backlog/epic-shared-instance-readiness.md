---
id: epic-shared-instance-readiness
type: backlog_item
title: "Epic: Shared-instance readiness — trusted-peer read-only pilot"
kind: epic
status: proposed
priority: high
effort: L
rank: 2500
created: "2026-07-02"
tags: [epic, hosting, multi-user, collaboration, journalism]
links:
- target: verify-after-write-on-the-index-path
  relation: has_subtask
  kb: pyrite
- target: collapse-kb-registry-to-one-source-of-truth
  relation: has_subtask
  kb: pyrite
- target: oauth-state-store-persistence
  relation: has_subtask
  kb: pyrite
- target: mcp-rest-tool-parity
  relation: has_subtask
  kb: pyrite
- target: llm-usage-tracking-and-quotas
  relation: has_subtask
  kb: pyrite
- target: search-query-syntax-error-contract
  relation: has_subtask
  kb: pyrite
- target: docs-onboarding-fiction-sweep
  relation: has_subtask
  kb: pyrite
- target: docs-operational-contracts-travel-with-tool
  relation: has_subtask
  kb: pyrite
- target: security-audit-trail
  relation: related
  kb: pyrite
- target: hosting-security-hardening
  relation: related
  kb: pyrite
- target: epic-pyrite-publication-strategy
  relation: related
  kb: pyrite
- target: hosting-security-requirements
  relation: related
  kb: pyrite
---

## Thesis

Invite 1–2 trusted peer writers (candidates: Drey Dossier, The
Pugilist) onto a hosted Pyrite instance with **read access** to the
research corpus (cascade-research, cascade-timeline, actors). This
converts the corpus from a personal archive into shared
infrastructure — the "OSINT for the resistance" move — and makes
collaborators structurally invested rather than merely reciprocal.

Read-only first, deliberately. The read/write/admin tier split and
read-tier MCP already exist for exactly this. Write access is a
later epic, gated on provenance/source-tier enforcement.

## Relationship to existing epics

- [[hosting-security-hardening]] (accepted, XL) owns the full
  journalist threat model (REQ-1..8). This epic does NOT duplicate
  it — it cherry-picks the minimum needed for a *trusted-peer,
  read-only* pilot and defers the rest.
- [[epic-pyrite-publication-strategy]] owns the static/live split.
  The pilot is the first real test of the "investigation is live"
  surface with a non-Mark user.

## Scope (in order)

1. [[verify-after-write-on-the-index-path]] — prerequisite. Peers must
   never hit the silent-index class. (M)
2. [[collapse-kb-registry-to-one-source-of-truth]] — the sibling
   registry-drift half; finish the `all_kbs()` sweep and pick one
   registry owner. (M)
3. [[oauth-state-store-persistence]] — login must survive process
   restarts on the hosted instance; first-session login failure is a
   trust-killer. (S)
4. [[mcp-rest-tool-parity]] — peers get the web UI; Mark gets MCP.
   The pilot fails socially if the web surface is a second-class
   citizen. (M)
5. [[llm-usage-tracking-and-quotas]] — only if hosted AI features are
   enabled for peers; can ship after invite if AI is off at launch. (M)
6. [[search-query-syntax-error-contract]] — the remaining live member
   of the 40e7a39 crash class (sanitizer bypass on operator/quoted
   queries) plus QUERY_SYNTAX error classification; includes the
   deliberate pass over every MATCH/tsquery construction site. (S)
7. [[docs-onboarding-fiction-sweep]] — a peer's first hour IS the
   onboarding funnel; every documented command they'd run must work
   (`pip install`, `--tier read`, MCP setup). (S)
8. [[docs-operational-contracts-travel-with-tool]] — peers' agents
   won't have tcp-skills or Mark's memory notes; the operational
   contracts (index-after-write, claim semantics, error shape, search
   quoting rule) must ship in `orient`/help/docs. (M)
9. Hosting-security Phase 1 (static analysis audit from
   [[hosting-security-hardening]]) run against the pilot deployment
   config — audit only, fixes triaged by tier. (S)

## Explicitly out of scope (deferred, with reasons)

- **Write access for peers** — needs provenance guards (source tiers
  enforced by tool, not convention) and per-user fork directories
  ([[per-user-fork-directories]], [[fork-divergence-indicators]]).
- **SQLCipher at rest** ([[security-sqlcipher-option]]) — Tier-3
  hosting hardening; tracked under [[hosting-security-hardening]].
- **Generic OIDC/SSO** — GitHub OAuth is sufficient for 1–2 peers.

## Definition of done

- One peer logged in on the hosted instance, searching
  cascade-research + cascade-timeline read-only, for two weeks,
  without an operator intervention caused by index/registry drift.
- Zero known crash bugs reachable from the read surface.
- A written invite doc (what they can see, what's logged, what's not —
  per [[hosting-security-requirements]] REQ-1 posture).
