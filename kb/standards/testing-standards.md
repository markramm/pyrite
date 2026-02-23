---
type: standard
title: "Testing Standards"
category: testing
enforced: true
tags: [testing, pytest]
---

## Framework
- pytest with rich output
- Pre-commit hook runs full suite on every commit

## Test Structure for Extensions (proven 8-section pattern)
1. **TestPluginRegistration** — verify name, all capabilities in registry (use `in` not `len ==`)
2. **TestEntryType** — defaults, to_frontmatter, from_frontmatter, roundtrip_markdown
3. **TestValidators** — one test per rule (positive + negative), test ignores-other-types
4. **TestHooks** — direct call + registry.run_hooks tests
5. **TestWorkflows** — each transition allowed/blocked, requires_reason
6. **TestDBTables** — definition checks + actual SQLite creation in tmpdir
7. **TestPreset** — structure, directories, validation rules
8. **TestCoreIntegration** — entry_class_resolution, entry_from_frontmatter, multi-plugin coexistence

## Key Rules
- Use `in` checks not exact counts for registry assertions (other installed plugins affect counts)
- Each test class should create a fresh PluginRegistry to avoid cross-test contamination
- Use try/finally when patching `reg_module._registry` to guarantee restoration
