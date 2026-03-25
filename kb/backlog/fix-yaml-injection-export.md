---
id: fix-yaml-injection-export
type: backlog_item
title: "Fix YAML injection in export service frontmatter generation"
kind: bug
status: proposed
priority: critical
effort: S
tags: [security, export]
epic: epic-release-readiness-review
---

## Problem

`export_service.py:75-83` — Builds YAML frontmatter by string interpolation (`f"{key}: {val}"`) without quoting values. Titles with `: `, `#`, or newlines can break or inject additional frontmatter fields.

## Fix

Use `pyrite.utils.yaml.dump_yaml` or `yaml.safe_dump` for frontmatter generation instead of string interpolation.
