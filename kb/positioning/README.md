---
type: design_doc
title: "Market Positioning Documents"
status: active
author: markr
date: "2026-02-23"
tags: [positioning, strategy, markets]
---

# Market Positioning Documents

Pyrite is a horizontal knowledge infrastructure platform. These documents analyze each addressable market segment — the use case, competitive landscape, differentiation, and go-to-market approach.

## Documents

| Market | File | Priority | TAM Signal |
|--------|------|----------|------------|
| Agent Shared Memory | `agent-shared-memory.md` | **1 — Ship now** | Fastest-growing; no incumbent |
| Software Development Teams | `software-teams.md` | **2 — Next** | Natural early adopters |
| Domain-Specific KB Creation | `domain-specific-kb.md` | **3 — Build partnerships** | Platform play |
| OSINT & Investigative Journalism | `osint-journalism.md` | **4 — Proven** | Proven by CascadeSeries |
| Enterprise Knowledge Management | `enterprise-kb.md` | **5 — Later** | Largest TAM, hardest entry |

## Cross-Cutting Concerns

**Web UI polish** — The current frontend is functional (entries, search, backlinks, daily notes, starred, templates, slash commands) but not Notion-polished. For agent shared memory (market 1), the CLI and MCP interface matter most. For all other markets, UI quality becomes progressively more important. Enterprise (market 5) cannot be entered without significant UI investment.

**Standalone packaging** — The go-to-market for agent shared memory depends on `pip install pyrite-mcp` being a 30-second experience. This is tracked as [backlog #52](../backlog/standalone-mcp-packaging.md).

**Single-maintainer sustainability** — Every market cares about project longevity. Mitigated by: 583 tests, 11 ADRs, comprehensive plugin guide, clear architecture docs, and dog-fooding (Pyrite's own backlog is managed in Pyrite). Building community through markets 1-2 is essential before markets 3-5 are viable.

## How to Read These

Each document follows the same structure:

1. **Market Overview** — What the buyers need and why
2. **Competitive Landscape** — Who's there now and what they get wrong
3. **Pyrite Differentiation** — What we do that nobody else does
4. **What's Already Built** — Shipped capabilities that back up differentiation claims
5. **Ideal Customer Profile** — Who adopts first
6. **Go-to-Market** — How we reach them
7. **Feature Gaps** — What we'd need to build
8. **Risks** — What could go wrong
