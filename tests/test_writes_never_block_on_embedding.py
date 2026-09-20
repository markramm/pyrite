"""A write enqueues; it never loads the embedding model (ADR-0035, #13).

`settings.auto_embed: true` used to mean *this write blocks until the entry is
embedded*. On a fresh install that meant the first `POST /api/entries`
imported torch and downloaded a ~90 MB sentence-transformers model inside the
HTTP request, and blocked for over a minute (#13). ADR-0035 changed the
promise: `auto_embed: true` guarantees the entry **will be** embedded, not
that it is embedded when the write returns.

Two things make this file's shape non-obvious, and both are the reason #13
went uncaught for so long:

1. **The suite runs with write-time embedding off.** The root `conftest.py`
   stubs `KBService._get_embedding_svc` to `None` and sets
   `PYRITE_AUTO_EMBED=0` for every test that does not carry
   `@pytest.mark.embeddings`. So an in-process test of "does a write embed?"
   asserts nothing at all unless it opts back in. The cold-process checks
   below opt in by running in a **subprocess** with the suite's stubs absent.

2. **Every developer machine has the model cached**, so a wall-clock bound
   alone passes no matter what the code does. The cold-cache regime is
   simulated honestly instead: `HF_HOME` points at an empty directory and
   `HF_HUB_OFFLINE=1` blocks the network, which is what a fresh install looks
   like before the download. Measured on the pre-fix code that combination
   makes one `create_entry` take ~7.5 s and import ~1270 `torch` /
   `sentence_transformers` modules; post-fix it must import **zero** and
   return in milliseconds.

The load-bearing assertion is the module count, not the clock: it is false on
a warm machine too, the moment a write takes the synchronous branch.
"""

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.services.kb_service import KBService
from pyrite.storage.database import PyriteDB

HEAVY_PREFIXES = ("torch", "sentence_transformers")

# Generous: on the pre-fix code this probe spends ~7.5 s inside the failing
# model load, and on a fresh install with a network it spends over a minute
# downloading. The bound exists to stop a hang, not to measure anything.
PROBE_TIMEOUT = 180.0


# ---------------------------------------------------------------------------
# Cold-process probe: the only honest way to ask "did this write load a model?"
# ---------------------------------------------------------------------------

PROBE = textwrap.dedent(
    """
    import json, sys, tempfile, time
    from pathlib import Path
    from pyrite.config import KBConfig, PyriteConfig, Settings
    from pyrite.services.kb_service import KBService
    from pyrite.storage.database import PyriteDB

    auto_embed = json.loads(sys.argv[1])
    d = Path(tempfile.mkdtemp())
    (d / "kb").mkdir()
    config = PyriteConfig(
        knowledge_bases=[KBConfig(name="t", path=d / "kb", kb_type="generic")],
        settings=Settings(index_path=d / "i.db", auto_embed=auto_embed),
    )
    db = PyriteDB(config.settings.index_path)
    svc = KBService(config, db)

    started = time.monotonic()
    svc.create_entry("t", "kestrel-notes", "Kestrel Notes", "note", "about falcons")
    elapsed = time.monotonic() - started

    heavy = [m for m in sys.modules if m.startswith(("torch", "sentence_transformers"))]
    try:
        queued = db._raw_conn.execute(
            "SELECT entry_id, kb_name, status FROM embed_queue"
        ).fetchall()
        queued = [tuple(r) for r in queued]
    except Exception:
        queued = []
    keyword_hits = [h["id"] for h in db.search("Kestrel", kb_name="t")]

    print("PROBE" + json.dumps({
        "elapsed": elapsed,
        "heavy": len(heavy),
        "queued": queued,
        "keyword_hits": keyword_hits,
        "vec_available": bool(db.vec_available),
    }))
    """
)


def run_cold_probe(tmp_path: Path, *, auto_embed: bool) -> dict:
    """One `create_entry` in a cold interpreter with an empty HF cache, offline.

    Runs out of process on purpose: the suite's autouse fixture neutralises
    write-time embedding in-process, so an in-process assertion about model
    loading is vacuous. A subprocess sees the production code path.
    """
    import os

    hf_home = tmp_path / "empty-hf-cache"
    hf_home.mkdir(parents=True, exist_ok=True)

    env = dict(os.environ)
    env.pop("PYRITE_AUTO_EMBED", None)  # the probe passes it explicitly
    env.update(
        {
            "HF_HOME": str(hf_home),
            "HUGGINGFACE_HUB_CACHE": str(hf_home / "hub"),
            "TRANSFORMERS_CACHE": str(hf_home / "hub"),
            # A fresh install before the download: nothing cached, no network.
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
        }
    )

    proc = subprocess.run(
        [sys.executable, "-c", PROBE, json.dumps(auto_embed)],
        env=env,
        capture_output=True,
        text=True,
        timeout=PROBE_TIMEOUT,
    )
    assert proc.returncode == 0, f"probe failed:\n{proc.stdout}\n{proc.stderr}"
    line = next((ln for ln in proc.stdout.splitlines() if ln.startswith("PROBE")), None)
    assert line, f"probe produced no result line:\n{proc.stdout}\n{proc.stderr}"
    return json.loads(line[len("PROBE") :])


@pytest.fixture(scope="module")
def cold_write(tmp_path_factory) -> dict:
    """One cold write with `auto_embed: true` — the #13 scenario."""
    return run_cold_probe(tmp_path_factory.mktemp("cold-write"), auto_embed=True)


class TestColdWriteNeverLoadsTheModel:
    """The regime #13 was filed against: empty HF cache, no network."""

    def test_the_write_imports_no_embedding_stack(self, cold_write):
        """The assertion that would have caught #13 on a warm machine too."""
        assert cold_write["heavy"] == 0, (
            "create_entry imported the embedding stack inside the write "
            f"({cold_write['heavy']} torch/sentence_transformers modules). "
            "ADR-0035: a write enqueues, it does not embed."
        )

    def test_the_write_returns_in_under_two_seconds(self, cold_write):
        """Issue #13's acceptance bound, measured on the cold path."""
        assert cold_write["elapsed"] < 2.0, (
            f"create_entry took {cold_write['elapsed']:.2f}s with an empty HF "
            "cache and no network; on a fresh install with a network that is "
            "the ~90 MB download happening inside the write (#13)."
        )

    def test_the_entry_is_immediately_keyword_searchable(self, cold_write):
        """Eventually-embedded must not mean eventually-indexed."""
        assert "kestrel-notes" in cold_write["keyword_hits"], cold_write

    def test_the_debt_is_recorded_as_pending(self, cold_write):
        """Skipping the embed is only acceptable if the debt is visible."""
        if not cold_write["vec_available"]:
            pytest.skip("sqlite-vec unavailable; nothing would be embeddable anyway")
        assert cold_write["queued"] == [("kestrel-notes", "t", "pending")], cold_write


class TestAutoEmbedOffIsUnchanged:
    """ADR-0035 §4: `auto_embed: false` keeps its present meaning exactly.

    Off means nothing in the embedding stack is touched *and* nothing is
    enqueued. The suite's 3m37s -> 45 s win depends on the first half; the
    second half is what stops this change from quietly re-enabling work the
    operator switched off.
    """

    def test_off_touches_nothing_and_enqueues_nothing(self, tmp_path_factory):
        result = run_cold_probe(tmp_path_factory.mktemp("cold-off"), auto_embed=False)
        assert result["heavy"] == 0, result
        assert result["queued"] == [], result
        assert "kestrel-notes" in result["keyword_hits"], result


# ---------------------------------------------------------------------------
# In-process: the queue mechanics, which need no model and no subprocess
# ---------------------------------------------------------------------------


def _svc(tmp_path, **settings):
    kb_path = tmp_path / "kb"
    kb_path.mkdir(exist_ok=True)
    kb = KBConfig(name="t", path=kb_path, kb_type="generic")
    config = PyriteConfig(
        knowledge_bases=[kb], settings=Settings(index_path=tmp_path / "i.db", **settings)
    )
    return KBService(config, PyriteDB(config.settings.index_path))


def queue_rows(db):
    try:
        return [
            tuple(r)
            for r in db._raw_conn.execute("SELECT entry_id, kb_name, status FROM embed_queue")
        ]
    except Exception:  # table absent == nothing was enqueued
        return []


@pytest.mark.embeddings
class TestEveryWritePathEnqueues:
    """All four `_auto_embed` call sites, not just `create_entry`.

    Marked `embeddings` so the suite's autouse stub is out of the way and the
    real `_auto_embed` runs. No model is loaded because enqueueing is the
    whole point — if one ever were, `test_no_write_path_loads_a_model` below
    would fail.
    """

    def test_create_update_and_bulk_create_all_record_pending_rows(self, tmp_path):
        svc = _svc(tmp_path, auto_embed=True)
        svc.create_entry("t", "one", "One", "note", "first")
        svc.update_entry("one", "t", body="first, revised")
        svc.bulk_create_entries("t", [{"entry_type": "note", "title": "Two", "body": "second"}])

        ids = {row[0] for row in queue_rows(svc.db)}
        assert {"one", "two"} <= ids, ids

    def test_no_write_path_loads_a_model(self, tmp_path):
        svc = _svc(tmp_path, auto_embed=True)
        before = {m for m in list(sys.modules) if m.startswith(HEAVY_PREFIXES)}

        svc.create_entry("t", "one", "One", "note", "first")
        svc.update_entry("one", "t", body="revised")
        svc.bulk_create_entries("t", [{"entry_type": "note", "title": "Two", "body": "second"}])

        new_heavy = {m for m in list(sys.modules) if m.startswith(HEAVY_PREFIXES)} - before
        assert not new_heavy, sorted(new_heavy)


class TestDrainingTheQueue:
    """The other half of the promise: the debt is drainable."""

    def test_drain_embeds_pending_rows_and_empties_the_queue(self, tmp_path):
        from unittest.mock import MagicMock

        from pyrite.services.embedding_worker import EmbeddingWorker

        svc = _svc(tmp_path, auto_embed=True)
        worker = EmbeddingWorker(svc.db)
        worker.enqueue("one", "t")
        worker.enqueue("two", "t")
        worker._embedding_svc = MagicMock(**{"embed_entry.return_value": True})

        embedded = worker.drain()

        assert embedded == 2
        assert worker.get_status()["pending"] == 0

    def test_drain_crosses_batch_boundaries(self, tmp_path):
        """More pending rows than one batch: drain keeps going."""
        from unittest.mock import MagicMock

        from pyrite.services.embedding_worker import EmbeddingWorker

        svc = _svc(tmp_path, auto_embed=True)
        worker = EmbeddingWorker(svc.db)
        for i in range(7):
            worker.enqueue(f"e{i}", "t")
        worker._embedding_svc = MagicMock(**{"embed_entry.return_value": True})

        assert worker.drain(batch_size=2) == 7
        assert worker.get_status()["total"] == 0

    def test_drain_stops_on_a_batch_that_makes_no_progress(self, tmp_path):
        """A failing embed must not spin drain() forever."""
        from unittest.mock import MagicMock

        from pyrite.services.embedding_worker import EmbeddingWorker

        svc = _svc(tmp_path, auto_embed=True)
        worker = EmbeddingWorker(svc.db, max_attempts=3)
        worker.enqueue("one", "t")
        worker._embedding_svc = MagicMock(
            **{"embed_entry.side_effect": RuntimeError("model unavailable")}
        )

        embedded = worker.drain()

        assert embedded == 0
        assert worker.get_status()["failed"] == 1

    def test_drain_is_a_noop_without_an_embedding_service(self, tmp_path):
        """Offline with no model: rows stay pending, nothing raises."""
        from pyrite.services.embedding_worker import EmbeddingWorker

        svc = _svc(tmp_path, auto_embed=True)
        worker = EmbeddingWorker(svc.db)
        worker.enqueue("one", "t")
        worker._get_embedding_svc = lambda: None

        assert worker.drain() == 0
        assert worker.get_status()["pending"] == 1
