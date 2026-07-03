---
id: fail-open-exception-sweep
title: "Fail-open exception sweep: ~10 broad excepts convert failure to false success at trust boundaries"
type: backlog_item
tags: [reliability, exceptions, audit-2026-07]
links:
- target: epic-shared-instance-readiness
  relation: subtask_of
  kb: pyrite
- target: verify-after-write-on-the-index-path
  relation: related
  kb: pyrite
importance: 5
kind: tech_debt
status: proposed
priority: high
effort: S
rank: 0
---

## Problem

The 2026-07-03 code audit categorized ~35 broad `except Exception`
sites: ~30% legitimate boundaries, ~50% logged-and-degraded (the
plugin registry's documented before-raises/after-swallows policy is
the good model), and ~20% truly swallowed — fail-open behavior at
exactly the seams where past field bugs emerged. Ranked:

1. `pyrite/server/mcp_server.py:159-160` — `except Exception: pass`
   in `__init__` around merging DB-registered KBs into config. If the
   SELECT fails, DB-registered KBs silently vanish from the MCP
   surface (the dual-registry class, again).
2. `pyrite/storage/index.py:888-891` (+ `:807`) — the invalid-status
   drift detector swallows validator errors and silently disables
   itself — the check built after the 75-entry status drift can turn
   itself off.
3. `pyrite/services/kb_service.py:1382` — any push exception is
   relabeled `push_error = "No remote configured"`, masking
   auth/network failures.
4. `pyrite/storage/index.py:310-311` — frontmatter `references`
   dropped silently on parse error (recall-bug class).
5. `pyrite/services/auth_service.py:663,729` — decryption failure
   silently treated as plaintext token (documented, but a
   security-relevant fail-open; at minimum log at warning).
6. `pyrite/plugins/registry.py:519-521` — KB-type compatibility check
   fails → `return True` (fail-open authorization).
7. Low-stakes unlogged: `storage/repository.py:256`,
   `document_manager.py:87-88`, alembic `002_collaboration_tables.py`
   (4× pass).

Also in-family, from the CLI consistency review:
`search_commands.py` rich-mode silently falls back to file search on
index errors (masks index corruption as degraded search), and
`qa_service.py:377` + `kb_service.py:106` log write failures at
`debug` level.

## Fix

Per site: narrow the except to expected types, log at warning+ with a
WHY comment, and convert fail-open to fail-closed (or an explicit
degraded-state result) where the site guards an invariant. Follow the
plugin-registry policy shape. Add ruff BLE001 (or a review-checklist
rule): no bare pass / fail-open without a log line and a WHY comment.

**Amendment (2026-07-03, Mark):** log-at-warning is necessary but NOT
sufficient where the degradation changes user-visible behavior —
"logs are not available to agents using the CLI." Those sites also
need an in-band signal (stderr line + `warnings` array on JSON/MCP)
per [[in-band-degradation-signaling]]. Sites already closed log-only
(1, 2, 3) get their in-band signal retrofitted under that ticket —
no need to reopen them here.

## Progress

- [x] **Site #1 — mcp_server.py DB-registered-KB merge** (37a37c9,
  2026-07-03) — turned out to be a third near-identical copy of the
  same raw-SQL merge (cli/context.py had its own, already logging at
  debug; server/api.py had a fourth, also bare `except: pass`).
  Consolidated all three call sites into
  `PyriteDB.merge_registered_kbs(config)` (storage/kb_ops.py), narrowed
  to `SQLAlchemyError`, logs at warning with `exc_info`. Fault-injection
  test in tests/test_merge_registered_kbs.py. Net -60 LOC.
- [x] **Site #2 — index.py invalid-status drift detector** (30af0dd,
  2026-07-03) — two swallowed-exception paths, both fixed: (a) the
  `get_registry().get_validators_for_kb()` lookup wrapped in bare
  `except Exception: kb_validators = []`, disabling the check for the
  whole KB with no log; (b) each per-entry validator call (both the
  3-arg and 2-arg-fallback forms) wrapped in bare `except Exception:
  continue`. Both now log at warning with `exc_info` before degrading.
  The `TypeError` signature-compatibility fallback between validator
  call forms is unchanged -- legitimate boundary, not a swallow. Two
  fault-injection tests in test_storage.py::TestInvalidStatusInHealth.
- [x] **Site #3 — kb_service.py push_error mislabel** (2463476,
  2026-07-03) — root cause: `GitService.push()` never actually raises
  for real push failures (no remote, auth, network) -- it catches its
  own subprocess and returns `(False, message)`, which `push_kb()`
  already surfaced via `push_result["message"]` one line above the
  `except`. The `except Exception: push_error = "No remote configured"`
  was unreachable for the real no-remote case and only fires on
  something genuinely unexpected (e.g. a future `push_kb` change) --
  when it did, it categorically mislabeled whatever the real error was
  (e.g. an auth failure reported as a config problem). Now logs at
  warning with `exc_info` and surfaces `str(exception)`. Two tests:
  one confirms the already-working no-remote path reports the real git
  error (passed immediately -- documents existing correct behavior);
  one fault-injects `push_kb` raising and asserts the real message
  surfaces (failed before the fix, proving the swallow was reachable).
- [ ] Site #4 — index.py frontmatter `references` dropped silently
- [ ] Site #5 — auth_service.py decryption failure silently falls
  back to plaintext (security-relevant, at minimum warning-log)
- [x] **Site #6 — plugins/registry.py `_plugin_matches_kb_type` fail
  closed** (a7e0b82, 2026-07-03) — mechanical flip per the operator
  decision: `except Exception: return True` → `return False`, warning
  message now names the excluded plugin and KB type. This site was
  never silent (already logged at warning) -- the fix is the fail-open
  *behavior*, not visibility. New test in TestValidatorScoping: a
  plugin whose `get_kb_types()` raises must be excluded from
  `get_validators_for_kb`, not included; failed before the fix
  (validator was incorrectly returned). Broader semantics (wiring
  KB-type scoping into entry-type resolution itself, deterministic
  same-scope conflict handling) stay with
  [[plugin-type-resolution-scoping]] -- out of scope for the sweep.
  In-band signaling for this exclusion is tracked under
  [[in-band-degradation-signaling]], not retrofitted here per the
  operator's explicit split.
- [ ] Low-stakes site #7 (repository.py, document_manager.py, alembic
  4x pass)
- [ ] CLI-consistency-review items: search_commands.py silent
  file-search fallback, qa_service.py/kb_service.py debug-level write
  failures
- [ ] Lint/checklist rule preventing new fail-open sites

## Acceptance criteria

- Sites 1-6 fixed with a test each where feasible (fault-inject the
  swallowed exception, assert the failure is now visible).
- A lint or documented checklist rule prevents new fail-open sites.

