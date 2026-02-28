---
name: pyrite-dev
description: "Use when developing Pyrite core, extensions, web frontend, or API. Enforces TDD, systematic debugging, verification, and backlog management. Covers architecture, code patterns, testing conventions, and project processes."
---

# Pyrite Development Skill

## Overview

Systematic development workflow for Pyrite. Covers the full cycle: understand → plan → implement (TDD) → verify → complete.

**Announce at start:** "I'm using the pyrite-dev skill."

## The Iron Laws

```
1. NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
2. NO FIX ATTEMPTS WITHOUT ROOT CAUSE INVESTIGATION
3. NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
4. NO BACKLOG CHANGES WITHOUT UPDATING BACKLOG.md
```

Thinking "skip this just once"? That's rationalization. These exist because skipping them always costs more time than following them.

---

## Development Process

### Before Writing Code

Read the relevant backlog item, ADR, or design doc. Understand what you're building and why.

```
CHECKLIST — before any implementation:
- [ ] Read the backlog item / design doc / ADR
- [ ] Check kb/adrs/ for relevant architecture decisions
- [ ] Identify which files need to change (see Key Source Files)
- [ ] Check existing tests for the area you're modifying
- [ ] If multi-step: create tasks with TaskCreate, set dependencies
```

### Test-Driven Development

**RED → GREEN → REFACTOR. No exceptions.**

For detailed TDD patterns and anti-patterns, see [tdd.md](tdd.md).

**Quick version:**

1. **RED** — Write one failing test showing desired behavior
2. **Verify RED** — Run it. Confirm it fails for the right reason (feature missing, not typo)
3. **GREEN** — Write minimal code to pass the test. Nothing more.
4. **Verify GREEN** — Run it. Confirm it passes. Confirm other tests still pass.
5. **REFACTOR** — Clean up while staying green. Don't add behavior.
6. **Commit** — Frequent, small commits.

**Wrote code before the test?** Delete it. Start over. Don't keep it as "reference."

| Rationalization | Reality |
|-----------------|---------|
| "Too simple to test" | Simple code breaks. Test takes 30 seconds. |
| "I'll test after" | Tests passing immediately prove nothing. |
| "Need to explore first" | Fine. Throw away exploration, start with TDD. |
| "TDD will slow me down" | TDD is faster than debugging. Always. |
| "Manual test faster" | Manual doesn't prove edge cases. Can't re-run. |

### Systematic Debugging

**When something breaks: investigate root cause before attempting fixes.**

For the full 4-phase debugging process and supporting techniques, see [debugging.md](debugging.md).

**Quick version:**

1. **Read error messages carefully** — stack traces, line numbers, exact messages
2. **Reproduce consistently** — exact steps, every time
3. **Check recent changes** — `git diff`, recent commits, new deps
4. **Trace data flow** — where does bad value originate? Trace backward through call chain.
5. **Form hypothesis** — "I think X because Y." Test minimally. One variable at a time.
6. **Fix at root cause** — not at symptom. Add validation at every layer the data passes through.

**If 3+ fix attempts fail:** Stop. Question the architecture. Discuss before attempting more fixes.

| Red Flag | Action |
|----------|--------|
| "Quick fix, investigate later" | STOP. Investigate now. |
| "Just try changing X" | STOP. Form hypothesis first. |
| "Add multiple changes, see what works" | STOP. One variable at a time. |
| "I don't fully understand but this might work" | STOP. Understand first. |

### Verification Before Completion

**Evidence before claims. Always.**

```
BEFORE claiming any work is complete:

1. IDENTIFY: What command proves this claim?
2. RUN: Execute the FULL verification (not partial, not cached)
3. READ: Check output — exit code, failure count, warnings
4. VERIFY: Does output confirm the claim?
   - YES → State claim WITH evidence
   - NO  → State actual status with evidence
5. ONLY THEN: Make the claim
```

**Pyrite verification commands:**

| Claim | Run | Look For |
|-------|-----|----------|
| Backend tests pass | `cd /Users/markr/pyrite && .venv/bin/pytest tests/ -v` | `X passed, 0 failed` |
| Frontend unit tests pass | `cd web && npm run test:unit` | All tests pass |
| E2E tests pass | `cd web && npm run test:e2e` | All tests pass |
| Build succeeds | `cd web && npm run build` | `dist/` created, exit 0 |
| Linting passes | `ruff check pyrite/` | No errors |
| Type check passes | `cd web && npm run check` | No errors |
| KB index healthy | `.venv/bin/pyrite index health` | `✓ Index is healthy` |
| KB content findable | `.venv/bin/pyrite search "<feature>" -k pyrite` | Relevant results appear |
| Components documented | `.venv/bin/pyrite sw components` | New services listed |
| Backlog current | `.venv/bin/pyrite sw backlog` | Statuses match reality |

**Forbidden words without evidence:** "should work", "looks correct", "probably passes", "I'm confident"

### Pre-Commit Checklist: Use the CLI

**Dogfood Pyrite's own tools to manage the KB. Don't hand-edit markdown when the CLI can do it.**

```
⚠️  PRE-COMMIT: KB DOCUMENTATION (use CLI)
───────────────────────────────────────────
1. Sync the index to pick up any files changed during this work:
   .venv/bin/pyrite index sync

2. Search for existing docs that may need updating:
   .venv/bin/pyrite search "<feature name>" -k pyrite

3. Check current component/ADR/backlog state:
   .venv/bin/pyrite sw components
   .venv/bin/pyrite sw adrs
   .venv/bin/pyrite sw backlog --status proposed

4. Create or update KB entries via CLI:
   .venv/bin/pyrite create -k pyrite -t component --title "..." -b "..." --tags core,api
   .venv/bin/pyrite update <entry-id> -k pyrite -b "new body"

5. For new ADRs:
   .venv/bin/pyrite sw new-adr --title "..." --status accepted

6. Verify the new content is findable:
   .venv/bin/pyrite search "<key terms>" -k pyrite

7. Check index health:
   .venv/bin/pyrite index health
```

Use the correct `type` frontmatter for KB entries so plugin tools can find them:
- `type: component` (with `kind`, `path`, `owner`, `dependencies`) → shows in `pyrite sw components`
- `type: adr` (with `adr_number`, `status`, `date`) → shows in `pyrite sw adrs`
- `type: backlog_item` (with `kind`, `status`, `priority`, `effort`) → shows in `pyrite sw backlog`
- `type: standard` → shows in `pyrite sw standards`

```
⚠️  PRE-COMMIT: UPDATE BACKLOG (use CLI to verify)
───────────────────────────────────────────────────
- Completed a backlog item? → Set status: completed, move to done/, update BACKLOG.md
- Check backlog state: .venv/bin/pyrite sw backlog
- Discovered new work? → Create backlog_item file, add to BACKLOG.md
- Unblocked downstream items? → Note in BACKLOG.md

Ask: "Did this work change the status of any backlog item, or reveal new work?"
```

```
⚠️  PRE-COMMIT: UPDATE GOTCHAS
───────────────────────────────
- Hit a surprising behavior? → Append to .claude/skills/pyrite-dev/gotchas.md
- Resolved an existing gotcha? → Update or remove it from gotchas.md
- Found a new _resolve_entry_type mapping issue? → Document it

Ask: "Did I encounter any non-obvious behavior that would trip up the next agent?"
```

### Wave Completion Checklist

**Run this at the end of every wave, before the final commit.** This is both process enforcement and dogfooding.

```bash
# 1. Sync index to pick up all changes from this wave
.venv/bin/pyrite index sync

# 2. Verify KB health — no orphaned or stale entries
.venv/bin/pyrite index health

# 3. Search for the wave's key concepts — verify discoverability
.venv/bin/pyrite search "<wave feature 1>" -k pyrite
.venv/bin/pyrite search "<wave feature 2>" -k pyrite

# 4. Check component/ADR/backlog consistency
.venv/bin/pyrite sw components    # New services documented?
.venv/bin/pyrite sw adrs          # New decisions recorded?
.venv/bin/pyrite sw backlog       # Items updated?

# 5. Run full test suite
.venv/bin/pytest tests/ -v

# 6. Then commit
```

### Completing a Feature

When implementation + verification are done, follow the backlog process:

1. Set `status: completed` in the backlog item's YAML frontmatter
2. Move the file from `kb/backlog/` to `kb/backlog/done/`
3. Update `kb/backlog/BACKLOG.md` — move to Completed section, re-number
4. If work revealed new tech debt or follow-on features:
   - Create new `backlog_item` files
   - Place in `kb/backlog/` (priority) or `kb/backlog/future-ideas/` (low priority)
   - Add to `BACKLOG.md` in the correct position
5. Run `pyrite index sync` and verify with `pyrite sw backlog`
6. Commit the backlog changes

---

## Architecture Quick Reference

### Key source files

| File | Purpose |
|------|---------|
| `pyrite/plugins/protocol.py` | PyritePlugin Protocol (15 methods + `name` attribute) |
| `pyrite/plugins/registry.py` | Plugin discovery and aggregation |
| `pyrite/models/core_types.py` | 9 built-in entry types + ENTRY_TYPE_REGISTRY |
| `pyrite/models/factory.py` | Entry factory — `build_entry()` single dispatch point |
| `pyrite/cli/__init__.py` | Main Typer CLI app, all commands |
| `pyrite/storage/database.py` | PyriteDB (SQLite + FTS5) |
| `pyrite/storage/queries.py` | SQL queries (FTS search, tag search, graph) |
| `pyrite/server/api.py` | REST API factory, deps, rate limiter |
| `pyrite/server/endpoints/` | Per-feature endpoint modules (kbs, search, entries, etc.) |
| `pyrite/server/mcp_server.py` | MCP server (3-tier tools) |
| `pyrite/services/kb_service.py` | KBService CRUD with hooks |
| `pyrite/services/search_service.py` | SearchService — keyword, semantic, hybrid search + RRF |
| `pyrite/services/embedding_service.py` | EmbeddingService — vector storage, similarity search |
| `pyrite/services/embedding_worker.py` | EmbeddingWorker — background embedding pipeline |
| `pyrite/services/llm_service.py` | LLMService — provider-agnostic LLM abstraction |
| `pyrite/services/template_service.py` | TemplateService — entry templates and presets |
| `pyrite/services/git_service.py` | GitService — git operations, commit, diff |
| `pyrite/services/repo_service.py` | RepoService — multi-repo management |
| `pyrite/services/user_service.py` | UserService — user identity and auth |
| `pyrite/services/clipper.py` | ClipperService — web clipper |
| `pyrite/services/collection_query.py` | Collection query functions |
| `pyrite/schema.py` | KBSchema, FieldSchema — schema-as-config validation |
| `pyrite/config.py` | PyriteConfig, Settings, KBConfig |

### Architecture decisions

See `kb/adrs/` for full details:

| ADR | Decision |
|-----|----------|
| 0001 | Git-native markdown storage |
| 0002 | Plugin system via entry points |
| 0003 | Two-tier durability (content: git, engagement: SQLite) |
| 0006 | MCP three-tier tools (read/write/admin) |
| 0007 | AI integration: three surfaces, BYOK, Anthropic+OpenAI SDKs |
| 0008 | Structured data: schema-as-config, field types, object refs |

### 6 plugin integration points

1. **Entry type resolution** — `get_entry_class()` consults registry before GenericEntry
2. **CLI commands** — `cli/__init__.py` adds plugin Typer sub-apps
3. **MCP tools** — `mcp_server.py` merges plugin tools per tier
4. **Validators** — `schema.py` runs plugin validators always (even for undeclared types)
5. **Relationship types** — `schema.py` merges plugin relationship types
6. **PluginContext** — `set_context(ctx)` injects config, db, and services into plugins at startup

---

## Parallel Agent Work

For wave planning, agent launch checklists, and the merge protocol, see [parallel-agents.md](parallel-agents.md).

**Critical: Do NOT use `isolation: "worktree"`.** Agents work directly on main. Edit tool retries on conflict are cheaper than worktree merge ceremonies. See CLAUDE.md and parallel-agents.md.

**Quick rules:**
- **No worktrees** — agents write directly to the working tree, no isolation parameter
- Each wave item must list its file footprint — minimize shared modified files
- When agents share a file, Edit's exact-match fails gracefully on conflict — the agent retries
- Max 3 parallel agents per wave
- Commit all pending work before launching agents
- Run full test suite after all agents complete

## Extension Building

For complete scaffolding recipes, entry type contracts, plugin class templates, and validator/preset patterns, see [extensions.md](extensions.md).

## Testing Conventions

For the 8-section test structure, fixture patterns, and test-specific gotchas, see [testing.md](testing.md).

## Data Pipelines

For the entry lifecycle (create → validate → build → save → index → embed), type resolution behavior, and the build_entry factory, see [data-pipelines.md](data-pipelines.md).

## Gotchas

For known pitfalls with hooks, DB access, entry IDs, validators, and two-tier durability, see [gotchas.md](gotchas.md).
