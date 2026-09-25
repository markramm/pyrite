---
id: tests-t6-extension-mcp-tools-tested-through-dispatch
title: 'Tests T6: extension MCP tools tested through dispatch'
type: backlog_item
tags:
- quality
- test
importance: 5
kind: tech_debt
status: proposed
priority: medium
effort: M
rank: 0
---

Source: test-architecture review 2026-09-25 (theme T6, fan-out on T4). Milestone 0.27, as the maintainer decided on 2026-09-24.

## Problem

There are 126 direct `plugin._mcp_*(...)` calls in 11 files (all 5 extensions, plus `tests/test_gates.py`). They bypass tier gating, the readable-set wrapper and argument handling. Core has `test_mcp_tool_dispatch_smoke.py` for breadth, but the extensions' behavioural tests never go through dispatch. The extensions are 65% small tests.

## Target shape

- Behavioural tests dispatch through `world.mcp(tier)`.
- Pure validator and type tests stay small.
- Each extension gets one tier-gating test per tool family.

## Groom 2026-09-25

**Acceptance** (verbatim from the review):
1. The direct `._mcp_` call count drops to an allowlist of handler-unit tests with a reason each (ratchet).
2. For each extension, a read-tier server refuses its write tools through dispatch.
3. The readable-set tests (`cascade/test_cascade_readable_set.py`, `journalism-investigation/test_*_readable_set.py`) pass through dispatch, and a test fails if the scoping wrapper is removed.

**Packages.** One per extension, all with disjoint files: software-kb, journalism-investigation, cascade, social, zettelkasten/encyclopedia, and `tests/test_gates.py`. The ratchet goes in `tests/test_test_rules.py` with the first package.

**Sequence:**
- After T4 (the builder's `.mcp(tier)`).
- After the private security batch, because the readable-set and scoping tests are its territory.
- For each extension, before that extension's #384 package (PluginContext services), so the refactor is made under dispatch-level tests.
- Cascade: check `remove-cascade-plugin` first. If the plugin is being removed, skip its package.

**Model:** Sonnet. **Size:** M in total (S each). **Heavy:** yes. **Cold read:** yes for the readable-set package (journalism-investigation), and no for the others.

**Out of scope:**
- Changing any extension's tool behaviour. A bug the dispatch path exposes gets filed, not fixed here.
- The PluginContext refactor (#384).
