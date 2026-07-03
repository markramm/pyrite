---
id: plugin-type-resolution-scoping
type: backlog_item
title: "Scope plugin entry-type resolution by KB type: global person→actor remapping is order-dependent and surprises every KB"
kind: improvement
status: proposed
priority: medium
effort: L
created: "2026-07-03"
tags: [plugins, extensions, architecture, audit-2026-07]
links:
- target: extension-registry
  relation: related
  kb: pyrite
---

## Problem

`KBService._resolve_entry_type` (kb_service.py:180-200) iterates ALL
installed plugins' entry types and rewrites requested type names in
EVERY KB, regardless of kb_type: with the cascade extension
installed, `create_entry(type="person")` becomes `actor` in a
generic research KB (this is the mechanism behind the 2026-07-02
docs-audit finding where a fresh tutorial KB immediately failed
`index health` with `undeclared_types` warnings on its own tutorial
entries). Multiple plugins subclass `EventEntry`, so `type="event"`
resolves nondeterministically (dict-iteration order, last-writer-wins
merge at registry.py:199-210, WARN only).

The KB-type scoping machinery EXISTS (`registry.py:508-576`) but is
wired only for hooks and validators — not entry types, DB
tables/columns, or migrations. Related blast-radius items from the
same audit: `PluginContext` hands plugins the live db with
unrestricted DDL (`plugins/context.py:31-36`); the `social` extension
writes via IndexManager/KBRepository directly, bypassing KBService
hooks/validators; `mcp_server.py:35-77` `_UPDATE_FIELDS` leaks
extension vocabulary (`sender`, `funder`, `claim_status`) into core.

Tolerable with 6 first-party extensions; not tolerable the day a
third party writes one — a prerequisite for [[extension-registry]].

## Decision (2026-07-03, Mark): compat-check failures FAIL CLOSED

From the fail-open sweep's site #6 investigation:
`_plugin_matches_kb_type` (registry.py:508-521) already logs its
failure — the open question was the `return True` fail-open. Decided:
**fail closed** — a plugin whose compatibility check errors is
SKIPPED for that KB. Rationale: the check reads static plugin
declarations (errors are structural, not transient), while the blast
radius of a wrongly-applied plugin is global type remapping (the
person→actor tutorial-KB failure). Additionally, per
[[in-band-degradation-signaling]]: the skip must surface in-band
(warnings array / stderr), not log-only — logs are invisible to
CLI/MCP agents.

## Fix

1. Wire the existing KB-type scoping into entry-type resolution:
   a plugin's type remaps apply only in KBs whose kb_type the plugin
   declares. Core type names resolve to core classes everywhere else.
2. Deterministic conflict handling: two plugins claiming the same
   type name in the same scope = hard error at load, not
   last-writer-wins WARN.
3. Move `_UPDATE_FIELDS` extension vocabulary behind a plugin
   contribution (plugins declare their updatable fields).
4. (Stretch / may split) Narrow PluginContext: schema-scoped DDL,
   and route extension writes through KBService so hooks/validators
   always run.

## Acceptance criteria

- A generic research KB with all 6 extensions installed:
  `create_entry --type person` yields `person`, and the
  getting-started tutorial passes `index health` clean.
- Load-time hard error test for same-scope type conflicts.
