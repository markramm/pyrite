---
id: web-ui-kb-orientation-page
title: "Web UI KB orientation page"
type: backlog_item
tags: [web, ux, onboarding]
kind: feature
status: done
priority: high
effort: M
---

## Problem

When a visitor selects a KB in the web UI, they land on the entries list with no context about what the KB is, what it contains, or how to navigate it. The CLI has `pyrite orient` which generates a narrative overview, but human users in the GUI get no equivalent orientation.

## Solution

Add a `/orient` or `/kb/:name` page to the web UI that renders the KB's orientation — description, entry types with counts, key entries, guidelines, and cross-KB links. This should be the default landing when clicking a KB name from the dashboard KB list.

### What to show

- KB name, description, and type (from kb.yaml)
- Entry type breakdown with counts (similar to dashboard donut but per-KB)
- KB guidelines (contributing, quality) rendered as markdown
- Key entries (highest importance or most linked) as clickable cards
- Cross-KB links if any exist
- Quick actions: Browse entries, View graph, Search this KB

### Implementation

- Reuse the orient logic from `pyrite/cli/__init__.py` or `pyrite/services/kb_service.py`
- New API endpoint: `GET /api/kbs/:name/orient` returning structured orient data
- New SvelteKit route: `/orient?kb=:name` or `/kb/:name`
- The dashboard KB list cards should link here instead of to `/entries?kb=:name`

## Success criteria

- Clicking a KB name from the dashboard shows a rich orientation page
- The page renders in under 2 seconds
- All content from kb.yaml guidelines is visible
- Entry type breakdown matches the actual indexed content
