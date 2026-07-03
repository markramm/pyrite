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
status: done
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
- [x] **Site #4 — index.py references-extraction swallow** (b2a220b,
  2026-07-03) — the `to_frontmatter()` fallback (recovering
  `references` when `entry.metadata` doesn't carry it) now logs at
  warning with `exc_info` instead of a bare `except: pass`. Test
  isolates this specific call site (there's an earlier, already-
  correct `to_frontmatter()` call for metadata extraction in the same
  method) via a `side_effect` that lets the first call succeed and only
  the second fail. Failed before the fix (zero warnings), confirming
  the swallow was reachable. **Deeper structural finding, filed
  separately:** `references:` never actually reaches typed entries
  (EventEntry, PersonEntry, etc.) in the first place — their
  `from_frontmatter` only reads specific known fields, unlike
  GenericEntry which collects all unknown keys into `.metadata`. So
  this site's fallback can only ever recover `references` for
  GenericEntry; for typed entries there's structurally nothing to
  recover. See
  [[typed-entries-silently-drop-the-references-frontmatter-field]]
  (medium, M) — out of scope for this sweep, which is about swallow
  visibility, not the underlying recall gap.
- [x] **Site #5 — auth_service.py decryption failure fails closed**
  (16a0e65, 2026-07-03) — both `get_github_token_for_user` and
  `get_user_api_key` had `except Exception: <return raw undecryptable
  bytes>`, rationalized as "may be stored as plaintext from before
  encryption was enabled." Fernet's `decrypt()` raises `InvalidToken`
  for ANY non-ciphertext value -- corrupted data, a rotated/wrong key,
  and genuine legacy plaintext are indistinguishable by exception type,
  so the old code returned corrupt-key-material as a usable token in
  every failure case, not just the legacy one. Now: logs a warning with
  `exc_info` and returns the same "absent" shape already used for
  no-token-stored (`(None, scopes)` / `None`) -- forces a reconnect,
  which re-stores through the normal encrypted path (the migration for
  legacy plaintext rows). The no-key-configured path (plaintext storage
  mode when `PYRITE_ENCRYPTION_KEY` isn't set) is untouched -- different
  code branch, `test_plaintext_fallback_when_no_key` still passes
  unchanged. Two fault-injection tests (GitHub token + API key) both
  failed before the fix (corrupted bytes returned as a real token/key).
  Full in-band signaling (surfacing the forced-reconnect reason to the
  UI, not just server logs) deferred to
  [[in-band-degradation-signaling]] per the same split as sites 1-4.
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
- [x] **Site #7 — low-stakes unlogged swallows** (2026-07-03) — two
  of the three fixed, one left as-is on inspection:
  - `repository.py`'s `find_file` frontmatter-scan fallback (`except
    Exception: continue` while scanning `*.md` for a matching
    frontmatter ID) now logs a warning naming the unreadable file
    before continuing the scan. Fault-injection test: a file with
    unterminated-YAML frontmatter in the scan path; asserts the
    warning names the file and the scan still returns None gracefully
    (not raising) — failed before the fix (zero warnings).
  - `document_manager.py`'s `_uses_templated_subdir` schema-lookup
    fallback (`except Exception: return False`) now logs a warning
    naming the entry type before returning the same safe default.
    Fault-injection test: mocks `repo.config.kb_schema` to raise;
    asserts the entry type appears in a warning log — failed before
    the fix.
  - alembic `002_collaboration_tables.py`'s 4× `except Exception:
    pass` around `ALTER TABLE ADD COLUMN` were NOT touched — inspected
    and confirmed legitimate: the code comment already documents these
    as deliberately idempotent (fail only when the column already
    exists, from a prior `create_all()`). Logging here would just add
    warning noise on every normal idempotent re-run without
    identifying any real failure mode. This is the sweep's own
    documented "~30% legitimate boundary" category, not a swallow.
- [x] **CLI-consistency-review items** (2026-07-03) —
  `search_commands.py`'s index-search-fails-fall-back-to-file-search
  path was inspected and found already correctly surfaced, not
  masked: it prints `[red]Search error...[/red]` /
  `[dim]Falling back to file search...[/dim]` to the console in rich
  mode, and returns a proper `{error, error_type}` JSON payload with
  exit code 1 in non-rich mode (both landed via the earlier
  `QuerySyntaxError`/`cli_error` work this session). The ticket's
  "masks index corruption as degraded search" framing was accurate at
  audit time but stale by the time this item was picked up — left
  unchanged. `qa_service.py:_maybe_create_task` and
  `kb_service.py:_auto_embed` both bumped `logger.debug` →
  `logger.warning` (with `exc_info`) — both are optional side effects
  (a follow-up task, a search-index embed) whose failure doesn't
  affect the primary write, but silent debug-level failure would hide
  a broken auto-task or auto-embed pipeline from operators. Two new
  fault-injection tests, both failed before the level bump (warning
  assertion found nothing at debug level).
- [x] **Lint/checklist rule preventing new fail-open sites** (2026-07-03)
  — evaluated ruff's `BLE001` (blind-except) as the mechanical gate.
  Found 153 pre-existing violations repo-wide (index.py 13,
  registry.py 12, kb_service.py 10, admin.py 10, github_auth.py 8,
  ...) — enabling it repo-wide today would either fail CI immediately
  or require blanket per-file-ignores that defeat the purpose, same
  shape as the mypy strict-ratchet decision on
  [[mypy-strict-ratchet-burn-down-pyrite-storage-errors]]. Filed
  [[add-ruff-ble001-blind-except-lint-gate-for-fail-open-prevention]]
  (medium, M) to scope a per-file-ignore ratchet or diff-scoped check
  rather than adding it unscoped in this pass.

## Acceptance criteria

- Sites 1-6 fixed with a test each where feasible (fault-inject the
  swallowed exception, assert the failure is now visible). **Met** —
  sites 1-7 all fixed (site 7 added beyond the original 1-6 scope).
- A lint or documented checklist rule prevents new fail-open sites.
  **Deferred** — evaluated and scoped as a follow-up ticket rather
  than implemented, since a naive rollout would be either broken (CI
  fails on 153 pre-existing sites) or toothless (blanket-ignored).
