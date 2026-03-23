---
id: quartz-static-site-export
title: "Quartz static site export for KB publishing"
type: backlog_item
tags:
- export
- static-site
- publishing
- quartz
links:
- target: cascade-timeline-static-export-for-viewer-consumption
  relation: related
  kb: pyrite
kind: feature
status: proposed
priority: medium
effort: M
---

## Problem

KB owners who want public discoverability (Google indexing) and zero-cost hosting have no way to publish a Pyrite KB as a static site without running a Pyrite server instance. Investigation KBs (e.g. tcp-internal-kb) benefit from being browsable by the public without requiring infrastructure.

## Solution

Add a Quartz renderer (`pyrite/renderers/quartz.py`) and a `pyrite export site` CLI command that exports a KB as a Quartz-compatible content directory, ready for GitHub Pages deployment.

[Quartz](https://quartz.jzhao.xyz/) is a static site generator (11.5K GitHub stars, active maintenance) purpose-built for markdown knowledge bases. It provides wikilink resolution, backlinks, interactive graph visualization, tag pages, folder navigation, and client-side full-text search — all out of the box from markdown+YAML frontmatter.

## Why Quartz

- **Wikilink/backlink/graph trifecta** — matches Pyrite's relationship-heavy KB model
- **YAML frontmatter native** — Pyrite's `title`, `tags`, `date` fields work directly; unknown fields are preserved
- **Zero hosting cost** — GitHub Pages, Cloudflare Pages, or Netlify
- **Google indexable** — static HTML with good SEO defaults
- **Obsidian-compatible link syntax** — close to Pyrite's existing `[[entry-id]]` format

## Scope

### Renderer (`pyrite/renderers/quartz.py`)

Entry-level rendering:
- Emit standard YAML frontmatter (`title`, `tags`, `date`, `description`, `aliases`)
- Add `aliases: [entry-id]` for reliable wikilink resolution
- Normalize link syntax: `[[kb:entry-id]]` → `[[entry-id]]`, strip spaces around pipes
- Strip transclusion parameters: `![[id]]{ view: "table" }` → `![[id]]`
- Pass body markdown through mostly unchanged
- Optionally render type-specific frontmatter as a metadata table at the top of the body (status badges, priority, etc.) since Quartz doesn't surface custom frontmatter in UI

Site-level output:
- Write entries into `content/` preserving type-based folder structure
- Generate `content/index.md` landing page from KB description
- Generate folder `index.md` files for each type directory
- Support entry filtering by type and status

### CLI command

```bash
# Export entire KB as Quartz content
pyrite export site -k tcp-internal-kb -o ./published-site --format quartz

# With filtering
pyrite export site -k tcp-internal-kb -o ./published-site --format quartz \
    --exclude-types backlog_item,note \
    --exclude-status draft,done

# First-time setup: scaffold a complete Quartz project
pyrite export site -k tcp-internal-kb -o ./published-site --format quartz --init
```

### `--init` scaffolding (one-time)

When `--init` is passed, generate a minimal Quartz project around the content:
- `package.json` with quartz dependency
- `quartz.config.ts` with sensible defaults (title from KB name, graph enabled, backlinks enabled)
- `quartz.layout.ts` with explorer + graph + backlinks layout
- `.github/workflows/deploy.yml` for GitHub Pages CI

Subsequent exports only update `content/`.

## What's NOT in scope

- Incremental export (full wipe-and-rewrite of `content/` is fine for CI)
- Custom Quartz plugins or themes
- Semantic search (Quartz only supports client-side Flexsearch)
- Dataview-style dynamic queries
- Parameterized transclusion rendering

## Integration points

- Follows existing renderer pattern: `pyrite/renderers/quartz.py` alongside `notebooklm.py`
- New `site` subcommand on `export_app` in `pyrite/cli/export_commands.py`
- Uses `ExportService` for git-push workflow (`export_kb_to_repo` already supports clone→export→commit→push)

## Success criteria

- `pyrite export site --init` produces a buildable Quartz project
- `npx quartz build` succeeds on the exported content
- Wikilinks between entries resolve correctly
- Graph view shows entity relationships
- Tag pages and folder navigation work
- GitHub Pages deployment works via the generated workflow
