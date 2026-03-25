---
id: update-adr-0002-plugin-points
type: backlog_item
title: "Update ADR-0002 to reflect 18 plugin integration points"
kind: enhancement
status: proposed
priority: medium
effort: XS
tags: [docs, adr]
epic: epic-release-readiness-review
---

## Problem

ADR-0002 says "5 integration points" but the actual plugin protocol has grown to 18 unique methods including `get_db_tables`, `get_hooks`, `get_kb_presets`, `get_field_schemas`, `get_type_metadata`, `get_collection_types`, `get_validators`, `get_migrations`, `get_protocols`, `get_orient_supplement`, `get_rubric_checkers`, and `get_workflows`.

## Fix

Update ADR-0002 with an addendum documenting the evolution from 5 to 18 integration points and the current protocol surface.
