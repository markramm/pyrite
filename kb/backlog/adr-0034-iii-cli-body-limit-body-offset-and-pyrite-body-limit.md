---
id: adr-0034-iii-cli-body-limit-body-offset-and-pyrite-body-limit
title: 'ADR-0034 (iii): CLI --body-limit / --body-offset and PYRITE_BODY_LIMIT, with the stderr notice'
type: backlog_item
tags:
- mcp
- agent-ux
- bounded-reads
- adr-0034
- blocked
importance: 5
kind: improvement
status: proposed
priority: medium
effort: S
rank: 0
---

**BLOCKED — not dispatchable. ADR-0034 ("Agent-facing reads are bounded by default", PR #170) is `proposed`, not accepted.** The numbers in rule 4 are the maintainer's to set. Re-read the ADR as accepted before dispatching: if a number, a variable name or the CLI default changed, this item changes with it.

## Problem

The CLI has no body bound at all, and most of its callers today are agents (Claude Code and similar) for whom the context window matters as much as over MCP. It also serves scripts and the maintainer at a terminal, so its default must stay complete (ADR-0034 rule 5).

## Acceptance (rule 5)

1. "`--body-limit N` / `--body-offset N` on every command that prints a body (`get`, `search --include-body`, exports to stdout), and the environment variable **`PYRITE_BODY_LIMIT`**, which applies the same limit to every such command in that environment."
2. Default output stays complete: with neither the flag nor the variable, every command's stdout is byte-identical to today's.
3. "When a limit truncates, `--format json` carries the same `body_*` keys as MCP and a one-line notice goes to stderr, so stdout stays parseable." The notice names `--body-offset <next>`.
4. The flag overrides the variable; `--body-limit 0` means "no limit" so one command can opt out inside an agent environment.
5. The ceiling (`PYRITE_BODY_CHUNK_MAX`) applies when a limit is in force.

## Groom 2026-09-18 (serial)

**Regimes:** `PYRITE_BODY_LIMIT` unset / valid / `"abc"` / negative (a clear error, not a traceback, and not silently ignored); flag and variable both set; `--body-offset` beyond the body's length (empty body, marker says so, exit 0); a body shorter than the limit (no marker, no notice); rich/terminal output vs `--format json` vs `--format yaml` (notice on stderr in all three; stdout parses in the structured ones); `search --include-body` with 20 results (the limit is per body; say whether the response budget applies — it does not unless the ADR as accepted says so); stdout piped to a closed pipe.

**Touches** — existing: `pyrite/cli/entry_commands.py` (`get` :87), `pyrite/cli/search_commands.py` (`--include-body` :85, :211), `pyrite/cli/export_commands.py` (stdout exports only), `pyrite/cli/output.py`, `docs/configuration.md`. New: `tests/test_cli_body_limit.py`.

**Sequence:** after ADR-0034 is accepted; after (i) — imports `pyrite/services/body_bounds.py`. Independent of (ii) and (iv) by file.

**Model:** sonnet (well-specified; one helper, three commands). **heavy:** no. **Cold read:** yes — a public CLI shape, and the "scripts receive corrupt data" failure the ADR names is exactly what a wrong default would cause. **Size:** S–M, ~250 lines.

**Out of scope:** setting `PYRITE_BODY_LIMIT` in agent-facing setup docs, `CLAUDE.md` templates and the skills (theme v); bounding the default (ADR alternative, rejected unless the maintainer reverses it on acceptance).
