"""Embedding prewarm actually happens at startup, and /health says so.

Regression for PR #5. `create_app()` constructed an `EmbeddingService` when
`PYRITE_PREWARM_EMBEDDINGS=true` and stored it on app state next to a comment
claiming "actual prewarm happens in lifespan" -- but no lifespan handler and no
startup event ever called `.prewarm()`. So `/health`'s `embeddings.ready`
stayed `false` forever, and the cold-start cost the feature exists to remove
was paid by whichever request first touched the model.

The shape of that bug is why this test has to be out of process: it is not
"does prewarm() work" (it did) but "is prewarm() wired into the startup of a
real server". Only starting one can answer that, and the answer has to be read
from the same place an operator reads it -- `/health`, without issuing any
write first.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from .conftest import seed_kb, start_server, stop_server

pytestmark = pytest.mark.e2e

HF_REPO = "sentence-transformers/all-MiniLM-L6-v2"

# Startup prewarm loads the model from disk; on a cold filesystem cache that is
# slow, and /health answers before it finishes.
PREWARM_TIMEOUT = 180.0


def model_is_cached() -> bool:
    """Is the embedding model already on this machine?

    The smoke layer runs with HF_HUB_OFFLINE=1 and must never pull a ~90 MB
    model in CI, so when the model is absent this test skips rather than
    failing or downloading. `try_to_load_from_cache` asks the hub cache
    without any network call.
    """
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
def prewarmed_server(tmp_path_factory):
    if not sentence_transformers_available():
        pytest.skip("sentence-transformers not installed; prewarm cannot run")
    if not model_is_cached():
        pytest.skip(
            f"embedding model {HF_REPO!r} is not in the local HuggingFace cache "
            f"and the smoke layer runs offline (HF_HUB_OFFLINE=1); "
            f"warm it with `huggingface-cli download {HF_REPO}` to run this test"
        )

    data_dir: Path = tmp_path_factory.mktemp("pyrite-smoke-prewarm")
    kb_dir = data_dir / "smoke-kb"
    seed_kb(kb_dir, "smoke", title="Analytical Engine", body="A mechanical computer.")
    server = start_server(
        data_dir,
        kbs=[{"name": "smoke", "path": str(kb_dir), "kb_type": "generic", "description": "smoke"}],
        env_extra={
            "PYRITE_PREWARM_EMBEDDINGS": "true",
            # Still no write-time embedding: the point is that STARTUP warms
            # the model, with no write anywhere in the picture.
            "PYRITE_AUTO_EMBED": "0",
        },
    )
    try:
        yield server
    finally:
        stop_server(server)


def test_health_reports_embeddings_ready_after_startup_without_any_write(prewarmed_server):
    """`embeddings.ready` must become true on its own.

    No entry is created, no search is issued -- the only thing that has
    happened is that the process started. If this stays false, the startup
    hook is missing again (PR #5) and every first request pays the cold start.
    """
    import time

    body: dict = {}
    deadline = time.monotonic() + PREWARM_TIMEOUT
    while time.monotonic() < deadline:
        resp = prewarmed_server.client.get("/health")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "embeddings" in body, (
            f"PYRITE_PREWARM_EMBEDDINGS=true but /health reports no embeddings block at all: {body}"
        )
        if body["embeddings"].get("ready"):
            return
        time.sleep(0.5)

    pytest.fail(
        f"/health still reports embeddings.ready={body.get('embeddings')} after "
        f"{PREWARM_TIMEOUT}s with PYRITE_PREWARM_EMBEDDINGS=true and no write "
        f"issued. Nothing called EmbeddingService.prewarm() at startup "
        f"(PR #5's bug).\nServer output:\n{prewarmed_server.output()}"
    )


def test_health_omits_the_embeddings_block_when_prewarm_is_off(live_server):
    """The negative control: the flag is what turns the field on.

    Without this, a `/health` that hardcoded ready=true would pass the test
    above and mean nothing.
    """
    body = live_server.client.get("/health").json()
    assert body["status"] == "ok"
    assert "embeddings" not in body, body
