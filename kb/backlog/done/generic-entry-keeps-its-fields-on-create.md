---
id: generic-entry-keeps-its-fields-on-create
title: "A kb.yaml-only type keeps every field on create, bulk create and import (#386)"
type: backlog_item
tags:
- bug
- data-loss
kind: bug
status: done
assignee: agent:pyrite-worker
priority: high
effort: S
milestone: "0.26"
---

See GitHub #386 for the reproduction and the architect's groom comment. `build_entry`'s GenericEntry branch keeps only tags, summary and metadata, so every other field given to `KBService.create_entry` or `bulk_create_entries` is silently dropped, and schema validation never sees it.
