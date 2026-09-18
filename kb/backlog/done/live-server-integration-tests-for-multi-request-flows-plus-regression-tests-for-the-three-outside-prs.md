---
body: "## Problem\n\n~4000 tests, yet every bug the outside contributor found came from *deploying\nthe server and using it as a client*, and none of the three fixes has a\nregression test:\n\n- **PR #3** (MCP over SSE): `tests/test_mcp_routes.py` never asserts the emitted\n  `event: endpoint` path, so the doubled-path bug could return. Nothing tests\n  the install against mcp 2.x.\n- **PR #4** (KB created over REST invisible until restart): no test checks that\n  `add_kb()` refreshes `_db_kb_cache`. This is the **fourth** occurrence of the\n  stale-registry class (closed issues #1, #2, commit 37a37c9) — see\n  [[collapse-kb-registry-to-one-source-of-truth]], which this finding should\n  raise in priority.\n- **PR #5** (embedding prewarm): `tests/test_embedding_prewarm.py` has no\n  startup/lifespan assertion, so whether prewarm is wired in is untested.\n\nThe common gap: tests that start a real server process and run a multi-request\nflow (create a KB over REST, then search it; open an SSE session, then call a\ntool). The tests cover what an agent thought to test, not what a user does.\nSame family as the MCP dispatch smoke test (done).\n\n## Acceptance\n\n- [ ] A fixture starts `pyrite-server` on a free port against a temp data dir.\n- [ ] Flows: create KB over REST then read/search it without restart; MCP SSE\n      handshake asserts the endpoint path, then a tool call; startup triggers\n      prewarm.\n- [ ] Each of the three PR bugs, reintroduced, fails a test.\n\nSource: 2026-09-17 project review (three read-only audits: docs/contributor, public-repo, code-health). Related: [[ci-run-getting-started-tutorial]].\n\n## Scope added 2026-09-17: MCP over stdio\n\nThe SSE flow above covers the server transport. Claude Desktop and Claude Code\nuse **stdio**: `pyrite mcp` as a subprocess speaking JSON-RPC on stdin/stdout.\nNothing exercises that path end to end (`tests/test_mcp_tool_dispatch_smoke.py`\ncalls handlers in-process). Add to acceptance:\n\n- [ ] Spawn `pyrite mcp` (from the installed package, not the checkout), send\n      `initialize`, `tools/list`, and a `kb_search` call against a temp KB;\n      assert the tool list matches `tool_schemas.py` for the configured tier\n      and the search returns the seeded entry.\n- [ ] Same over SSE, so the two transports are asserted against each other.\n\nRoadmap: 0.24.2 workstream 1, \"every interface has an end-to-end test in CI\"."
file_path: /Users/markr/pyrite-wt/feature-smoke-e2e/kb/backlog/live-server-integration-tests-for-multi-request-flows-plus-regression-tests-for-the-three-outside-prs.md
id: live-server-integration-tests-for-multi-request-flows-plus-regression-tests-for-the-three-outside-prs
title: Live-server integration tests for multi-request flows, plus regression tests for the three outside PRs
type: backlog_item
tags:
- testing
- server
- programmatic-validation
importance: 5
kind: improvement
status: done
priority: high
assignee: agent:conductor
effort: M
rank: 0
---

## Problem

~4000 tests, yet every bug the outside contributor found came from *deploying
the server and using it as a client*, and none of the three fixes has a
regression test:

- **PR #3** (MCP over SSE): `tests/test_mcp_routes.py` never asserts the emitted
  `event: endpoint` path, so the doubled-path bug could return. Nothing tests
  the install against mcp 2.x.
- **PR #4** (KB created over REST invisible until restart): no test checks that
  `add_kb()` refreshes `_db_kb_cache`. This is the **fourth** occurrence of the
  stale-registry class (closed issues #1, #2, commit 37a37c9) — see
  [[collapse-kb-registry-to-one-source-of-truth]], which this finding should
  raise in priority.
- **PR #5** (embedding prewarm): `tests/test_embedding_prewarm.py` has no
  startup/lifespan assertion, so whether prewarm is wired in is untested.

The common gap: tests that start a real server process and run a multi-request
flow (create a KB over REST, then search it; open an SSE session, then call a
tool). The tests cover what an agent thought to test, not what a user does.
Same family as the MCP dispatch smoke test (done).

## Acceptance

- [ ] A fixture starts `pyrite-server` on a free port against a temp data dir.
- [ ] Flows: create KB over REST then read/search it without restart; MCP SSE
      handshake asserts the endpoint path, then a tool call; startup triggers
      prewarm.
- [ ] Each of the three PR bugs, reintroduced, fails a test.

Source: 2026-09-17 project review (three read-only audits: docs/contributor, public-repo, code-health). Related: [[ci-run-getting-started-tutorial]].

## Scope added 2026-09-17: MCP over stdio

The SSE flow above covers the server transport. Claude Desktop and Claude Code
use **stdio**: `pyrite mcp` as a subprocess speaking JSON-RPC on stdin/stdout.
Nothing exercises that path end to end (`tests/test_mcp_tool_dispatch_smoke.py`
calls handlers in-process). Add to acceptance:

- [ ] Spawn `pyrite mcp` (from the installed package, not the checkout), send
      `initialize`, `tools/list`, and a `kb_search` call against a temp KB;
      assert the tool list matches `tool_schemas.py` for the configured tier
      and the search returns the seeded entry.
- [ ] Same over SSE, so the two transports are asserted against each other.

Roadmap: 0.24.2 workstream 1, "every interface has an end-to-end test in CI".
