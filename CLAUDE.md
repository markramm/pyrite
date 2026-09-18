# Pyrite Development Guide

Pyrite is a knowledge infrastructure platform — Knowledge-as-Code for humans and AI agents.

## Using the KB for Project Context

This project has a comprehensive knowledge base in `kb/` indexed by Pyrite's own tools. **Use the CLI to get context before and during work** — it's faster and cheaper than reading files manually.

### Quick Context Lookups

```bash
# Search for anything — architecture, decisions, components, backlog items
.venv/bin/pyrite search "<topic>" -k pyrite

# Semantic search (finds conceptually related content, not just keyword matches)
.venv/bin/pyrite search "<question>" -k pyrite --mode semantic

# Get a specific entry by ID
.venv/bin/pyrite get <entry-id> -k pyrite

# Browse project structure
.venv/bin/pyrite sw components    # Core modules and services
.venv/bin/pyrite sw adrs          # Architecture Decision Records
.venv/bin/pyrite sw backlog       # All backlog items with status
.venv/bin/pyrite sw standards     # Coding standards and conventions

# Find what links to something
.venv/bin/pyrite backlinks <entry-id> -k pyrite

# Browse by tag
.venv/bin/pyrite tags -k pyrite
```

### When to Use KB Tools

- **Starting work on a feature**: Search for the backlog item, related ADRs, and component docs
- **Understanding architecture**: `pyrite sw components` and `pyrite sw adrs`
- **Finding related code**: `pyrite search "<module or pattern>" -k pyrite --mode hybrid`
- **Checking what's been decided**: `pyrite search "<topic>" -k pyrite` — ADRs and design docs will surface
- **Before modifying shared files**: Search for the file path to see what docs reference it

### Updating the KB After Work

When your work changes architecture, adds components, or completes backlog items:

```bash
# Sync index to pick up file changes
.venv/bin/pyrite index sync

# Create new entries using proper types
.venv/bin/pyrite create -k pyrite -t component --title "..." -b "..." --tags core
.venv/bin/pyrite create -k pyrite -t backlog_item --title "..." -b "..." --tags enhancement

# Create new ADRs
.venv/bin/pyrite sw new-adr --title "..." --status accepted

# Verify your changes are findable
.venv/bin/pyrite search "<your feature>" -k pyrite
.venv/bin/pyrite index health
```

Use correct `type` frontmatter so plugin tools can find entries:
- `type: component` (with `kind`, `path`, `owner`, `dependencies`) — `pyrite sw components`
- `type: adr` (with `adr_number`, `status`, `date`) — `pyrite sw adrs`
- `type: backlog_item` (with `kind`, `status`, `priority`, `effort`) — `pyrite sw backlog`
- `type: standard` — `pyrite sw standards`

## Key Architecture

- **Core code**: `pyrite/` — CLI, server, storage, services, plugins, models
- **REST API**: `pyrite/server/api.py` (factory + deps) + `pyrite/server/endpoints/` (per-feature modules)
- **MCP server**: `pyrite/server/mcp_server.py` (3-tier tools)
- **Extensions**: `extensions/` — zettelkasten, social, encyclopedia, software-kb, journalism-investigation, cascade
- **Web frontend**: `web/` — SvelteKit + Svelte 5
- **Knowledge base**: `kb/` — ADRs, backlog, components, designs, standards, runbooks

## Git Workflow (ADR-0025, amended by ADR-0032)

- **`dev`** — the integration branch and default. **Nobody pushes to it directly**, including this session: a ruleset requires a pull request whose checks passed on top of current `dev`, with no bypass.
- **`main`** — releases only; moves by fast-forward to a commit CI already verified (see the release runbook in `.claude/skills/pyrite-dev/release-runbook.md`).
- **Your branch** — every batch of work lives on `feature/*`, `fix/*` or `kb/*`, in **its own worktree**. Commit there at whatever pace the work needs.

**Start of a session** (one command; creates the worktree, branch, venv and hooks):

```bash
scripts/new-worktree.sh fix/what-it-fixes        # from origin/dev
cd ../pyrite-wt/fix-what-it-fixes
```

**End of a batch:**

```bash
git push -u origin "$(git branch --show-current)"
gh pr create --base dev --fill          # Fixes #N in the body for a bug
gh pr merge --auto --rebase             # merges itself when checks are green
gh pr view --json mergeStateStatus      # BEHIND? another PR landed first:
gh pr update-branch --rebase            #   rebase onto dev; checks re-run; auto-merge still armed
```

Auto-merge does not rebase for you: with "up to date" required, a PR goes
`BEHIND` the moment another one merges, and sits there until updated.

CI on a PR: ~30 s for docs/KB-only changes, ~4-5 min for code. If `dev` is red, no PR merges until it is fixed — that is the point. `rebase` is the default merge method; `squash` for a branch whose history is noise.

## Testing

```bash
# Backend tests (~3100 in tests/, ~4000 including extensions/*/tests/)
.venv/bin/pytest tests/ -v

# Frontend
cd web && npm run build && npm run test:unit

# Linting
ruff check pyrite/
```

## Parallel Agents

**Do NOT use `isolation: "worktree"` for parallel sub-agents inside one wave.** They share the session's branch and a file-footprint plan; worktree merges between them are fragile and expensive. Launch them without isolation, working on the session's branch in the session's worktree. When agents share a file, the Edit tool's exact-match replacement fails gracefully on conflict and the agent retries.

**Read `.claude/skills/pyrite-dev/parallel-agents.md` before launching parallel agents.**

The unit of isolation is the *session's branch*, not the agent: separate sessions get separate worktrees (above); sub-agents of one session share one.

## Multiple Sessions

Each session has its own worktree and branch, so the old shared-tree hazards (a hook stashing another session's edits, interleaved commits, a wiped shared index) cannot happen between sessions. Two rules remain:

- **Stage explicit paths.** Never `git add -A` or `git add .` — sub-agents of this session may have unrelated edits in the same tree.
- **Re-read before editing** when the Edit tool reports "modified since read"; a sub-agent moved the file.

If you find yourself in `/Users/markr/pyrite` on `dev` with uncommitted work, you are in the wrong place: `scripts/new-worktree.sh <branch>` and move the work there (`git stash` → `git stash pop` in the worktree).

## Pre-commit Hooks

One-time setup on a fresh clone: `.venv/bin/pip install -e ".[dev]"` (installs `pre-commit`), then `.venv/bin/pre-commit install`. If that fails with "Cowardly refusing to install hooks with core.hooksPath set", run `git config --unset-all core.hooksPath` first — some environments set it to a directory of unused `.sample` files, which blocks installation.

`pre-commit install` installs all three hook types (`default_install_hook_types` in `.pre-commit-config.yaml`). On a clone that installed hooks before 2026-09-17, re-run it once to pick up `commit-msg` and `pre-push`.

| Stage | What runs |
|-------|-----------|
| commit | ruff, ruff-format, trailing-whitespace, end-of-file, check-yaml, check-large-files, check-merge-conflict, debug-statements, import-cycle check, KB schema validation. Seconds. **No pytest.** |
| commit-msg | `fix:` commits must touch `tests/` |
| pre-push | full pytest suite incl. `extensions/`, `-n auto` (~3 min), only when the pushed range touches code or config |
| CI | the authority — everything above plus the full matrix |

If ruff-format modifies files, re-stage and commit again.

**Why the commit stage is fast:** pre-commit stashes *every* unstaged edit in the working tree to `~/.cache/pre-commit/patch*` while commit hooks run. With several sessions sharing the tree, a slow hook makes other sessions' edits vanish for minutes. `tests/test_dev_process_config.py` pins this layout — change the config and the tests together. If a commit is killed mid-hook (crash, Ctrl-C at the wrong moment), unstaged edits may exist *only* in the newest patch file: check `git apply --check ~/.cache/pre-commit/patch<newest>`, then `git apply` it.

The pre-push suite runs in parallel. A test that passes alone and fails under `-n auto` is a real bug in that test (shared state, fixed wall-clock timeouts under load, a shared port or path), not a reason to go serial; `tests/test_task_claim_concurrency.py` shows the pattern for process-spawning tests (start barrier + one group deadline). If a blocked push fails on a test you didn't touch, re-run that file under `-n auto` with the rest of the suite to confirm it is load-sensitive, then fix the test or file a GitHub issue for it; `--no-verify` needs a clear justification in the commit message plus the issue number.
