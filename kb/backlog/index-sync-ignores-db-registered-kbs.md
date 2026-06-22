---
id: index-sync-ignores-db-registered-kbs
type: backlog_item
title: "index sync/build ignore DB-registered KBs (get_config_and_db skips _register_db_kbs)"
kind: bug
status: proposed
priority: high
effort: S
tags: [index, cli, kb-registry, context, cloud, headless]
---

## Problem

`pyrite index sync` (and the other `index_commands.py` entry points) operate on a config that is
**missing any KB added via `pyrite kb add`**, so indexing a DB-registered KB produces **0 entries**
even though `pyrite kb list` shows it. This makes `kb add` + `index sync` unusable together — the
exact path a headless/cloud setup relies on (register a KB at runtime, then index it, with no YAML
config edit).

## Root cause

`pyrite/cli/index_commands.py` builds its context via `get_config_and_db()`:

```python
# index_commands.py:42, 142, 197
config, db = get_config_and_db()
```

`get_config_and_db()` (`pyrite/cli/context.py:85`) only does `load_config()` — it never calls
`_register_db_kbs()`:

```python
def get_config_and_db() -> tuple[PyriteConfig, PyriteDB]:
    config = load_config()
    db = PyriteDB(config.settings.index_path)
    return config, db          # <-- no _register_db_kbs(config, db)
```

By contrast `_init_base()` (`context.py:44`, used by the context managers) DOES merge them:

```python
def _init_base():
    config = load_config()
    db = PyriteDB(config.settings.index_path)
    _register_db_kbs(config, db)   # <-- DB-registered KBs merged in
    ...
```

So KBs registered through `pyrite kb add` (which live in the DB, not the YAML config) are invisible
to `index sync`.

## Repro

```bash
pyrite kb add /path/to/some-kb -n some-kb        # registers into the DB
pyrite kb list                                   # some-kb shows up
pyrite index sync -k some-kb                      # "Updated: 0" — indexes nothing
pyrite search "<known term>" -k some-kb           # 0 results
```

Observed in a cloud container: a freshly `kb add`-ed cascade-timeline indexed 0 entries until the
KB path was hand-added to the YAML config so `load_config()` picked it up.

## Acceptance criteria

- `pyrite kb add <path> -n foo` followed by `pyrite index sync -k foo` indexes `foo`'s entries
  (non-zero) with no YAML config edit.
- `pyrite search <term> -k foo` returns those entries.

## Suggested fix

Make `get_config_and_db()` call `_register_db_kbs(config, db)` before returning (matching
`_init_base()`), or migrate `index_commands.py` to a context that performs the merge
(e.g. `cli_db_context()`).

## Provenance

Surfaced 2026-06-22 by the daily-capture cloud smoke test (a headless container running
`kb add cascade-timeline` then `index sync`). Also filed as GitHub issue markramm/pyrite#2.
Workaround in the capture fleet: drop pyrite from the cloud path entirely (stdlib grep over the
cloned timeline) — but this bug should still be fixed for any `kb add` + index user.
