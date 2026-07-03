---
id: db-registered-kbs-never-get-their-kb-yaml-schema-loaded
title: DB-registered KBs never get their kb.yaml schema loaded
type: backlog_item
tags:
- bug
- kb-registry
- dual-registry
importance: 5
kind: bug
status: done
priority: medium
effort: S
rank: 0
---

## Investigation result: NOT a bug, closing

`pyrite/config.py`'s `load_config()` loop (`for kb in
config.knowledge_bases: kb.load_kb_yaml()`) is confirmed structurally
unable to reach DB-registered KBs (runs before any caller's
`merge_registered_kbs()` call in every code path). Investigated
whether this actually breaks anything for DB-only KBs.

**Verified directly**: `KBConfig.kb_schema` (config.py:76-87) is a
lazy property that loads `self.path / "kb.yaml"` on first access,
completely independent of `load_config()`'s eager pre-warm loop. A
DB-only KB registered via `register_db_kbs()` (the same path
`merge_registered_kbs()` uses) correctly loads its kb.yaml schema,
including `required` fields, on first schema access -- confirmed with
a live reproduction: registered a DB-only KB with a kb.yaml requiring
`title` + `owner`, accessed the schema without ever going through the
eager loop, got the correct required-fields list back.

So `load_config()`'s loop is a config.yaml-only pre-warming
optimization (avoids a lazy-load stall on first schema access for
config.yaml KBs specifically), not a correctness-load-bearing step.
DB-only KBs pay a first-access lazy-load cost but get the exact same
correct schema. No functional gap exists here.

Closing without a code change -- the site was flagged during the
all_kbs() sweep audit but doesn't need one.
