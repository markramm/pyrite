---
id: dirty-world-fixtures-and-adversarial-corpus
type: backlog_item
title: "Dirty-world fixture tier + adversarial string corpus: make the field-bug classes representable in tests"
kind: tech_debt
status: proposed
priority: medium
effort: M
created: "2026-07-03"
tags: [testing, fixtures, audit-2026-07]
links:
- target: verify-after-write-on-the-index-path
  relation: related
  kb: pyrite
- target: collapse-kb-registry-to-one-source-of-truth
  relation: related
  kb: pyrite
---

## Problem

The 2026-07-03 test audit's escape analysis: all five major field
bugs were structurally unrepresentable in the current fixtures. The
suite verifies the system agrees with itself, not with the world:

- Fixtures hand a fully-populated in-memory `PyriteConfig` to
  services (`tests/conftest.py:76-79`); CLI tests patch
  `pyrite.cli.load_config` entirely (`test_cli_commands.py:71-84`).
  The real config path — YAML load + DB-registered-KB merge — is
  exercised almost nowhere → dual-registry bugs invisible.
- No test modifies a file out-of-band after indexing → staleness
  bugs invisible.
- Test strings are friendly ("Test Event 0", "immigration") while
  field vocabulary is "capture", "legalism", "0.6 milestone",
  emails → FTS-syntax bugs invisible (each character class was
  added reactively after its field crash).
- Shape-only assertions on the CLI/admin surface (162
  `exit_code == 0` asserts; `test_admin_cli.py:137` accepts exit
  codes 0, 1, AND 2; `test_kb_create_success` never uses the created
  KB afterward).
- 84 of 175 test files roll their own tempdir environments — every
  copy re-decides what "a KB" looks like, all of them clean-world.

## Fix

1. **Dirty-world fixture family** in tests/conftest.py: a config
   with (a) a KB registered in the DB but absent from YAML, (b) a KB
   in YAML pointing at a moved path, (c) a file modified out-of-band
   after indexing (mtime + same-second variants), (d) config loaded
   through real `load_config` from a real temp YAML — no patching.
   Migrate the highest-traffic CLI/index tests onto it.
2. **`ADVERSARIAL_TITLES` shared constant** (hyphens, dots, colons,
   FTS column names like "capture"/"legalism", quotes, unicode,
   emails) used by DEFAULT in fixture entry factories — friendly
   strings become the opt-in, not the default.
3. **One Hypothesis property test per FTS-query builder** ("any
   string → no OperationalError") — currently zero property tests in
   3,800+.
4. **Seam assertions**: for each index write path, one test reading
   the raw DB row (the 2f49984 pattern, generalized); for each JSON
   surface, assert field content not shape.
5. Consolidate the ~50 file-local `*_env` fixtures onto the conftest
   chain opportunistically as tests get touched (don't big-bang).

## Acceptance criteria

- A test written against the dirty-world tier reproduces (in
  pre-fix form) at least 3 of the 5 historical field bugs.
- New fixture entries contain adversarial strings by default.
