# Pyrite Knowledge Base Skill

Use when working with pyrite knowledge bases: searching, reading, creating, updating, or deleting entries. Also covers index management, KB administration, and plugin CLI sub-commands.

## Quick Reference

One entry point: `pyrite`. Rich table output. Run `pyrite index build` before first use.

```bash
pyrite --help                                   # All commands + plugin sub-apps
pyrite search "plugin system"                   # Full-text search (FTS5)
pyrite get <entry-id>                           # Retrieve entry by ID
pyrite list                                     # Table of KBs with entry counts
pyrite create --kb=pyrite --type=note --title="My Note" --body="Content"
pyrite sw adrs                                  # List ADRs (software KB plugin)
```

Plugin sub-apps: `pyrite sw` (software), `pyrite zettel` (zettelkasten), `pyrite wiki` (encyclopedia), `pyrite social`.

---

## Reading from the KB

### Search

```bash
pyrite search "migration"                       # Full-text search
pyrite search "migration" --kb=pyrite           # Specific KB
pyrite search "auth*" --type=component          # Prefix + type filter
pyrite search "storage" --tag=architecture      # Tag filter
pyrite search "query" --expand                  # AI-powered query expansion
```

FTS5 syntax: simple terms, `"exact phrase"`, `auth*` prefix, `storage -legacy` exclusion, `AND` boolean.

### Get, list, timeline, tags, backlinks

```bash
pyrite get <entry-id>                           # Search all KBs
pyrite get <entry-id> --kb=pyrite               # Specific KB
pyrite list                                     # All KBs with entry counts
pyrite timeline                                 # All events
pyrite timeline --from=2025-01-01 --to=2025-12-31 --min-importance=7 --limit=20
pyrite tags                                     # All tags with counts
pyrite tags --kb=pyrite --limit=20              # Filter by KB
pyrite backlinks <entry-id> --kb=pyrite         # Entries linking to this one
```

### Plugin read commands

```bash
pyrite sw adrs                                  # List ADRs
pyrite sw backlog                               # List backlog items
pyrite sw standards                             # List standards
pyrite sw components                            # List components
```

---

## Writing to the KB

### Create with core types

```bash
pyrite create --kb=pyrite --type=note --title="My Note" --body="Content here"
pyrite create --kb=pyrite --type=event --title="Release v1.0" --date=2026-02-22 --importance=8
pyrite create --kb=pyrite --type=person --title="Jane Smith" --tags="team,backend"
```

### Create with plugin types (use --field for extension-specific fields)

```bash
# ADR
pyrite create --kb=pyrite --type=adr --title="Use Typer for CLI" \
  --field adr_number=7 --field status=proposed --field date=2026-02-22

# Backlog item
pyrite create --kb=pyrite --type=backlog_item --title="Add caching layer" \
  --field kind=feature --field status=proposed --field priority=high --field effort=M

# Runbook
pyrite create --kb=pyrite --type=runbook --title="Deploy to Production" \
  --field runbook_kind=howto --field audience=developers

# Standard
pyrite create --kb=pyrite --type=standard --title="Error Handling" \
  --field category=python --field enforced=true

# Component
pyrite create --kb=pyrite --type=component --title="Auth Service" \
  --field kind=service --field path=pyrite/auth/ --field owner=alice
```

Entries are saved to the correct subdirectory automatically and indexed.

### Shortcuts and mutations

```bash
pyrite sw new-adr --title "Add Rate Limiting"   # Auto-numbered ADR
pyrite update <entry-id> --kb=pyrite --title="New Title"
pyrite update <entry-id> --kb=pyrite --body="Updated body" --tags="new,tags" --importance=8
pyrite delete <entry-id> --kb=pyrite             # With confirmation
pyrite delete <entry-id> --kb=pyrite --force     # Skip confirmation
```

---

## Admin Commands

### Index management

```bash
pyrite index build                              # Full rebuild (required before search works)
pyrite index build --kb=pyrite                  # Rebuild single KB
pyrite index sync                               # Incremental sync (fast)
pyrite index stats                              # Entry/tag/link counts
pyrite index health                             # Check for stale/missing/unindexed
```

After creating or updating entries, the index updates automatically. Run `index build` when setting up a new environment or after bulk file changes.

### KB management

```bash
pyrite kb list                                  # List configured KBs
pyrite kb add ./path/to/kb --name=myproject --type=software
pyrite kb remove myproject
pyrite kb discover                              # Auto-discover KBs by kb.yaml
pyrite kb validate pyrite                       # Validate KB entries
```

### Other admin

```bash
pyrite repo add ./path --name=myrepo --discover # Repository management
pyrite repo remove myrepo
pyrite auth status                              # Check GitHub auth
pyrite auth whoami                              # Current identity
pyrite auth github-login                        # OAuth flow
pyrite mcp                                      # Start MCP server (stdio, write tier)
pyrite mcp-setup                                # Configure Claude Code integration
```

---

## This Project's KB

The `kb/` directory is a software-type KB:

```
kb/
  kb.yaml              # KB config (name: pyrite, kb_type: software)
  adrs/                # Architecture Decision Records
  designs/             # Design documents
  standards/           # Coding standards and conventions
  components/          # Module/service documentation
  backlog/             # Feature requests, bugs, tech debt
  runbooks/            # How-to guides and procedures
```

### Entry types and fields

| Type | Key Fields | Subdirectory |
|------|-----------|--------------|
| `adr` | adr_number, status, deciders, date | `adrs/` |
| `design_doc` | status, reviewers, date, author | `designs/` |
| `standard` | category, enforced | `standards/` |
| `component` | kind, path, owner, dependencies | `components/` |
| `backlog_item` | kind, status, priority, assignee, effort | `backlog/` |
| `runbook` | runbook_kind, audience | `runbooks/` |

Core types also available: `note`, `person`, `organization`, `event`, `document`, `topic`, `relationship`, `timeline`.

### Status enums

- **ADR**: `proposed` -> `accepted` -> `deprecated` | `superseded`
- **Backlog**: `proposed` -> `accepted` -> `in_progress` -> `done` | `wont_fix`
- **Backlog priority**: `critical`, `high`, `medium`, `low`
- **Backlog effort**: `XS`, `S`, `M`, `L`, `XL`

---

## Project Processes

### Backlog Management

The backlog lives in `kb/backlog/` with three zones:

| Location | Contents |
|----------|----------|
| `kb/backlog/*.md` | Active priority items (~top 30) |
| `kb/backlog/done/` | Completed items |
| `kb/backlog/future-ideas/` | Lower-priority items for later |

**`kb/backlog/BACKLOG.md`** is the single prioritized index — a numbered list linking to every item. Always keep it in sync.

### When completing a feature:

1. Set `status: completed` in the item's YAML frontmatter
2. Move the file from `kb/backlog/` to `kb/backlog/done/`
3. Update `BACKLOG.md` — move item to the Completed section
4. If the work revealed new tech debt, cleanup needs, or follow-on features:
   - Create new `backlog_item` files for each
   - Place in `kb/backlog/` if high priority, or `kb/backlog/future-ideas/` if low
   - Add to `BACKLOG.md` in the correct priority position
5. Re-number priorities in `BACKLOG.md` if needed to keep the list clean

### When promoting a future idea:

1. Move the file from `future-ideas/` to `kb/backlog/`
2. Add it to `BACKLOG.md` in the right priority position

### Backlog item file format:

```yaml
---
type: backlog_item
title: "Human-readable title"
kind: feature | improvement | bug
status: proposed | in_progress | completed
priority: high | medium | low
effort: S | M | L | XL
tags: [relevant, tags]
---

Description of the work, context, approach, and dependencies.
```
