---
id: awesome-plugins-page
title: "Awesome Plugins Page"
type: backlog_item
tags:
- docs
- plugins
- discovery
- launch
kind: feature
priority: medium
effort: XS
status: planned
links:
- plugin-repo-extraction
- extension-registry
- roadmap
---

## Problem

Once plugins are extracted to separate repos, users need a way to discover them. The full extension registry (#84) is 0.13 scope. We need a lightweight discovery mechanism for launch.

## Solution

A curated "Awesome Pyrite Plugins" page in the Pyrite repo. Simple markdown file listing available plugins with:

- Name and one-line description
- Install command (`pip install pyrite-<name>`)
- Link to repo
- What it adds (entry types, MCP tools, presets)
- Status badge (official vs community)

### Location

`docs/plugins.md` or `PLUGINS.md` in the repo root. Linked from README.

### Content

**Official Plugins** (shipped with Pyrite, maintained by core team):
- `pyrite-software-kb` — ADRs, components, backlog, standards for software projects
- `pyrite-zettelkasten` — CEQRC maturity workflow, zettel types, Luhmann IDs
- `pyrite-encyclopedia` — Articles, reviews, voting, quality-gated validation
- `pyrite-social` — Engagement tracking, voting, reputation
- `pyrite-cascade` — Timeline events, migration tools

**Community Plugins** section (empty initially, with instructions for listing).

**Building Your Own** — link to the plugin writing tutorial.

## Prerequisites

- Plugin repo extraction (#107) — so there are repos to link to

## Success Criteria

- Page exists and is linked from README
- All 5 official plugins listed with install commands
- "Building Your Own" section links to tutorial
- Community contribution instructions included
