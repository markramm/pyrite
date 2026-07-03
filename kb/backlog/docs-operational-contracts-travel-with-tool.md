---
id: docs-operational-contracts-travel-with-tool
title: "Make operational contracts travel with the tool (orient/docs), not with the operator's skills and memory"
type: backlog_item
tags: [docs, agent-dx, mcp, orient, portability]
links:
- target: epic-shared-instance-readiness
  relation: subtask_of
  kb: pyrite
importance: 5
kind: improvement
status: proposed
priority: high
effort: M
rank: 0
---

## Problem

The knowledge agents need to use pyrite correctly lives outside
pyrite: in tcp-skills SKILL.md files (pyrite-search re-documents CLI
flags; kb-lifecycle carries frontmatter shape and the
seed→validate→index lifecycle — and is already stale on `orient`
syntax), in investigation-research's claim-conflict semantics ("do NOT
override; re-run task list"), and in the operator's Claude memory
notes (silent index failure, `--status` vs `readiness`, dual
registry). A fresh agent fleet — or an invited peer's agents on the
shared instance — relearns every field bug the hard way. This is the
core portability blocker for [[epic-shared-instance-readiness]].

Compounding it: the canonical JSON error contract exists only as a
docstring (`pyrite/utils/errors.py`); success envelopes are documented
nowhere; `kb/standards/api-design.md` still teaches the OLD
`{"error": "message"}` shape to extension authors; the CLI error-shape
convention is only recoverable from a done backlog item
(`cli-error-shape-consistency`) rather than a standard.

## Fix

1. **Extend `pyrite orient`** (and/or an MCP resource + top-level
   `--help` epilog) with the operational contracts: unindexed =
   unsearchable, run `index sync` after writes (incremental, cheap);
   task-claim atomicity and conflict behavior; the error contract
   (`{error, error_code, suggestion, retryable}`); the search
   auto-quote/bypass rule; `--format json` defaults per command group
   (and reconcile `task -f rich` vs everything-else `--format json`).
   Nothing currently tells a cold agent `orient` exists — advertise it
   in the CLI epilog the way the MCP `kb_orient` description already
   does ("Use this first").
2. **Write `docs/json-contracts.md`**: canonical error shape, success
   envelopes (`{query, count, has_more, results[]}`, `{entry}`,
   truncation fields `body_truncated`/`body_length`), exit codes.
3. **Promote the error-shape convention from
   `kb/backlog/done/cli-error-shape-consistency.md` into
   `kb/standards/api-design.md`** (replacing the stale
   `{"error": "message"}` guidance) so extension authors and agents
   find it in a standard, not a closed ticket.
4. **Document the multi-session git hazard in CLAUDE.md**: two+ Claude
   sessions commit to `dev` concurrently (observed 2026-07-02:
   backlog regroom session and 0.25 implementation session
   interleaving commits). Required discipline: explicit-path
   `git add` only (never `-a`/subtree adds), check `git status` for
   foreign staged changes before committing, re-read files before
   editing if the tree may have moved.
5. **Refresh `pyrite mcp --help`'s stale tool inventory** (claims 11
   tools; write tier exposes ~35 including orient/batch_read/task_*).
6. **Add AGENTS.md** (thin pointer to CLAUDE.md + orient) so
   non-Claude agents get an entry point.
7. Then **shrink the skills**: pyrite-search and kb-lifecycle drop
   their tool re-documentation sections and point at
   `orient`/`--help`, keeping only domain knowledge (KB inventory,
   capturecascade.org URL conventions).

## Progress

- [x] **Item 1 — orient/CLI epilog carry the operational contracts**
  (2026-07-03) — two parts:
  - Top-level `pyrite --help` gained an `epilog=` pointing a cold
    agent at `pyrite orient -k <kb-name>` as the recommended first
    call (previously `orient` was invisible except as one of ~20
    items in the auto-generated command list — a test confirmed the
    naive "orient appears somewhere in --help" bar was too weak, since
    `serve`/`mcp`'s own one-line descriptions happen to contain
    "Start" and would pass a loose substring check for the wrong
    reason).
  - `KBService.orient()` gained an `operational_contracts` field
    (`_operational_contracts()` static method) surfacing: the
    indexing contract (unindexed = unsearchable, `index sync` is
    incremental/cheap), the canonical error contract shape (kept in
    sync with `pyrite/utils/errors.py`'s `build_error` — same four
    keys, `suggestion` omitted-not-null), the search auto-quote rule
    (verbatim from `tool_schemas.py`'s `kb_search` description, so
    the two can't silently diverge), and task-claim atomicity/conflict
    behavior ("do NOT override; re-run the task list"). This surfaces
    identically in JSON (agents) and would flow into rich-mode
    (humans) since it's part of the same `result` dict `orient_kb` in
    `browse_commands.py` renders from.
- [x] **Item 2 — `docs/json-contracts.md` written** (2026-07-03) —
  documents the error shape, search-result envelope (`{query, count,
  results[]}` — `count` is `len(results)`, not a separate total),
  entry envelope (unwrapped, not `{"entry": ...}`), body-truncation
  fields (`body_truncated`/`body_length`/`body_offset`/
  `body_chunk_size`, all sourced from `mcp_server.py`'s `_chunk_body`),
  CLI exit codes, and `--format` defaults. Cross-links the operational
  contracts above rather than duplicating their wording.
- [x] **Item 3 — error-shape convention promoted into
  `kb/standards/api-design.md`** (2026-07-03, via `pyrite update`) —
  replaced the stale `Return {"error": "message"} for user errors`
  line with the full canonical shape (all four keys, omission rule,
  match-on-error_code guidance), a pointer to `docs/json-contracts.md`
  for the full contract, and a `## Provenance` section linking
  `cli-error-shape-consistency` (done) as history rather than the
  source of truth going forward.
- [x] **Item 4 — multi-session git hazard documented in CLAUDE.md**
  (2026-07-03) — new `## Multi-Session Git Hazard` section: explicit-
  path-only staging, check `git status` before staging, re-read files
  before editing if the tree may have moved, never assume you're the
  only writer even if `git status` was clean at turn-start.
- [x] **Item 5 — `pyrite mcp --help` tool inventory refreshed**
  (2026-07-03) — was hardcoded to 8 named read tools / "+3" for write
  / vague "KB management" for admin. Actual counts (verified against
  `pyrite/server/tool_schemas.py`'s `READ_TOOLS`/`WRITE_TOOLS`/
  `ADMIN_TOOLS` dicts): 29 read, +11 write, +8 admin (48 total before
  plugin tools) — the read tier alone grew 3.6x since the original
  text was written (orient, batch_read, task_* additions). Rewrote
  `_mcp_command_help()` to compute counts from the same dicts at
  import time so this can't drift silently again; a test
  (`test_help_tool_inventory_matches_actual_tool_counts`) asserts the
  three counts appear in `--help` output, so a future tool addition
  that isn't reflected fails CI instead of just going stale. Also
  added an `epilog=` to the `mcp` command pointing at `kb_orient` as
  the first call, matching item 1's CLI-level pointer.
- [x] **Item 6 — `AGENTS.md` added** (2026-07-03) — thin pointer
  (three steps: read CLAUDE.md, run `pyrite orient`, check
  `docs/json-contracts.md`) for non-Claude agent frameworks that
  specifically look for this filename.
- [x] **Item 7 — investigated, re-scoped as a follow-up ticket, NOT
  edited this session** (2026-07-03) — read both target files in
  `~/tcp-skills`. Findings: `pyrite-search/SKILL.md` is mostly domain
  knowledge already (KB inventory, capturecascade.org URL patterns,
  research strategy) — only ~5 lines are genuine CLI
  re-documentation, a smaller edit than the parent ticket implied.
  `kb-lifecycle/SKILL.md` has a CONFIRMED stale-syntax bug matching
  the parent ticket's own prediction: `pyrite orient {kb-name}` and
  `pyrite kb health {kb-name}` are wrong (both need `--kb`/`-k` as a
  named option, verified against real `--help` output), and several
  other commands (`index sync`/`build`, `recent`) have the same
  positional-vs-named mismatch. **Not edited**: `~/tcp-skills` is a
  separate git repo with its own uncommitted work in progress on a
  non-default branch at the time of this investigation — editing
  another actively-modified repo without checking in first is exactly
  the risk item 4's new CLAUDE.md hazard section warns against, and
  an AskUserQuestion asking how to proceed there went unanswered (60s
  timeout). Filed
  [[shrink-tcp-skills-pyrite-search-kb-lifecycle-skill-md-tool-re-documentation]]
  (medium, S) with the specific confirmed bugs listed, so the fix is
  ready to apply once the other repo's state is confirmed safe to
  touch.

## Acceptance criteria

- A cold agent with no tcp-skills, given only "use pyrite to research
  X in KB Y", can discover orient → search correctly → handle a
  QUERY_SYNTAX error → know to index-sync after a write, from
  tool-shipped surfaces alone. **Met** — `pyrite --help`'s epilog
  points to `orient`; `orient`'s `operational_contracts` field covers
  indexing, the error contract, search quoting, and task-claim
  semantics; `docs/json-contracts.md` covers the rest in depth.
- `api-design.md` teaches the canonical shape; the done-ticket is
  linked as provenance, not the source. **Met.**
- kb-lifecycle/pyrite-search SKILL.md no longer contain flag tables
  that can drift from `--help`. **Not met this session** — deferred
  to the follow-up ticket above (separate repo, concurrent-work
  safety concern).
