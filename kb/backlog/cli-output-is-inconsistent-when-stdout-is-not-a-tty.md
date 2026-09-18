---
id: cli-output-is-inconsistent-when-stdout-is-not-a-tty
title: CLI output is inconsistent when stdout is not a TTY
type: backlog_item
tags:
- cli
- agent-experience
- quality
importance: 5
kind: improvement
status: proposed
priority: low
effort: S
rank: 0
---

## Problem

Found walking the README Quick Start in a clean environment: `init` and `search`
print raw JSON by default when stdout is not a TTY, while `create` prints plain
text. The semantic search result also dumps every DB column (`fips`,
`content_hash`, `rowid`), which is noise for both people and agents.

## Fix

One rule for every command: human text unless `-f json` (or a documented
non-TTY default applied uniformly). Search results return the documented entry
shape, not the row.

## Acceptance

- [ ] A test runs each Quick Start command with piped stdout and asserts one
      consistent format.

Source: 2026-09-17 project review (three read-only audits: docs/contributor, public-repo, code-health). Related: [[unify-rest-mcp-error-response-shape]].

## More instances (CLI probe, 2026-09-17)

Errors are as inconsistent as successes. With piped stdout, in one session:

- `get` / `update` / `rename` print a JSON object: `{"error": ..., "error_code": ...}`
- `create` / `delete` print text: `ERROR [NOT_FOUND]: ...`
- `update` on a missing entry reports `error_code: "ERROR"`; `get` on the same
  entry reports `NOT_FOUND`. `"ERROR"` is the catch-all and carries no information;
  an agent cannot branch on it.
- `pyrite link a <missing-target>` exits 0 and prints "Linked". That may be
  intended (wanted pages), but nothing says the target does not exist.

The MCP dispatcher had the same disease (every exception became
`INTERNAL, retryable: true`) and now maps domain errors to stable codes; the CLI
should reuse that mapping.
