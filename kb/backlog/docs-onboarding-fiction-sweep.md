---
id: docs-onboarding-fiction-sweep
type: backlog_item
title: "Docs fiction sweep: every documented onboarding command must actually work on v0.24"
kind: bug
status: proposed
priority: high
effort: S
created: "2026-07-02"
tags: [docs, onboarding, trust, field-reported]
epic: shared-instance-readiness
links:
- target: epic-shared-instance-readiness
  relation: subtask_of
  kb: pyrite
---

## Problem

A 2026-07-02 docs audit walked the documented onboarding path against
v0.24.0 in a clean environment. The prose is release-grade; the build it
describes doesn't ship. A new user (or invited pilot peer) hits a hard
failure at literally the first command. Verified fiction:

1. **`pip install pyrite` fails** — the PyPI name holds only an empty
   0.1 release with no distribution files ("No matching distribution
   found"). In README line ~22, docs/getting-started.md line ~8, and
   both MCP integration docs. pyrite.wiki already (correctly) says
   clone-from-source — the repo docs are behind the website. Decide:
   publish real wheels, or switch all docs to the source install.
2. **`pyrite mcp --tier read` does not exist** ("No such option") —
   documented in README, getting-started, openai-mcp-integration,
   gemini-mcp-integration. The backend supports tiers
   (`mcp_server.py` `tier: str = "read"`); the CLI never exposes the
   flag. This is the headline three-tier security story. Fix the CLI
   (preferred — the pilot needs it) AND the docs.
3. **`pip install pyrite-mcp` is a PyPI 404** (both MCP docs).
4. **getting-started fabricates the storage model**: "a git repo
   initialized automatically" — false (fresh `pyrite init` KB has no
   `.git`); "`.pyrite/` — SQLite index inside the KB" — false (index
   is global at `~/.pyrite/index.db`). For a git-native product aimed
   at journalists, silently-unversioned users are a real harm; either
   implement git-init on `init` or correct the claim loudly.
5. **`search --help` exclusion example is inverted**: `miller -bannon`
   returns Bannon-titled entries top-ranked (sanitizer quotes
   `-bannon` to a literal). Correct form is `miller NOT bannon`. See
   [[search-query-syntax-error-contract]] for the underlying sanitizer
   fix; this item covers the help text.
6. **`pyrite serve --mcp` does not exist** (openai-mcp-integration).
7. **docs/plugins.md points at `extensions/task`** — deleted directory,
   dead GitHub link (tasks moved into core). README architecture tree
   has the same ghost; CONTRIBUTING's `pip install -e extensions/task`
   is the same class.
8. **README search example returns 0 results as written**
   ("career transition" only matches in semantic mode — undocumented).
9. **white-labeling.md says `pyrite server`** — command is `serve`.
10. **Stale counts**: `pyrite mcp --help` lists 11 tools vs ~35 actual;
    CONTRIBUTING says 1468+ tests, CLAUDE.md ~2700, actual ~3813;
    CHANGELOG missing 0.13–0.19 and 0.21–0.24 (backfill is already a
    0.25 Workstream-3 task).
11. **Undocumented good stuff to surface while in there**:
    `pyrite mcp-setup` (one-command Claude setup — exactly what the
    target user needs, absent from all docs), `pyrite orient`,
    `pyrite rename`, `--debug` search tracing.

## Acceptance criteria

- Every code block in README, docs/getting-started.md, and both MCP
  integration docs executes successfully on a clean install of the
  current version (this is mechanically checkable — see
  [[ci-run-getting-started-tutorial]] for making it stay true).
- No doc references `pyrite-mcp`, `extensions/task`, `--tier` (unless
  implemented), `serve --mcp`, or `pyrite server`.
- `mcp-setup` documented in the Claude section of getting-started.
