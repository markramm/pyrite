---
id: enhance-orient-for-software-type-kbs-with-kanban-and-architecture-context
title: Enhance orient for software-type KBs with kanban and architecture context
type: backlog_item
tags:
- extension:software-kb
- dx
- mcp
- software
- kanban
- agents
kind: enhancement
effort: M
---

## Problem

The orient command (kb_orient MCP tool, pyrite orient CLI) provides generic KB stats — type counts, top tags, 5 recent entries, schema info. For a software-type KB, this misses critical context an agent needs to start working:

- No kanban board view (what is in each lane, WIP limit status)
- No component list or architecture overview
- No in-progress items or who has what claimed
- No recent ADRs or key architectural decisions
- No review queue status

An agent entering a software KB gets told "there are 203 backlog items" but not "there are 2 items in progress assigned to X, 3 in review, and the top priority unclaimed item is Y."

## Solution

For software-type KBs, orient should additionally return:

- Board summary: lane counts and WIP status (from sw_board logic)
- In-progress items with assignees
- Review queue summary
- Top 5 components (by link count or recent activity)
- Recent accepted ADRs (last 3-5)
- Recommended next item (from sw_pull_next logic)

This could be implemented as a plugin hook on orient, or by having the orient command detect kb_type=software and call into the software-kb plugin for supplementary data.

