---
id: entry-factory
title: Entry Factory
type: component
kind: module
path: pyrite/models/factory.py
owner: core
tags:
- core
- models
---

Single dispatch point for entry construction. Routes all types through get_entry_class() and from_frontmatter(). Unknown types fall back to GenericEntry. Ensures all entries are constructed consistently regardless of source (CLI, API, MCP).
