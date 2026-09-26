"""Read/write the golden JSON files under `tests/characterization/goldens/`.

One file per surface (`rest.json`, `mcp.json`, `error_bodies.json`), each a
JSON object keyed by a stable, sorted string key so a diff is one line per
changed case, not a reshuffled file -- EXCEPT that a surface whose full
golden would exceed the repo's 500KB `check-added-large-files` pre-commit
limit is sharded into `{name}.{shard}.json` files instead (`load`/`save`
below do this transparently: callers still pass one `name` and get one
merged `dict` back). `rest`/`mcp` shard by principal (one of `world.py`'s
seven principal names is always the middle segment of every key here, so
this needs no new grouping logic); `error_bodies` (12KB) never shards.
Regeneration (`PYRITE_CHARACTERIZATION_REGENERATE=1 pytest
tests/characterization/ -n4`, documented in each test module's docstring)
writes these files; every other run only reads and compares. **Never gated
to run in CI** -- the regenerate path is opt-in per the environment
variable, off by default, and nothing in `scripts/test-affected`, the
pre-push hook or CI sets it.

**`save` merges into the file on disk, under a lock.** `test_rest_matrix.py`
and `test_mcp_matrix.py` parametrize one test per principal, and `-n4` (the
regenerate command every module's docstring documents) runs those in
separate worker processes -- each with its own in-memory `golden` dict from
its own `load()` call at the start of ITS test. A blind overwrite (what this
function used to do) is a lost-update race: worker B's `save()` replaces
worker A's already-written keys with B's smaller, worker-local dict, so the
regenerated file ends up holding only the last worker to finish -- confirmed
while building this harness (`PYRITE_CHARACTERIZATION_REGENERATE=1 pytest
... -n4` produced a `rest.json` missing 5 of 7 principals' keys, silently,
no error, until the very next plain run failed every one of them with "no
golden recorded"). `save` now re-reads the file immediately before writing
and merges `data` on top of it, inside a cross-process advisory lock
(`fcntl.flock`, POSIX-only -- matching this repo's dev platforms) so two
workers' read-merge-write cannot interleave.
"""

from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
from typing import Any

GOLDEN_DIR = Path(__file__).parent / "goldens"
REGENERATE_ENV = "PYRITE_CHARACTERIZATION_REGENERATE"

# Surfaces whose one-file golden would exceed the repo's 500KB
# check-added-large-files pre-commit limit -- sharded by principal instead
# (the middle " | "-delimited segment of every key in these two surfaces is
# always one of world.py's seven principal names).
_SHARDED_SURFACES = {"rest", "mcp"}


def regenerating() -> bool:
    return os.environ.get(REGENERATE_ENV) == "1"


def _shard_key(key: str) -> str:
    """The principal name segment of a sharded surface's key
    (``"{route/tool} | {principal} | {kb_state}"``) -- the shard a key
    belongs to."""
    parts = key.split(" | ")
    return parts[1] if len(parts) >= 2 else "_other"


def _shard_paths(name: str) -> list[Path]:
    return sorted(GOLDEN_DIR.glob(f"{name}.*.json"))


def load(name: str) -> dict[str, Any]:
    if name in _SHARDED_SURFACES:
        merged: dict[str, Any] = {}
        for path in _shard_paths(name):
            merged.update(json.loads(path.read_text()))
        return merged
    path = GOLDEN_DIR / f"{name}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def save(name: str, data: dict[str, Any]) -> None:
    """Merge `data`'s keys into `{name}.json` (or, for a sharded surface,
    into each `{name}.{shard}.json`) on disk, under a lock.

    Not a blind overwrite -- see the module docstring. A `.lock` sidecar
    file (not the `.json` itself) is what `flock` holds, so a reader that
    never regenerates never needs to touch a lock at all.
    """
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    if name in _SHARDED_SURFACES:
        by_shard: dict[str, dict[str, Any]] = {}
        for key, value in data.items():
            by_shard.setdefault(_shard_key(key), {})[key] = value
        for shard, shard_data in by_shard.items():
            _save_one(GOLDEN_DIR / f"{name}.{shard}.json", shard_data)
        return
    _save_one(GOLDEN_DIR / f"{name}.json", data)


def _save_one(path: Path, data: dict[str, Any]) -> None:
    lock_path = path.with_suffix(path.suffix + ".lock")
    with open(lock_path, "w") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            on_disk: dict[str, Any] = {}
            if path.exists():
                on_disk = json.loads(path.read_text())
            on_disk.update(data)
            path.write_text(json.dumps(on_disk, indent=2, sort_keys=True) + "\n")
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)


def assert_matches(name: str, key: str, actual: Any, golden: dict[str, Any]) -> None:
    """Compare `actual` against `golden[key]`. In regenerate mode, records
    instead of comparing (the caller writes the whole dict once at the end
    of the module via `save`)."""
    if regenerating():
        golden[key] = actual
        return
    assert key in golden, (
        f"{key!r} has no golden recorded. Run with "
        f"{REGENERATE_ENV}=1 to (re)generate tests/characterization/goldens/{name}.json, "
        f"review the diff, and commit it as its own reviewed change."
    )
    assert actual == golden[key], (
        f"golden mismatch for {key!r}:\n  golden:  {golden[key]}\n  actual:  {actual}"
    )
