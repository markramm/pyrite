---
id: kb-remove-permanently-refuses-a-kb-whose-config-yaml-entry-was-already-deleted
title: kb remove permanently refuses a KB whose config.yaml entry was already deleted
type: backlog_item
tags:
- bug
- kb-registry
- dual-registry
importance: 5
kind: bug
status: proposed
priority: medium
effort: S
rank: 0
---

## Problem

Discovered while verifying a README.md doc claim (docs-onboarding-
fiction-sweep item 8) with a real `pyrite init` in a scratch directory,
then cleaning up afterward: `pyrite kb remove <name>` permanently
refuses to remove a KB if its DB row's `source` column is `"config"`,
even after the corresponding entry has been deleted from
`~/.pyrite/config.yaml` directly.

Root cause (`kb_registry_service.py`):

- `register_kb(..., source="config")` is called once, during
  `pyrite init` or any `seed_from_config()` sync, for any KB currently
  listed in `config.knowledge_bases`.
- `seed_from_config()` only ever upserts KBs that ARE in
  `config.knowledge_bases` right now -- it never demotes a KB whose
  `source` was previously set to `"config"` but is no longer present
  in the YAML. There is no "config KB was removed, revert its DB
  source" path anywhere.
- `remove_kb()` raises `KBProtectedError` unconditionally whenever
  `kb.source == "config"`, regardless of whether that KB is still
  actually in `config.yaml`.

Net effect: editing `config.yaml` by hand to remove a KB (the
documented, correct way per the existing error message: "Edit
config.yaml to remove it") does NOT actually make the KB removable
afterward -- the stale `source="config"` DB row makes `kb remove`
refuse forever. The only way out is a raw SQL DELETE against
`~/.pyrite/index.db`'s `kb` and `entry` tables (verified as the
workaround this session).

## Fix

`remove_kb()` (or `seed_from_config()`) should check whether the KB
is CURRENTLY in `config.knowledge_bases`, not just its DB-cached
`source` field, before refusing removal. Options:
1. `seed_from_config()` also demotes any DB row with `source="config"`
   that's no longer in `config.knowledge_bases` back to `source="user"`
   (or a new `source="orphaned"`) on every sync -- self-healing.
2. `remove_kb()` re-checks `config.get_kb(name)` live instead of
   trusting the cached `source` column -- simpler, no extra sync work,
   but only fixes the symptom at removal time, not general DB/config
   drift.

Prefer option 1 -- it's the same "the DB registry can drift from
config.yaml, and the fix is to reconcile them at every sync" pattern
already applied elsewhere this session (merge_registered_kbs,
verify-after-write-on-the-index-path).

## Acceptance criteria

- Removing a KB from config.yaml by hand, then running any command
  that calls `seed_from_config()` (e.g. `pyrite kb list`), makes the
  KB immediately removable via `pyrite kb remove <name>` without a
  raw SQL workaround.
