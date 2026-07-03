---
id: collapse-kb-registry-to-one-source-of-truth
title: Collapse KB registry to one source of truth (finish knowledge_bases -> all_kbs() sweep)
type: backlog_item
tags:
- tech-debt
- config
- index
links:
- target: epic-shared-instance-readiness
  relation: subtask_of
  kb: pyrite
importance: 5
kind: tech_debt
status: proposed
priority: medium
effort: M
rank: 0
---

## Problem

KBs live in two registries: config.yaml (`config.knowledge_bases`) and the DB `kb` table (`pyrite kb add`, reachable only via `get_kb()`/`all_kbs()` through `_db_kb_cache`). Every loop over `config.knowledge_bases` silently skips DB-registered KBs — the bug class `all_kbs()`'s own docstring warns about.

The index/MCP sites were fixed (index.py get_index_stats/check_staleness/check_health x3, mcp_server.py _list_edge_types — see tests/test_index_covers_db_registered_kbs.py). Remaining direct-iteration sites to audit and migrate (some may be intentionally config-only, e.g. seeding and worktree patching):

- pyrite/config.py:843
- pyrite/ui/data.py:57, 166
- pyrite/cli/schema_commands.py:468, 479
- pyrite/cli/search_commands.py:105 (error-message KB list)
- pyrite/services/sitemap_service.py:43
- pyrite/services/kb_registry_service.py:34
- pyrite/services/site_cache.py:67
- pyrite/services/ephemeral_service.py:56, 74, 89
- pyrite/services/qa_service.py:157
- pyrite/services/kb_service.py:125, 172

## Proposal

1. Audit each site: config-only semantics intentional, or silent-skip bug?
2. Migrate bug sites to `all_kbs()` with a regression test each (fixture pattern in tests/test_index_covers_db_registered_kbs.py).
3. Longer term: make `knowledge_bases` private or rename, so enumeration goes through `all_kbs()` by default and config-only access is the explicit opt-in.

## Decision (2026-07-03): ADR-0029 governs this ticket

The design discussion concluded and is recorded in [[adr-0029]]
(Libraries, KB Lifecycles, and Runtime State). The 0.25 scope of
THIS ticket, per the ADR's phasing:

1. Finish the `all_kbs()` sweep (the Problem list above), regression
   test per site.
2. Consolidate to ONE YAML: the merged file becomes a valid library
   file named `default` (`library:` header, full KB list, `db:`
   path); `~/kb/config.yaml` migrated in and retired; `~/.pyrite/`
   owns the registry; stale test registrations dropped during
   migration.
3. `pyrite kb create` / `kb add` WRITE the library YAML (ruamel
   round-trip, file lock + atomic rename); the DB `kb` table is
   demoted to a derived cache rebuilt from the file at load, with
   read-back verification.
4. Load-time validation: a malformed library file fails with a good
   error, never silent divergence.

Library switching, per-library DBs, readonly mounts, claim leases,
and ephemeral leasing are 0.26 (see the ADR) — do NOT implement here.

## Progress

- [x] **Item 1 (sweep) — audited and fixed** (2026-07-03). Each of
  the ~10 listed sites, resolved:
  - **`sitemap_service.py:43`** — bug, fixed. `_public_kb_names()`
    used `config.knowledge_bases`; a DB-only KB with
    `default_role='read'` could never appear in the public sitemap.
    Root-caused one layer deeper: `merge_registered_kbs`'s raw SQL
    SELECT never fetched `default_role` at all (real DB column,
    `kb` table, migration v-whatever added it for per-KB access
    control), and `config.register_db_kbs()`'s dict→KBConfig mapping
    didn't pass it through even when present — so this needed a
    two-layer fix (kb_ops.py's SELECT + config.py's KBConfig
    construction) before the sitemap fix alone would have worked.
    Tests: `test_merges_default_role_from_db` (merge layer),
    `test_includes_db_only_public_kb` (sitemap layer). Both RED
    (via `git stash`) before GREEN.
  - **`schema_commands.py:486,497`** — bug, fixed. Both
    schema-detection loops (for `--changed` and positional `files`)
    used `config.knowledge_bases`, so a DB-only KB's `kb.yaml`
    required-field rules were silently skipped (schema stayed
    `None`, and `validate_entry`'s required-fields check only runs
    `if schema:`) even though the SAME function's file-resolution
    (`_get_git_changed_md_files`) already correctly used
    `config.all_kbs()`. New test file
    `test_schema_validate_db_only_kb.py`: a DB-only KB with a
    required `owner` field, entry missing it — asserted `exit_code
    != 0` and the error names `owner`. RED confirmed (pre-fix:
    "0 errors, 1 clean").
  - **`search_commands.py:126`** — bug, fixed. The `KB_NOT_FOUND`
    error's "known KBs: ..." suggestion used `config.knowledge_bases`,
    so a DB-only KB was invisible in the typo-correction hint even
    though it's real and searchable.
    `test_search_kb_not_found_suggestion_includes_db_only_kb`. RED
    confirmed.
  - **`site_cache.py:67`** — bug, fixed. `render_all()`'s KB
    enumeration for the static-site export used
    `config.knowledge_bases`; a `kb add`-registered KB would never
    get exported/rendered. `test_includes_db_only_kb`. RED confirmed.
  - **`qa_service.py:157`** — bug, fixed. `validate_all()` used
    `config.knowledge_bases`; a DB-only KB would silently skip QA
    validation entirely. `test_validate_all_includes_db_only_kb`. RED
    confirmed.
  - **`kb_service.py:126,172`** — bug, fixed (2 sites). `list_kbs()`'s
    non-registry fallback path (used when `KBService` is constructed
    without a `_registry`) and `get_entry()`'s "search all KBs"
    fallback (when no `kb_name` given) both used
    `config.knowledge_bases`. `test_list_kbs_includes_db_only_kb_when_no_registry`,
    `test_get_entry_searches_db_only_kb`. Both RED confirmed.
  - **`ephemeral_service.py:56,74,89`** — audited, NOT a bug,
    intentionally config-only. `create_ephemeral_kb()` explicitly
    calls `self.config.add_kb(kb)` + `save_config(self.config)`, so
    every ephemeral KB this service creates always lands in
    `knowledge_bases` by construction — there is no DB-only ephemeral
    KB for these three sites to silently skip. Left unchanged.
  - **`kb_registry_service.py:34`** — audited, NOT a bug,
    intentionally config-only. `seed_from_config()`'s explicit job is
    "upsert config.yaml KBs into the DB" — iterating `all_kbs()`
    here would try to re-seed already-DB-registered KBs back into
    themselves and could incorrectly reset their `source` column
    from `"user"` back to `"config"`. Left unchanged.
  - **`config.py:843`** — audited, confirmed NOT a bug on
    investigation. This loop (`kb.load_kb_yaml()` for each KB) runs
    inside `load_config()`, which always returns BEFORE any caller
    has queried the DB and called `merge_registered_kbs()` — so
    `config._db_kb_cache` is unconditionally empty at this point in
    every call path, meaning a mechanical `knowledge_bases` →
    `all_kbs()` swap here would be a no-op. Investigated whether this
    actually breaks anything: `KBConfig.kb_schema` is a *lazy*
    property that loads `kb.yaml` from disk on first access,
    completely independent of this eager loop. Verified live: a
    DB-only KB's schema (including `required` fields) loads correctly
    on first access with zero dependency on this loop ever running.
    The loop is a config.yaml-only pre-warming optimization, not a
    correctness-load-bearing step — DB-only KBs pay a first-access
    lazy-load cost but get the identical correct schema. Filed, then
    closed same-session after verification:
    [[db-registered-kbs-never-get-their-kb-yaml-schema-loaded]].
  - **`ui/data.py:57,166`** — audited, deliberately left unfixed.
    This is the legacy Streamlit UI (`ui_streamlit.py`), superseded
    by the SvelteKit `web/` frontend per CLAUDE.md's architecture
    section. `git log` shows zero commits to this file since the very
    first commit (v0.2.0) while the product is now at v0.24 — dead
    code, not part of the actively maintained product surface. Not
    worth the test-writing effort of fixing a bug in an abandoned UI.
- [ ] **Items 2-4 (ADR-0029 phases 2-4: YAML consolidation, `kb add`/
  `create` writing the library file, DB demoted to verified cache,
  load-time validation) — deliberately NOT attempted this session.**
  This directly rewrites the operator's live production config
  (`~/.pyrite/config.yaml` and `~/kb/config.yaml`, ~25+ KBs, currently
  disagreeing on paths for several of them per the ADR's own Context
  section) — a hard-to-reverse action on live state, out of scope for
  an unattended sweep-and-fix pass. Needs a dedicated session where
  the operator can review the migration plan (and ideally a backup of
  both config files) before it runs.

## Notes

Sibling of [[verify-after-write-on-the-index-path]]; together they retire the derived-state-synchronization bug class.

The same dual-registry class also exists one level up in the primary deployment: `~/kb/config.yaml` and `~/.pyrite/config.yaml` disagree on paths for ~25 KBs (biography KBs point at `pyrite-kb-demo/` in one and `tcp-kb-internal/` in the other; `~/.pyrite` still registers stale `/private/tmp/test-release-kb` and `test-tasks`). The ADR resolves this via the one-file consolidation above. This also closes the registry-ADR item in [[file-missing-adrs-for-session-arc-decisions]].
