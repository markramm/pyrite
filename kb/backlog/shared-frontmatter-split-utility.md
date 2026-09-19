---
id: shared-frontmatter-split-utility
type: backlog_item
title: "One shared frontmatter-split function; retire 8+ hand-rolled copies (one already divergently buggy)"
kind: tech_debt
status: proposed
priority: medium
effort: S
created: "2026-07-03"
tags: [refactor, frontmatter, duplication, audit-2026-07, quality]
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

## Groom 2026-09-20 (retro 6 — the quality theme)

**Why now:** #187 (merged 2026-09-19) found and deleted **five** hand-rolled copies of `Entry._base_kwargs`, each drifting differently, after a registry-wide conformance test went red on 59 entry types. This item named the journalism copy's drift (`_schema_version` dropped, raw `int()` on `importance`) in July; it was fixed only when the duplication class was attacked as a class. The frontmatter *split* is the same class — 8+ copies of `startswith("---")`/`split("---", 2)` — and the same failure is waiting (a file whose body contains `---` on its own line, a CRLF file, a BOM, a frontmatter block with no trailing newline: each copy answers differently today).

**Acceptance**
1. One function, `split_frontmatter(text) -> tuple[dict, str]` (or `(raw_yaml, body)` plus the existing loader — decide once, say why in the docstring), in `pyrite/utils/yaml.py` beside the round-trip loader, raising `FrontmatterError` on a malformed block. It is the *only* implementation: `grep -rn 'split("---"\|startswith("---")' pyrite/ extensions/` returns hits only inside that function and its tests.
2. Every listed call site (`storage/repository.py`, `services/kb_service.py` ×2, `services/template_service.py`, `cli/entry_commands.py`, `cli/schema_commands.py`, `formats/importers/markdown_importer.py`, `extensions/cascade/.../hooks.py`, `extensions/journalism-investigation/.../known_entities.py`) calls it; the journalism `utils.py:parse_meta` duplicate and its dead alias at `plugin.py` are deleted in favour of `pyrite/utils/metadata.py`.
3. A conformance test over a fixed corpus of edge files — body containing `---` on its own line; `---` inside a fenced code block; CRLF line endings; a UTF-8 BOM; no trailing newline after the closing `---`; an empty frontmatter block; no frontmatter at all; a frontmatter block that is not a mapping — asserts every former call site's *observable* behaviour is unchanged where it was correct and identical across surfaces where it differed (RED first: write the corpus, run it through each copy via its public entry point — `KBRepository.load_entry_from_file`, `pyrite import`, the template service, the two extensions' hooks — and record which copies disagree; that table goes in the PR body).
4. `Regimes:` the eight corpus files above × the public entry points; plus the `pyrite/models/base.py` `from_markdown` path, which must keep using the same function.
5. CHANGELOG line under Fixed naming the divergent cases that now agree.

**Touches** — existing: the nine files above, `pyrite/utils/yaml.py`, `extensions/journalism-investigation/src/pyrite_journalism_investigation/{utils.py,plugin.py}`, `CHANGELOG.md`; new: `tests/test_split_frontmatter_conformance.py`, `tests/fixtures/frontmatter_split/*.md`.
**Sequence:** after #173 and #175 merge (both edit `pyrite/models/base.py` / the round-trip tests; this must not race them). Independent of #180/#161/#145/#140.
**Model:** Sonnet. **heavy:** no. **Cold read:** yes — `storage/` and a file-format surface. **Out of scope:** changing what any correct case returns; the YAML loader itself; `_base_kwargs` (done in #187).
