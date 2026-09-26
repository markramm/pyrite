"""Two worlds for the ADR-0037 theme-0 characterization harness.

`world` (session-scoped -- once per xdist worker, since xdist gives each
worker its own process) is READ-ONLY by convention: every read/list/search
case runs against it, and nothing may write through it, so its content is
exactly what `world.py`'s seeding put there for the life of the worker.

`write_world` is a MODULE-scoped world (one fresh `build_world` call per
test *module* that asks for it -- `test_rest_matrix.py`'s write loop and
`test_mcp_matrix.py`'s write loop each get their own, never one shared
across modules and never the same object as `world`). Round 1 already
solved individual write CASES colliding with each other inside one world
(unique `call_key`-derived identity fields, disposable entries for a tool
that mutates an existing row); module-level isolation is the next
granularity up -- it keeps a write module's OWN listing verifications
(does the entry I just wrote actually show up) free of whatever a
DIFFERENT module's write cases already added, while still building only a
handful of worlds total rather than one per individual case (which would
also work, just at a much higher, unnecessary cost: this harness's write
surface is a small minority of its whole matrix).
"""

from __future__ import annotations

import pytest

from tests.characterization.world import World, build_world


@pytest.fixture(scope="session")
def world(tmp_path_factory) -> World:
    w = build_world(tmp_path_factory, label="adr0037-read")
    try:
        yield w
    finally:
        w.close()


@pytest.fixture(scope="module")
def write_world(tmp_path_factory) -> World:
    w = build_world(tmp_path_factory, label="adr0037-write")
    try:
        yield w
    finally:
        w.close()
