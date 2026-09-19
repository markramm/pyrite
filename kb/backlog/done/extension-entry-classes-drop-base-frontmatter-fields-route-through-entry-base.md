---
id: extension-entry-classes-drop-base-frontmatter-fields-route-through-entry-base
title: 'Extension entry classes drop base frontmatter fields: route through Entry._base_kwargs and add a registry-wide conformance test'
type: backlog_item
tags:
- bug
- models
- extensions
- round-trip
importance: 5
status: done
priority: medium
rank: 0
assignee: agent:pyrite-worker
---

Three extensions' entry classes hand-roll the base constructor kwargs instead of
calling `Entry._base_kwargs`, so base frontmatter fields they forgot to list are
silently dropped on every load -> save round trip. Fix by routing them through
the shared path, and pin the guarantee for **every** registered entry class
(core + every installed plugin, discovered through the plugin registry) with a
conformance test.

## Groom 2026-09-19

### The mechanism, confirmed from the code

`pyrite/models/base.py:133` `Entry._base_kwargs` is the single place that reads
the base field set out of frontmatter. `pyrite/models/core_types.py` and three
extensions route through it (or a local copy of it). These three do not — each
`from_frontmatter` builds a literal `cls(...)` call listing the fields its author
remembered:

| Extension | Class | Line | Base fields omitted from the `cls(...)` call |
|---|---|---|---|
| social | `WriteupEntry` | `extensions/social/src/pyrite_social/entry_types.py:47-62` | `aliases`, `importance`, `_schema_version` |
| social | `UserProfileEntry` | `extensions/social/src/pyrite_social/entry_types.py:106-125` | `aliases`, `_schema_version` (reads `importance` by hand at :113) |
| zettelkasten | `ZettelEntry` | `extensions/zettelkasten/src/pyrite_zettelkasten/entry_types.py:52-68` | `aliases`, `importance`, `_schema_version` |
| zettelkasten | `LiteratureNoteEntry` | `extensions/zettelkasten/src/pyrite_zettelkasten/entry_types.py:103-118` | `aliases`, `importance`, `_schema_version` |
| encyclopedia | `ArticleEntry` | `extensions/encyclopedia/src/pyrite_encyclopedia/entry_types.py:51-67` | `aliases`, `importance`, `_schema_version` |
| encyclopedia | `TalkPageEntry` | `extensions/encyclopedia/src/pyrite_encyclopedia/entry_types.py:99-112` | `aliases`, `importance`, `_schema_version` |

Observed directly (load a file carrying `aliases: [alt-name]`, `importance: 9`,
`_schema_version: 3`, then read the entry back):

```
writeup          aliases= [] importance= 5 _sv= 0 lifecycle= archived extras= {}
user_profile     aliases= [] importance= 9 _sv= 0 lifecycle= archived extras= {}
zettel           aliases= [] importance= 5 _sv= 0 lifecycle= archived extras= {}
literature_note  aliases= [] importance= 5 _sv= 0 lifecycle= archived extras= {}
article          aliases= [] importance= 5 _sv= 0 lifecycle= archived extras= {}
talk_page        aliases= [] importance= 5 _sv= 0 lifecycle= archived extras= {}
```

`importance` is the worst of the three: it does not merely blank, it **silently
changes value** — a `writeup` saved at `importance: 9` comes back 5 and is
written back as 5, so a load/save cycle rewrites the user's ranking.

Two details that matter for the fix, both confirmed:

- **`extra_frontmatter` does not rescue these.** `aliases`, `importance` and
  `_schema_version` are all members of `_BASE_CONSUMED_KEYS`
  (`pyrite/models/base.py:29-47`), so `capture_extra_frontmatter` excludes them
  from the extras dict on the theory that the class handled them. The probe
  above shows `extras= {}`. The undeclared-key safety net landed in
  `tests/test_frontmatter_round_trip_all_types.py` is therefore blind to exactly
  this bug class, which is why it survived.
- **`lifecycle` is not affected.** `Entry.from_markdown`
  (`pyrite/models/base.py:263`) and `entry_from_frontmatter`
  (`pyrite/models/core_types.py:444`) restore it after construction, outside the
  constructor. Do not "fix" it in `_base_kwargs`; it is not a constructor kwarg
  on this path.

### Which extensions already conform

- **cascade** — `extensions/cascade/src/pyrite_cascade/entry_types.py:18` local
  `_base_kwargs`, includes `aliases`. Missing only `_schema_version`.
- **journalism-investigation** —
  `extensions/journalism-investigation/src/pyrite_journalism_investigation/entry_types.py:31`,
  same shape, includes `aliases`, missing `_schema_version`.
- **software-kb** —
  `extensions/software-kb/src/pyrite_software_kb/entry_types.py:61`
  `_note_base_kwargs`, missing **both** `aliases` and `_schema_version`.
- `pyrite/models/task.py:405` `_note_base_kwargs` is a fourth in-tree copy with
  the same gaps.

So there are five hand-rolled copies of one function, each drifting differently.
The fix is not "patch three extensions" — it is delete the copies and call
`Entry._base_kwargs`, which is already a `@staticmethod` and already correct.

### Acceptance

- Every entry class in `social`, `zettelkasten` and `encyclopedia` builds its
  constructor kwargs from `Entry._base_kwargs(meta, body)` and extends the
  result with its own fields — no literal re-listing of base fields.
- The local `_base_kwargs` / `_note_base_kwargs` copies in `cascade`,
  `journalism-investigation`, `software-kb` and `pyrite/models/task.py` are
  deleted in favour of `Entry._base_kwargs`, or (if a copy must stay for a
  signature reason) documented at its definition with why.
- A new conformance test, added to `tests/test_frontmatter_round_trip_all_types.py`,
  parametrizes over **every registered entry type** discovered through the
  plugin registry — reuse the existing `_all_types()` helper at line 24, do not
  hand-list classes — and asserts that an entry loaded from frontmatter carrying
  the full base field set (`aliases`, `importance`, `tags`, `links`, `sources`,
  `metadata`, `summary`, `provenance`, `created_at`, `updated_at`,
  `_schema_version`, `lifecycle`) round-trips each one unchanged through
  `to_frontmatter()`.
- The new test fails on `dev` for `writeup`, `user_profile`, `zettel`,
  `literature_note`, `article`, `talk_page` before the fix, and passes for every
  registered type after. Include the pre-fix failure list in the PR body.
- A type added by a future plugin is covered automatically, with no edit to the
  test.
- CHANGELOG entry under Fixed.

### Regimes

The conditions the test must enter, not just the happy path:

- **Full base field set present** — every base key carries a non-default value
  (this is the regime that fails today; defaults hide the bug).
- **Base fields absent** — frontmatter with only `id`/`title`/`type`; the
  defaults must still apply and nothing may be emitted as an empty key.
- **Round trip through disk**, not only in memory: `to_markdown()` ->
  `from_markdown()` for at least one class per extension, so the YAML layer is
  in the loop and `save()`'s body handling is exercised.
- **Undeclared keys still preserved** — the existing `EXTRAS` guarantee must not
  regress when `_base_kwargs` starts consuming more keys; assert both in the
  same run.
- **Plugin registry empty** — the test must not error when no extension is
  installed (core types only), since CI runs a core-only leg.

### Touches

- existing: `extensions/social/src/pyrite_social/entry_types.py`,
  `extensions/zettelkasten/src/pyrite_zettelkasten/entry_types.py`,
  `extensions/encyclopedia/src/pyrite_encyclopedia/entry_types.py`,
  `extensions/cascade/src/pyrite_cascade/entry_types.py`,
  `extensions/journalism-investigation/src/pyrite_journalism_investigation/entry_types.py`,
  `extensions/software-kb/src/pyrite_software_kb/entry_types.py`,
  `pyrite/models/task.py`, `tests/test_frontmatter_round_trip_all_types.py`,
  `CHANGELOG.md`
- new: none expected. If `_base_kwargs` needs a `lifecycle`-aware variant, that
  is a signal to stop and re-groom, not to add a file.

### Sequence

- **Does not wait on #180** (private-KB read scoping) — that PR is entirely
  under `pyrite/server/`, disjoint.
- **Land after #173** (`fix/writeback-timestamps-v2`). #173 modifies
  `pyrite/models/base.py` and adds `tests/test_roundtrip_identity.py`, changing
  when `created_at`/`updated_at` are written back. If this theme lands first,
  #173 rebases onto a changed `_base_kwargs` contract and its timestamp
  assertions move under it. One file in common (`pyrite/models/base.py`) only if
  the worker ends up touching the base; even if it does not, the *semantics* of
  a base-field round trip are what #173 is pinning.
- **Land after #175** (`fix/generic-entry-metadata-duplication`) — semantic
  overlap, not file overlap. #175 is about `GenericEntry` re-emitting undeclared
  keys into a `metadata:` block; both PRs edit `tests/test_roundtrip_identity.py`
  (#175) and this one edits the sibling round-trip file. The rule this theme
  states ("the base field set survives a round trip for every registered class")
  should be written *after* #175 settles what `metadata` means on the way out,
  or the conformance test will assert a shape #175 then changes.
- Practical read: this is third in the queue behind #173 and #175. If the
  conductor wants it sooner, it can go in parallel on the extension files alone
  and defer the `pyrite/models/task.py` and in-tree copy cleanup to a follow-up —
  but the conformance test must wait for #175 either way.

### Model

**Sonnet.** The fix is mechanical after the reading above: the target function
exists, is correct, and is already used by eight call sites; the change is
replacing six literal constructor calls with `kw = cls._base_kwargs(meta, body)`
plus the type-specific keys, exactly as `PersonEntry.from_frontmatter`
(`pyrite/models/core_types.py:72-81`) already does. The conformance test has a
working precedent in the same file. No base-path design change is required —
if the worker finds one is, that is a stop-and-report, not a judgement call.

heavy: no

### Cold read

**No.** No public shape changes: no CLI flag, REST route, MCP tool argument or
file format changes. The on-disk format gains *fidelity* (fields that were being
dropped are now kept), which is the fix, not a format change. Nothing under
auth, storage or server. The suite plus the new conformance test is the evidence.

### Out of scope

- Moving the extension directories or renaming them (that is the post-0.24.2
  move, explicitly deferred by the maintainer).
- Relabelling these three as example plugins — that is the sibling item and
  lands after this one.
- Adding new base fields to `Entry`, or changing `_BASE_CONSUMED_KEYS`
  membership. If `aliases` should not be a base field, that is an ADR.
- Fixing `lifecycle`'s out-of-constructor restore path. It works; leave it.
- Touching `GenericEntry` (#175 owns it) or the timestamp write-back rules
  (#173 owns them).
- A data migration for KBs already damaged by the dropped fields. Real, but a
  separate ticket: the fields are gone from disk already and cannot be recovered
  by code.
