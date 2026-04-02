---
id: kb-preset-application-on-create
type: backlog_item
title: "Apply plugin KB presets (kb.yaml + templates) when creating a new KB"
kind: bug
status: done
priority: high
effort: M
tags: [plugins, kb-creation, presets]
---

## Problem

When a user creates a new KB using a plugin preset (e.g. journalism-investigation), the KB is created as a bare directory with no `kb.yaml` types section and no `_templates/` directory. The user gets no entity types, no schemas, and no guidance on what types exist.

Plugin presets define rich type configurations (16 types for journalism-investigation) but these are never written to the KB on creation.

## Solution

When creating a KB with a `kb_type` that matches a registered plugin preset:

1. Generate and write `kb.yaml` from the preset's types/description
2. Create `_templates/` directory with entry templates for each type (frontmatter skeleton + body guidance)
3. Create subdirectories defined in the preset (entities/, events/, sources/, connections/, etc.)

The preset data already exists in the plugin — it just needs to be materialized into the KB directory at creation time.

## Reported By

User testing journalism-investigation plugin (2026-03-31).
