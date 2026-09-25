---
id: tests-t3-finish-test-isolation-after-377-extensions-covered-env-scrubbed-home
title: 'Tests T3: finish test isolation after #377 - extensions covered, env scrubbed, HOME out of reach'
type: backlog_item
tags:
- quality
- test
importance: 5
kind: tech_debt
status: proposed
priority: high
effort: M
rank: 0
---

Source: test-architecture review 2026-09-25 (theme T3). Milestone 0.26, as the maintainer decided on 2026-09-24. It finishes the work #377 / PR #387 starts.

## Problem

- The isolation fixtures (`_isolate_global_config`, `_reset_rate_limiter`) live in `tests/conftest.py`. `extensions/*/tests` has no conftest, so 994 extension tests run with the real `CONFIG_DIR`/`CONFIG_FILE` and a shared rate limiter.
- Nothing scrubs the environment. `_apply_env_overrides` reads 14 `PYRITE_*` variables, and `Settings` reads the AI keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_BASE`). So a developer's shell changes what the tests see.
- `tests/test_models.py:579` and `tests/test_storage.py:1038` read `~/CascadeSeries`, the maintainer's real data. On CI they skip; on the maintainer's machine they run.
- A subprocess `env=` built from scratch, rather than copied from `os.environ`, drops the session isolation #377 adds.

## Target shape

- Session isolation lives in the **root** `conftest.py`: the config dir, the data dir, the rate limiter, a scrub of every `PYRITE_*` variable the session does not set itself, the AI keys, and HOME for anything that reads `Path.home()`.
- The `~/CascadeSeries` tests move to a checked-in fixture corpus, or are deleted.
- A canary spawns `sys.executable -m pyrite kb list` (or `pyrite.cli:main`) from an extension test directory and asserts the child saw only the tmp config, the way `test_git_env_isolation.py` does for git.

## Groom 2026-09-25

**Acceptance** (verbatim from the review):
1. An extension test calling `save_config()` writes under tmp. A canary in `extensions/…/tests` proves it.
2. With `PYRITE_AUTH_ENABLED=true OPENAI_API_KEY=x` exported, the default suite result is unchanged. Run the core set both ways and report.
3. `grep -rn "Path.home()\|expanduser" tests extensions/*/tests` finds only tests that set HOME themselves.
4. The rules test rejects `subprocess` `env=` literals not derived from `os.environ` (or a named helper).

**Touches:**
- Existing: `conftest.py` (root), `tests/conftest.py` (the moved fixtures come out), `tests/test_models.py`, `tests/test_storage.py`, `tests/test_test_rules.py` (created by T1).
- New: `tests/test_session_isolation.py`, one canary test file under an extension's `tests/`.

**Sequence:**
- After #387 (#377), which edits the root `conftest.py` and `pyrite/config.py` path resolution.
- After T1, because it adds a rule to T1's `tests/test_test_rules.py`.
- Before T2a (same root conftest; T3 moves fixtures, so it goes first).
- Before T7 (both edit `tests/conftest.py` and `tests/test_models.py`).

**Model:** Sonnet. **Size:** S–M. **Heavy:** yes (full suite, extensions included). **Cold read:** yes. This is the fence around the maintainer's real config, and #377 showed that a gap costs about 9 hours of a broken registry.

**Out of scope:**
- The product-side default paths (`Settings.index_path` following the config dir). That is #377 / #387, and #382 (composition root) in 0.27.
- Moving `tests/` into packages.
- Postgres test isolation (roadmap: Later).
