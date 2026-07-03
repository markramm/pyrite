---
id: docs-onboarding-fiction-sweep
title: "Docs fiction sweep: every documented onboarding command must actually work on v0.24"
type: backlog_item
tags: [docs, onboarding, trust, field-reported]
links:
- target: epic-shared-instance-readiness
  relation: subtask_of
  kb: pyrite
importance: 5
kind: bug
status: proposed
priority: high
effort: S
rank: 0
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
   clone-from-source — the repo docs are behind the website.
   **DECIDED 2026-07-03 (Mark): rewrite all docs to source + Docker
   install for now** (no PyPI wheels yet — revisit at a later
   release). The install story is two paths: (a) clone + pip install
   from source for developers; (b) Docker container for everyone
   else, with the one-click cloud-service launch options
   (Railway/Render/Fly configs exist) featured — pyrite.wiki has the
   details and the repo docs should match/link it, not contradict it.
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

## Progress

- [x] **Item 2 — `pyrite mcp --tier` flag implemented** (594d392,
  2026-07-03) — added `--tier` (default `write`, preserving existing
  behavior) validated against `PyriteMCPServer.VALID_TIERS`, with a
  structured `INVALID_TIER` error via `cli_error` on a bad value.
  Surfaced and fixed an adjacent pre-existing bug in the same
  function while adding the first real test coverage for this
  command: the startup message used `console.print(..., err=True)`
  — a `click.echo` idiom, not a valid `rich.Console.print()` kwarg —
  which would have raised `TypeError` on every invocation. Replaced
  with a dedicated stderr `Console`, matching the `err_console`
  pattern in `search_commands.py`. Manually verified end-to-end:
  `pyrite mcp --tier read` starts cleanly, `--tier bogus` exits 1
  with a clear message, `--help` documents all three tiers. No doc
  changes needed — README/openai-mcp-integration.md already
  correctly documented `--tier read` as intended behavior; the CLI
  just hadn't caught up.
- [x] **Item 5 — `search --help` inverted example** — fixed as part
  of [[search-query-syntax-error-contract]] (commit 6039a83); see
  that ticket for the auto-quote-rule documentation added to both
  CLI help and the MCP tool schema.
- [ ] Item 1 — source + Docker install rewrite (**DECIDED**, not yet
  executed)
- [ ] Item 3 — `pip install pyrite-mcp` PyPI-404 references
- [ ] Item 4 — storage-model fabrication (git-init claim, `.pyrite/`
  location claim)
- [ ] Item 6 — `pyrite serve --mcp` doesn't exist
- [ ] Item 7 — dead `extensions/task` references
- [ ] Item 8 — README search example returns 0 results as written
- [ ] Item 9 — `white-labeling.md` says `pyrite server`
- [ ] Item 10 — stale tool/test counts, CHANGELOG gaps
- [ ] Item 11 — undocumented good stuff (`mcp-setup`, `orient`,
  `rename`, `--debug` tracing) not yet surfaced in docs

## Acceptance criteria

- Every code block in README, docs/getting-started.md, and both MCP
  integration docs executes successfully on a clean install of the
  current version (this is mechanically checkable — see
  [[ci-run-getting-started-tutorial]] for making it stay true).
- No doc references `pyrite-mcp`, `extensions/task`, `--tier` (unless
  implemented), `serve --mcp`, or `pyrite server`.
- `mcp-setup` documented in the Claude section of getting-started.

