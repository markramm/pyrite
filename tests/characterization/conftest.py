"""Session-scoped world for the ADR-0037 theme-0 characterization harness.

One `World` (tests/characterization/world.py) is built once per pytest
session (or once per xdist worker -- xdist gives each worker its own
process, so "session" here means "once per worker", which is still one
build for the whole matrix that worker runs) and shared read-only by every
test in this package. Building the REST app, the three-plus-one KBs, the
API keys and the six sessions costs real time (index syncs, bcrypt hashing);
doing it once is what keeps the full principal x KB-state x
operation/tool matrix inside the pre-push budget.
"""

from __future__ import annotations

import pytest

from tests.characterization.world import World, build_world


@pytest.fixture(scope="session")
def world(tmp_path_factory) -> World:
    w = build_world(tmp_path_factory)
    try:
        yield w
    finally:
        w.close()
