---
id: epic-release-readiness-review
type: backlog_item
title: "Epic: Release Readiness Review Findings"
kind: epic
status: proposed
priority: high
effort: XL
tags: [epic, security, quality, docs, release]
---

## Summary

Comprehensive review conducted 2025-03-25 across 5 parallel agents: code review, architecture review, test & QA review, frontend design review, and docs & KB review. This epic tracks all findings organized by priority.

## Critical — Security (XSS)

- `fix-xss-site-cache-title` — Title not HTML-escaped in `<title>` and og:title tags
- `fix-xss-site-cache-search-widget` — Inline search widget injects e.title into innerHTML without escaping
- `fix-xss-site-cache-markdown-links` — Markdown links pass through unescaped (javascript: URLs possible)
- `fix-xss-chat-sidebar` — `{@html renderCitations()}` doesn't escape surrounding text
- `fix-xss-search-highlight` — `{@html highlightSnippet()}` doesn't HTML-escape snippet before adding mark tags
- `fix-yaml-injection-export` — Export service builds YAML frontmatter via string interpolation

## High — Code Quality

- `fix-n-plus-one-site-cache` — render_all() issues 3 DB queries per entry in loop
- `fix-blocking-io-site-cache-render` — render_all() blocks async event loop
- `fix-entry-id-path-traversal` — Entry ID used as filename without sanitization in export + site cache
- `extract-site-cache-templates` — Move 807 lines of inline HTML/CSS/JS to Jinja2 templates
- `fix-sidebar-derived-bug` — userInitials() called as function but is $derived value
- `deduplicate-site-css` — 80+ lines duplicated between site_cache.py and static_search_page.py

## High — Documentation

- `fix-readme-mcp-counts` — MCP tool counts say 14/6/4, reality is 23/11/8
- `fix-readme-stats` — Test count (1468→2506), ADR count (16→22), extension points (15→18)
- `fix-readme-extensions-table` — task listed as extension (is core), journalism-investigation missing
- `fix-backlog-stale-statuses` — 14 backlog items marked done in BACKLOG.md but frontmatter says proposed
- `update-changelog-post-020` — 43 commits since 0.20.0 with substantial features undocumented

## Medium — Architecture

- `decompose-kb-service` — KBService is 1619-line God Object with 30+ pass-through methods
- `add-adr-site-cache` — No ADR for site-cache/static-HTML decision
- `document-undocumented-services` — 9 services have no component docs
- `fix-swallowed-exceptions-admin` — Site cache render failures logged at debug level
- `fix-duplicate-auth-service` — AuthService instantiated twice in manage_kb_permission
- `update-adr-0002-plugin-points` — Says 5 integration points, actual is 18

## Medium — Frontend

- `harmonize-app-site-fonts` — App and static site use inverted font stacks (jarring transition)
- `fix-quickswitcher-navigation` — Uses window.location.href instead of goto()
- `add-accessibility-labels` — KBSwitcher, ThemeToggle, sidebar toggle missing aria labels
- `add-offline-indicator` — No visual indicator when WebSocket disconnects
- `normalize-starred-store` — Uses closure pattern inconsistent with all other class-based stores

## Lower — Maintenance

- `fix-imports-in-loops` — import inside loop in static.py, repeated import re in site_cache.py
- `remove-dead-code-site-cache` — Dead limit=1 query in render_all
- `fix-empty-state-light-mode` — EmptyState/ErrorState hardcoded for dark mode
- `extract-entry-page-toolbar` — entries/[id]/+page.svelte is 393 lines, toolbar should be component
- `commit-export-renderers` — renderers/ package and export_commands.py are untracked
