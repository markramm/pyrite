---
id: shared-frontmatter-split-utility
type: backlog_item
title: "One shared frontmatter-split function; retire 8+ hand-rolled copies (one already divergently buggy)"
kind: tech_debt
status: proposed
priority: medium
effort: S
created: "2026-07-03"
tags: [refactor, frontmatter, duplication, audit-2026-07]
---

## Problem

A canonical YAML util exists (`pyrite/utils/yaml.py`, ruamel
round-trip, raises FrontmatterError) but there is no shared
"split frontmatter from body" function. The
`startswith("---")`/`split("---", 2)` pattern is hand-rolled in 8+
places: `storage/repository.py:250`, `services/kb_service.py:367,
1318` (two copies in one file), `services/template_service.py:60`,
`cli/entry_commands.py:218`, `cli/schema_commands.py:61`,
`formats/importers/markdown_importer.py:41`,
`extensions/cascade/.../hooks.py:72`,
`extensions/journalism-investigation/.../known_entities.py:84`.

Already-divergent copy with real bugs:
journalism-investigation's `entry_types.py:30` `_base_kwargs` is a
drifted copy of `pyrite/models/base.py:79` — it drops
`_schema_version` (silent round-trip loss for 11 entry types) and
replaces `safe_int` importance parsing with raw `int()` (ValueError
on malformed frontmatter). Also `utils.py:7 parse_meta` duplicates
core `pyrite/utils/metadata.py:7` less robustly, with a dead alias
at `plugin.py:1004`.

## Fix

- Add `split_frontmatter(text) -> (frontmatter_str|None, body)` (and
  a parsed variant) to `pyrite/utils/yaml.py`; handle the edge cases
  once (no frontmatter, `---` in body, CRLF, empty frontmatter).
- Migrate the 8+ call sites; delete the local copies.
- Fix journalism-investigation `_base_kwargs` divergence (restore
  `_schema_version` passthrough + `safe_int`) — or better, import
  the core helper.
- Extension authors get it via the same util (document in
  extension-development standard).

## Acceptance criteria

- `grep -rn 'split("---"' pyrite/ extensions/` returns only the
  shared util.
- Round-trip test: an entry with `_schema_version` survives
  journalism-investigation type instantiation.
