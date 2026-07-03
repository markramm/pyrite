---
id: docs-operational-contracts-travel-with-tool
type: backlog_item
title: "Make operational contracts travel with the tool (orient/docs), not with the operator's skills and memory"
kind: improvement
status: proposed
priority: high
effort: M
created: "2026-07-02"
tags: [docs, agent-dx, mcp, orient, portability]
epic: shared-instance-readiness
links:
- target: epic-shared-instance-readiness
  relation: subtask_of
  kb: pyrite
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

## Acceptance criteria

- A cold agent with no tcp-skills, given only "use pyrite to research
  X in KB Y", can discover orient → search correctly → handle a
  QUERY_SYNTAX error → know to index-sync after a write, from
  tool-shipped surfaces alone.
- `api-design.md` teaches the canonical shape; the done-ticket is
  linked as provenance, not the source.
- kb-lifecycle/pyrite-search SKILL.md no longer contain flag tables
  that can drift from `--help`.
