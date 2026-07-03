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
- [x] **Item 3 — `pip install pyrite-mcp` PyPI-404 references removed**
  (2026-07-03) — removed from both `docs/openai-mcp-integration.md`
  and `docs/gemini-mcp-integration.md`'s prerequisites lines and
  troubleshooting "standalone MCP package entry point" sections
  (which pointed at a `pyrite-mcp` binary that doesn't exist as a
  separate install). Left the source-install phrasing generic here
  rather than committing to the full item-1 Docker/source rewrite in
  this pass.
- [x] **Item 6 — `pyrite serve --mcp` fixed in both MCP docs**
  (2026-07-03) — verified `pyrite serve --help` has no `--mcp` flag;
  the MCP HTTP/SSE endpoint is verified real (`mcp_routes.py` always
  mounts `/mcp` under `serve`, no flag needed). Both docs now say
  "`pyrite serve` always mounts the MCP server at `/mcp` (no separate
  flag needed)".
- [x] **Item 7 — dead `extensions/task` references removed**
  (2026-07-03) — verified `extensions/task` doesn't exist (task
  commands are core, `pyrite/cli/task_commands.py`) and `extensions/`
  actually contains `cascade`, `encyclopedia`, `journalism-
  investigation`, `social`, `software-kb`, `zettelkasten`. Removed the
  fictional "### Task" plugin section from `docs/plugins.md`
  entirely (task management isn't a plugin, doesn't belong in an
  "Awesome Pyrite Plugins" doc). Fixed README.md's and CONTRIBUTING.md's
  extension install lists: dropped `extensions/task`, added the
  previously-missing `extensions/journalism-investigation` (a real gap
  found while fixing this, not explicitly named in the ticket).
- [x] **Item 9 — `white-labeling.md` `pyrite server` → `pyrite serve`**
  (2026-07-03) — one-line fix, verified against `pyrite serve --help`.
- [x] **Item 8 — README search example fixed and verified live**
  (2026-07-03) — reproduced the exact bug in an isolated scratch
  environment (`PYRITE_DATA_DIR` override, not the real `~/.pyrite`):
  `pyrite search "career transition" -k my-kb` (keyword mode, the
  default) returns `count: 0` against the two seed entries from the
  README's own `pyrite create` examples — confirmed exactly as the
  ticket claims, since neither entry's text contains those words
  verbatim. `--mode=semantic` correctly finds the Sarah Chen entry.
  Fixed the example to `pyrite search "consulting" -k my-kb` (a real
  word from the seed data, returns 1 result in keyword mode) plus
  `pyrite search "career transition" -k my-kb --mode=semantic` with
  an inline comment explaining why mode matters. Re-verified the fixed
  example end-to-end: both commands return `count: 1`.
- [x] **Item 4 — storage-model fabrication corrected**
  (2026-07-03) — verified in the same isolated environment: a fresh
  `pyrite init` KB has no `.git` and no `.pyrite/` subdirectory at all
  (just `kb.yaml` + template subdirs); the SQLite index lives globally
  at `~/.pyrite/index.db`, not inside the KB. Corrected
  `docs/getting-started.md`'s bullet list to describe what's actually
  created, added an explicit note that `pyrite init` does NOT run
  `git init`, and gave the exact `git init && git add -A && git commit`
  sequence a journalist-facing user would need to run themselves.
  Verified that sequence works (real `git init`/`add`/`commit` in the
  scratch KB, clean commit). Deferred the larger "should `init`
  auto-git-init" feature decision — this item corrects the claim
  loudly per the ticket's own stated fallback, doesn't implement the
  behavior change.
- [x] **Item 10 — stale test counts fixed** (2026-07-03) — real counts
  verified via `pytest --collect-only -q`: 3099 in `tests/` alone,
  3998 including `extensions/*/tests/` (not 1468 or ~2700).
  `CONTRIBUTING.md` and `CLAUDE.md` updated. The `pyrite mcp --help`
  tool-count staleness (11 vs ~35) was already fixed under
  [[docs-operational-contracts-travel-with-tool]] item 5 (29 read + 11
  write + 8 admin = 48, computed from `tool_schemas.py` at import time
  so it can't silently drift again). CHANGELOG version-range gaps
  (0.13–0.19, 0.21–0.24) left untouched — already tracked as its own
  0.25 Workstream-3 task per the ticket's own note.
- [ ] Item 1 — source + Docker install rewrite (**DECIDED**, not yet
  executed) — the largest remaining item; touches README,
  getting-started, both MCP docs' install sections coherently.
  Deliberately scoped OUT of this pass so the mechanical fixes above
  could land without waiting on the full install-story rewrite.
- [ ] Item 11 — undocumented good stuff (`mcp-setup`, `orient`,
  `rename`, `--debug` tracing) not yet surfaced in docs. `orient` is
  now advertised at the CLI level (top-level `--help` epilog, see
  [[docs-operational-contracts-travel-with-tool]]) but not yet in the
  prose docs (README/getting-started).

## Acceptance criteria

- Every code block in README, docs/getting-started.md, and both MCP
  integration docs executes successfully on a clean install of the
  current version (this is mechanically checkable — see
  [[ci-run-getting-started-tutorial]] for making it stay true).
  **Partially met** — items 2,3,5,6,7,8,9,10 verified working;
  item 1's install commands (`pip install pyrite`) still don't work
  since the PyPI-wheel rewrite hasn't landed yet.
- No doc references `pyrite-mcp`, `extensions/task`, `--tier` (unless
  implemented), `serve --mcp`, or `pyrite server`. **Met** for all of
  these except the now-implemented `--tier` flag, which is correctly
  referenced since it exists.
- `mcp-setup` documented in the Claude section of getting-started.
  **Not yet done** — part of remaining item 11.
