---
id: tests-t5-cli-and-software-kb-flow-tests-through-the-config-dir-not-load-config
title: 'Tests T5: CLI and software-kb flow tests through the config dir, not load_config or KBService patches'
type: backlog_item
tags:
- quality
- test
importance: 5
kind: tech_debt
status: proposed
priority: medium
effort: L
rank: 0
---

Source: test-architecture review 2026-09-25 (theme T5, fan-out on T4). Milestone 0.26, as the maintainer decided on 2026-09-24.

## Problem

- There are 95 patches of core constructors in 25 files, and `load_config` alone is patched at 9 module paths (`pyrite.config` 24, `pyrite.cli.context` 22, `pyrite.cli` 10, `pyrite.cli.search_commands` 5, `pyrite_software_kb.cli` 5, and four more). These tests pass whatever config file the real process would have read.
- `test_init_command.py` patches `save_config` in all 11 cases, so where `pyrite init` writes is untested. That is the #377 class of bug.
- In `extensions/software-kb/tests/test_software_kb.py`, the `sw_review`/`sw_submit`/`sw_transition`/`sw_claim` flow tools run against a mocked `KBService` (10 `patch("pyrite.services.kb_service.KBService")` sites). The CAS (`claim_entry` from_status→to_status), which is what the tools exist for, never runs; the tests assert the mock's canned return value. The conductor loop runs on these tools.

## Target shape

CLI tests use `world.cli()` and read back through the CLI or the service. The flow tools run the real CAS against a real DB and assert the entry's status on disk and in the index.

## Groom 2026-09-25

**Acceptance** (verbatim from the review):
1. The `patch("…load_config")` count in `tests/` and `extensions/*/tests` drops to an allowlist (ratchet test) of at most 5 justified sites.
2. `test_init_command.py` asserts where the config was written (inside the tmp config dir, and nothing under HOME), with no `save_config` patch.
3. In `test_software_kb.py`, each flow tool has a test in which removing the from-status check in `claim_entry` makes it fail (guard-removal proof).

**Packages.** There are three, with disjoint files. They can run in parallel with one another, but each is its own PR.
- **T5a, core CLI:** `tests/test_cli_commands.py`, `test_cli_context_db_kbs.py`, `test_link_*.py` (4), `test_import_cli.py`, `test_task_cli_*.py`, `test_schema_validate_*.py`, `test_db_backup*.py`, `test_index_health_exit_code.py`, `test_read_shaping_parity.py`, `test_search_filters_across_modes.py`, `test_readme.py`, `test_ci_command.py`. It also carries rule 6, the ratchet, in `tests/test_test_rules.py`.
- **T5b, admin/init:** `tests/test_admin_cli.py`, `tests/test_init_command.py`.
- **T5c, software-kb:** `extensions/software-kb/tests/test_software_kb.py`.

The ratchet in T5a must allow the sites that T5b and T5c have not yet removed. The last package to land tightens it.

**Sequence:**
- After T4, which provides `world.cli()`.
- Test files only, so there is no overlap with the security batch, unless that batch touches `test_admin_cli.py`. Check at dispatch.
- `test_link_*.py` overlaps #381's `tests/test_link_bulk_create.py`. Dispatch after #381 has merged.

**Model:** Sonnet. **Size:** M–L across the packages (S–M each). **Heavy:** yes. **Cold read:** no.

**Out of scope:**
- Changing any product code, including `claim_entry`.
- Converting REST tests off `dependency_overrides`. That happens as files are touched, on top of T4.
- Extension MCP dispatch (T6).
