"""#13's acceptance criterion, against a real `pyrite-server` on a real socket.

> With an empty HF cache and the network blocked, `POST /api/entries` returns
> in < 2 s and the entry is keyword-searchable (live-server test).

The three other test surfaces for ADR-0035 (module-level, TestClient, and the
cold subprocess probe in `tests/test_writes_never_block_on_embedding.py`) all
run pyrite's code inside the pytest process, where the suite's autouse fixture
has a hand on the embedding switch. This file is the one that runs the
*assembled artifact*: the `pyrite-server` console script, a config file on
disk with `auto_embed: true`, an HTTP client over a socket, and an empty
`HF_HOME` with `HF_HUB_OFFLINE=1` — which is what a fresh install looks like
before anyone has downloaded the model.

Deliberately not asserted here: "the server imported no torch". A live server
is a separate process whose `sys.modules` this test cannot read, and adding a
test-only probe endpoint to read it would be a production surface existing
only for a test. The module assertion lives in the cold subprocess probe,
where it is free; here the wall-clock bound plus a *pending* row in
`embed-status` is the observable evidence that the model was never touched.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from .conftest import seed_kb, start_server, stop_server

pytestmark = pytest.mark.e2e

# #13's number. A write that has to load a model cannot make this even with a
# warm cache (~3 s measured in the issue); with a cold one it is >60 s.
WRITE_BUDGET_SECS = 2.0


@pytest.fixture(scope="module")
def fresh_install_server(tmp_path_factory):
    """A server with `auto_embed: true`, an empty HF cache and no network.

    `smoke_env` sets `PYRITE_AUTO_EMBED=0` for the smoke layer at large; this
    fixture opts back in, because "does a write block on the model" is a
    question only `auto_embed: true` can answer.
    """
    data_dir: Path = tmp_path_factory.mktemp("pyrite-fresh-install")
    kb_dir = data_dir / "smoke-kb"
    seed_kb(kb_dir, "smoke", title="Analytical Engine", body="A mechanical computer.")

    hf_home = data_dir / "empty-hf-cache"
    hf_home.mkdir()

    server = start_server(
        data_dir,
        kbs=[{"name": "smoke", "path": str(kb_dir), "kb_type": "generic", "description": "smoke"}],
        settings={"auto_embed": True},
        env_extra={
            "PYRITE_AUTO_EMBED": "1",
            # A fresh install: nothing cached, and no way to fetch it.
            "HF_HOME": str(hf_home),
            "HUGGINGFACE_HUB_CACHE": str(hf_home / "hub"),
            "TRANSFORMERS_CACHE": str(hf_home / "hub"),
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            # Startup prewarm would load the model before the write and mask
            # the very thing under test.
            "PYRITE_PREWARM_EMBEDDINGS": "false",
        },
    )
    try:
        yield server
    finally:
        stop_server(server)


@pytest.fixture(scope="module")
def first_write(fresh_install_server):
    """The first `POST /api/entries` this server has ever seen, timed."""
    started = time.monotonic()
    resp = fresh_install_server.client.post(
        "/api/entries",
        json={
            "kb": "smoke",
            "title": "Kestrel Notes",
            "entry_type": "note",
            "body": "Field notes on falcons.",
        },
    )
    elapsed = time.monotonic() - started
    return resp, elapsed


def test_the_first_write_returns_in_under_two_seconds(fresh_install_server, first_write):
    resp, elapsed = first_write
    assert resp.status_code in (200, 201), (resp.status_code, resp.text)
    assert elapsed < WRITE_BUDGET_SECS, (
        f"POST /api/entries took {elapsed:.1f}s on a server with an empty HF "
        f"cache and no network. That is #13: the write is loading the "
        f"embedding model inline. ADR-0035 says a write enqueues.\n"
        f"Server output:\n{fresh_install_server.output()}"
    )


def test_the_new_entry_is_keyword_searchable(fresh_install_server, first_write):
    """Not embedding must not mean not indexed."""
    resp, _elapsed = first_write
    assert resp.status_code in (200, 201), resp.text

    found = fresh_install_server.client.get(
        "/api/search", params={"q": "Kestrel", "kb": "smoke", "mode": "keyword"}
    )
    assert found.status_code == 200, found.text
    ids = [r["id"] for r in found.json()["results"]]
    assert "kestrel-notes" in ids, (
        f"the entry wrote but is not keyword-searchable: {found.json()}\n"
        f"Server output:\n{fresh_install_server.output()}"
    )


def test_the_embedding_debt_is_visible(fresh_install_server, first_write):
    """The debt is recorded, not dropped — an operator can see and drain it."""
    resp, _elapsed = first_write
    assert resp.status_code in (200, 201), resp.text

    status = fresh_install_server.client.get("/api/index/embed-status")
    assert status.status_code == 200, status.text
    body = status.json()
    assert body["pending"] >= 1, (
        f"the write skipped embedding but recorded no debt: {body}. "
        f"Eventually-embedded means queued, not forgotten.\n"
        f"Server output:\n{fresh_install_server.output()}"
    )


# ---------------------------------------------------------------------------
# The other half of the promise: with a model available, the debt gets paid
# ---------------------------------------------------------------------------

HF_REPO = "sentence-transformers/all-MiniLM-L6-v2"


def model_is_cached() -> bool:
    """Is the embedding model already on this machine? (No network call.)"""
    try:
        from huggingface_hub import try_to_load_from_cache
    except ImportError:
        return False
    try:
        return isinstance(try_to_load_from_cache(HF_REPO, "config.json"), str)
    except Exception:
        return False


def sentence_transformers_available() -> bool:
    import importlib.util

    return importlib.util.find_spec("sentence_transformers") is not None


@pytest.fixture(scope="module")
def warm_cache_server(tmp_path_factory):
    """`auto_embed: true` with the model already on disk.

    The regression guard for the change this theme makes: without it,
    "the write does not embed" would be satisfied just as well by code that
    never embeds anything, and semantic search would silently go dark.
    """
    if not sentence_transformers_available():
        pytest.skip("sentence-transformers not installed")
    if not model_is_cached():
        pytest.skip(
            f"embedding model {HF_REPO!r} is not in the local HuggingFace cache "
            f"and the smoke layer runs offline; warm it with "
            f"`huggingface-cli download {HF_REPO}` to run this test"
        )

    data_dir: Path = tmp_path_factory.mktemp("pyrite-warm-cache")
    kb_dir = data_dir / "smoke-kb"
    seed_kb(kb_dir, "smoke", title="Analytical Engine", body="A mechanical computer.")

    server = start_server(
        data_dir,
        kbs=[{"name": "smoke", "path": str(kb_dir), "kb_type": "generic", "description": "smoke"}],
        settings={"auto_embed": True},
        env_extra={"PYRITE_AUTO_EMBED": "1"},
    )
    try:
        yield server
    finally:
        stop_server(server)


def test_a_sync_drains_the_queue_and_the_entry_becomes_semantically_findable(warm_cache_server):
    """ADR-0035's "eventually": the entry IS embedded, just not on the write.

    `POST /api/index/sync?wait=true` is one of the two documented drain points
    (the other is startup prewarm). After it, the debt is zero and the entry
    answers a query that shares no keywords with it.
    """
    client = warm_cache_server.client

    resp = client.post(
        "/api/entries",
        json={
            "kb": "smoke",
            "title": "Kestrel Notes",
            "entry_type": "note",
            "body": "Field notes on a small falcon that hovers while hunting.",
        },
    )
    assert resp.status_code in (200, 201), resp.text
    assert client.get("/api/index/embed-status").json()["pending"] >= 1

    synced = client.post("/api/index/sync?wait=true", timeout=180.0)
    assert synced.status_code == 200, synced.text

    status = client.get("/api/index/embed-status").json()
    assert status["pending"] == 0 and status["failed"] == 0, (
        f"sync did not drain the embed queue: {status}\n"
        f"Server output:\n{warm_cache_server.output()}"
    )

    found = client.get(
        "/api/search",
        params={"q": "birds of prey", "kb": "smoke", "mode": "semantic"},
        timeout=180.0,
    )
    assert found.status_code == 200, found.text
    ids = [r["id"] for r in found.json()["results"]]
    assert "kestrel-notes" in ids, (
        f"the queue drained but semantic search still cannot see the entry: {found.json()}\n"
        f"Server output:\n{warm_cache_server.output()}"
    )
