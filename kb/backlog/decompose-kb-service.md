---
id: decompose-kb-service
type: backlog_item
title: "Decompose KBService God Object into focused sub-services"
kind: enhancement
status: proposed
priority: medium
effort: XL
tags: [architecture, refactoring]
epic: epic-release-readiness-review
---

## Problem

`KBService` is 1619 lines with 30+ pass-through methods delegating to sub-services it internally instantiates. 26 files import it — every endpoint, the CLI, the MCP server. Any consumer that only needs graph queries pulls the full dependency tree.

## Fix

Extract `EntryService` (CRUD), register sub-services (GraphService, ExportService, etc.) via DI so consumers import what they need directly. Keep a slim `KBService` or `KBInfoService` for orient/stats. This is a large refactor that touches most endpoint modules.
