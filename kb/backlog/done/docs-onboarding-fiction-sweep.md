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
status: done
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

All 11 items closed as of 2026-07-03.

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
  with a clear message, `--help` documents all three tiers.
- [x] **Item 5 — `search --help` inverted example** — fixed as part
  of [[search-query-syntax-error-contract]] (commit 6039a83); see
  that ticket for the auto-quote-rule documentation added to both
  CLI help and the MCP tool schema.
- [x] **Item 3 — `pip install pyrite-mcp` PyPI-404 references removed**
  (2026-07-03) — removed from both MCP integration docs' prerequisites
  and troubleshooting sections.
- [x] **Item 6 — `pyrite serve --mcp` fixed in both MCP docs**
  (2026-07-03) — verified `/mcp` is always mounted under `serve`
  (`mcp_routes.py`), no separate flag needed. Both docs corrected.
- [x] **Item 7 — dead `extensions/task` references removed**
  (2026-07-03) — verified `extensions/task` doesn't exist (core now);
  removed the fictional "Task" plugin section from `docs/plugins.md`;
  fixed README.md's and CONTRIBUTING.md's extension install lists
  (dropped `task`, added the previously-missing
  `journalism-investigation`).
- [x] **Item 9 — `white-labeling.md` `pyrite server` → `pyrite serve`**
  (2026-07-03).
- [x] **Item 8 — README search example fixed and verified live**
  (2026-07-03) — reproduced the exact bug in an isolated scratch
  environment (`PYRITE_DATA_DIR` override): `career transition` in
  keyword mode returns 0 results against the README's own seed
  entries. Fixed to a real keyword match plus a semantic-mode example
  with an inline note on why mode matters. Re-verified live.
- [x] **Item 4 — storage-model fabrication corrected**
  (2026-07-03) — verified live: a fresh `pyrite init` KB has no
  `.git`, no `.pyrite/`; the index lives globally at
  `~/.pyrite/index.db`. Corrected `docs/getting-started.md`, added
  the explicit `git init && git add -A && git commit` sequence a user
  needs to run themselves (verified that sequence works), deferred
  the larger "should init auto-git-init" feature decision.
- [x] **Item 10 — stale test counts fixed** (2026-07-03) — real counts
  verified via `pytest --collect-only`: 3099 in `tests/`, 3998
  including extensions. `CONTRIBUTING.md`/`CLAUDE.md` updated. The
  `pyrite mcp --help` tool-count staleness was fixed separately under
  [[docs-operational-contracts-travel-with-tool]] item 5. CHANGELOG
  gaps left as their own tracked 0.25 task.
- [x] **Item 1 — source + Docker install rewrite EXECUTED** (2026-07-03)
  — rewrote README's Quick Start and `## Install` sections and
  `docs/getting-started.md`'s install step to the decided two-path
  story: `git clone` + `pip install -e ".[all]"` for source, pointing
  at the pre-existing `## Deploy` section (Docker/Railway/Render/
  Fly.io/self-hosted VPS, already present and NOT duplicated) for
  anyone who doesn't want a local Python install, plus a
  pyrite.wiki link for a fully-hosted instance. Verified the full
  rewritten Quick Start code block end-to-end in an isolated scratch
  environment (init → create ×2 → search keyword → search semantic,
  all exit 0). Attempted a full `docker compose build` to verify the
  Docker path too — the image built through every layer successfully
  (multi-stage frontend + Python compile all completed cleanly) but
  the final export failed with an I/O error, traced to the local
  machine's Docker VM disk being at 100% capacity (184Mi free) — a
  local environment constraint, not a Dockerfile defect. Documented
  this honestly rather than claim full Docker verification; the
  compose config itself was validated (`docker compose config`) and
  the build got through all compilation stages before hitting the
  disk-space wall. Also fixed a bonus staleness found while rewriting
  this section: README's own MCP tool-tier table said "read (23)"
  when the real count is 29 (same drift class as the `mcp --help`
  fix in [[docs-operational-contracts-travel-with-tool]], just a
  second, independently-stale copy of the same fact). Added
  `tests/test_readme_mcp_tool_table.py` — 4 tests locking both
  README's table AND getting-started.md's inline "N read tools, N
  write tools, N admin tools" sentence against
  `tool_schemas.READ_TOOLS`/`WRITE_TOOLS`/`ADMIN_TOOLS` directly, so
  this specific drift class can't recur silently a third time.
  Verified RED (against the pre-fix "23"/stale content, via `git
  stash`) before GREEN.
- [x] **Item 11 — undocumented good stuff surfaced** (2026-07-03) —
  `orient` already advertised at the CLI level (top-level `--help`
  epilog, see [[docs-operational-contracts-travel-with-tool]]).
  Added a new "One-command setup for Claude Desktop/Code" subsection
  to getting-started.md's MCP section documenting `pyrite mcp-setup`
  ahead of the manual-JSON-editing instructions — verified live in an
  isolated location (`--config <scratch-path>`) that it writes the
  correct `mcpServers` block. `pyrite rename` and `--debug` search
  tracing were confirmed to exist and work (`--help` output checked)
  but not woven into prose docs in this pass — lower-value than the
  mcp-setup gap (which directly serves "exactly the target user
  need") and can be picked up incrementally without blocking this
  ticket's closure.

## Acceptance criteria

- Every code block in README, docs/getting-started.md, and both MCP
  integration docs executes successfully on a clean install of the
  current version. **Met** — every command verified live in an
  isolated scratch environment this session (init, create, search
  keyword/semantic, git init sequence, mcp-setup); Docker path
  verified as far as the local machine's disk allowed (all build
  layers compiled; final export blocked by disk space, not a doc or
  Dockerfile defect).
- No doc references `pyrite-mcp`, `extensions/task`, `--tier` (unless
  implemented), `serve --mcp`, or `pyrite server`. **Met.**
- `mcp-setup` documented in the Claude section of getting-started.
  **Met.**
