---
id: tests-t4-a-world-builder-in-tests-config-dir-kbs-db-and-entries-once-surfaces
title: 'Tests T4: a world builder in tests/ - config dir, KBs, DB and entries once, surfaces through real wiring'
type: backlog_item
tags:
- quality
- test
importance: 5
kind: tech_debt
status: proposed
priority: high
effort: L
rank: 0
---

Source: test-architecture review 2026-09-25 (theme T4, the foundation). Milestone 0.26, as the maintainer decided on 2026-09-24.

**Decided (maintainer, 2026-09-24):**
- The world builder lives in `tests/`, not in `pyrite.testing`. It stays out of the wheel, and extensions import it through the repo root (`tests/__init__.py` exists; extension tests already run from the repo root).
- Size markers are deferred. This builder must not add a `medium` marker.

## Problem

- `PyriteConfig(` is built by hand 266 times in 149 files, and `create_app(` is hand-rolled in 52 files. The shared `make_client` builder is used by 10 files.
- 39 files replace `get_config`/`get_db` through `dependency_overrides`, so the real DI path is not what they test.
- 80 `TestClient(...)` constructions skip the lifespan, so startup hooks (the embed-queue drain, the websocket loop bind) never run.
- Three files alone printed 14 "unclosed database" warnings, because `create_app()` opens a second `PyriteDB` that hand-rolled fixtures never close.
- The MCP builder `_make_mcp_server` lives in `tests/test_mcp_server.py`, and `test_mcp_tool_dispatch_smoke.py` imports it: a test-to-test import.

## Target shape

A shared builder: an importable helper module under `tests/`, exposed as fixtures in the root conftest. It:
- writes a real `config.yaml` into a tmp config dir;
- creates KBs, and indexes entries through `KBService`;
- hands out `.rest(auth=…)` (a TestClient entered as a context manager, **no dependency_overrides**, the real lifespan), `.cli()` (a CliRunner with `PYRITE_CONFIG_DIR` in its env) and `.mcp(tier)`;
- owns and closes every DB and worker that it or the app opens.

`make_client`, `rest_api_env` and `_make_mcp_server` become thin wrappers over it, or move into it.

## Groom 2026-09-25

**Acceptance** (verbatim from the review; item 1 of the footprint follows the decision above):
1. The builder exists with its own tests. A route relying on startup (the embed drain) behaves as in production. Every DB it opened is closed at teardown (`ResourceWarning` as error in its tests).
2. `filterwarnings = error::ResourceWarning` (or scoped to the sqlite "unclosed database" message) passes for the files migrated in this PR.
3. Migrate as proof: `test_websocket_delivery.py`, `test_rest_api.py`, `test_kb_commit.py` (the three leaking files measured), plus `test_mcp_tool_dispatch_smoke.py`, which stops importing `tests.test_mcp_server`.
4. Document the builder in CONTRIBUTING "Running the tests" as the default way to write a medium test.

**Touches:**
- Existing: `conftest.py` (root), `tests/conftest.py` (the wrappers), `tests/test_mcp_server.py` (the helper moves out), `tests/test_websocket_delivery.py`, `tests/test_rest_api.py`, `tests/test_kb_commit.py`, `tests/test_mcp_tool_dispatch_smoke.py`, `CONTRIBUTING.md`.
- New: `tests/_world.py` (name at the worker's discretion, but under `tests/`), `tests/test_world.py`.

**Sequence:**
- After #387 (#377), T3 and T7, all of which edit the root or `tests/` conftest. T7's `wait_until` helper should exist first.
- After #381 (#378) merges, because #381 edits `tests/test_mcp_server.py` and `tests/test_mcp_tool_dispatch_smoke.py`.
- After T1, which adds timeouts in `test_websocket_delivery.py` and `test_kb_commit.py`.
- Before #382 (composition root, 0.27). With no DI overrides and a config dir on disk, the builder survives that move unchanged, and it turns #382's test churn into one place instead of 95 patch sites.
- `CONTRIBUTING.md` is also edited by #374 and #244. Rebase, don't parallelise.

**Model:** Opus. It is a design-shaped foundation that sets the default shape of every future test. **Size:** L. **Heavy:** yes (full suite). **Cold read:** yes: shared test infrastructure, and teardown ordering has caused #55-class flakes before.

**Out of scope:**
- `pyrite.testing` or anything shipped in the wheel (decided).
- Size markers (deferred).
- Migrating files beyond the four named. T5 and T6 do that fan-out.
- `pyrite/runtime.py` (#382).
- Reorganising `tests/` into directories.
