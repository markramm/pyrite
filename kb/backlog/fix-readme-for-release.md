---
id: fix-readme-for-release
type: backlog_item
title: "Fix stale counts and tables in README, CLAUDE.md, and getting-started"
kind: bug
status: proposed
priority: high
effort: S
tags: [docs, release]
epic: epic-release-readiness-review
---

## Problem

Multiple stale numbers across documentation:
- MCP tool counts: says 14/6/4, reality is 23/11/8 (README + getting-started)
- Test count: says 1468, actual ~2,506 (README + CLAUDE.md)
- ADR count: says 16, actual 22 (README)
- Extension points: says 15/16, actual 18 (README)
- Extensions table: lists `task` as extension (is core), missing `journalism-investigation`
- CLAUDE.md extensions list: missing cascade, journalism-investigation

## Fix

Update all counts to current values. Fix extensions table. Single pass through README.md, CLAUDE.md, and docs/getting-started.md.
