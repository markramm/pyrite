---
id: fix-yaml-injection-export
title: "Fix YAML injection in export service frontmatter generation"
type: backlog_item
tags: [security, export]
kind: bug
status: done
priority: critical
effort: S
---

## Problem

`export_service.py:75-83` — Builds YAML frontmatter by string interpolation (`f"{key}: {val}"`) without quoting values. Titles with `: `, `#`, or newlines can break or inject additional frontmatter fields.

## Fix

Use `pyrite.utils.yaml.dump_yaml` or `yaml.safe_dump` for frontmatter generation instead of string interpolation.
