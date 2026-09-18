"""Filters are honoured on every search leg — the filter x mode matrix (#56, #53).

``kb_search`` defaults to ``mode="hybrid"``. Historically ``entry_type``,
``tags``, ``state`` and ``fips`` were compiled only into the FTS/SQL leg's
``WHERE``; the vector leg was queried with ``kb_name`` alone and the two legs
fused, so a filtered hybrid or semantic search silently returned entries the
filter excluded. These tests pin the contract for every filter in every mode:

* a bogus filter value returns **0** results in keyword, semantic and hybrid;
* a valid filter value returns **only** matching entries in all three modes.

The semantic leg is exercised with a deterministic stub embedder (see
``_StubEmbedder``) rather than sentence-transformers: what is under test is
where the filter predicate is applied, not the quality of the model. The stub
gives every entry a real 384-dim vector, so the sqlite-vec KNN leg runs for
real and returns *every* entry as a candidate — which is exactly the condition
that made the unfiltered vector leg leak wrong-typed entries into the fused set.
"""

import tempfile
from pathlib import Path

import pytest

from pyrite.config import KBType
from pyrite.services.search_service import SearchService
from pyrite.storage.database import PyriteDB

MODES = ["keyword", "semantic", "hybrid"]

# Entries share the word "detention" so the FTS leg matches all of them; they
# differ only in the filterable columns. Any leak across a filter is therefore
# a filter bug, never a relevance artefact.
ENTRIES = [
    {
        "id": "mech-bypass",
        "entry_type": "mechanism",
        "title": "Detention oversight bypass",
        "summary": "A detention mechanism entry",
        "body": "detention accountability bypass mechanism",
        "tags": ["oversight", "detention"],
        "state": "MI",
        "fips": "26163",
        "status": "unprocessed",
    },
    {
        "id": "theme-capture",
        "entry_type": "theme",
        "title": "Detention capture theme",
        "summary": "A detention theme entry",
        "body": "detention accountability capture theme",
        "tags": ["capture"],
        "state": "LA",
        "fips": "22071",
        "status": "processed",
    },
    {
        "id": "task-ticket",
        "entry_type": "task",
        "title": "Detention bookkeeping task",
        "summary": "A detention task entry",
        "body": "detention workflow bookkeeping task",
        "tags": ["workflow"],
        "state": None,
        "fips": None,
        "status": "unprocessed",
    },
]

# (filter kwarg, valid value, the entry ids it must return, a bogus value)
FILTER_CASES = [
    ("entry_type", "mechanism", {"mech-bypass"}, "zzz-not-a-real-type"),
    ("tags", ["capture"], {"theme-capture"}, ["zzz-no-such-tag"]),
    ("state", "MI", {"mech-bypass"}, "ZZ"),
    ("fips", "26163", {"mech-bypass"}, "99999"),
    ("status", "processed", {"theme-capture"}, "zzz-bogus-status"),
]


class _StubEmbedder:
    """Deterministic 384-dim embeddings — no model download, no wall clock.

    Every vector is near-identical (a fixed base with a tiny per-text nudge),
    so the KNN leg ranks *all* embedded entries within ``max_distance``. That
    is deliberate: it makes the vector leg offer every entry as a candidate, so
    a filter that is not applied on that leg shows up immediately as a leak.
    """

    def __init__(self, *args, **kwargs):
        pass

    def embed_text(self, text: str) -> list[float]:
        vec = [0.05] * 384
        vec[hash(text) % 384] += 0.001
        return vec


def _populate(db):
    """Index ENTRIES into ``db`` and give each a stub embedding."""
    import pyrite.services.embedding_service as es

    embedder = es.EmbeddingService(db)
    for spec in ENTRIES:
        entry = dict(spec)
        entry["kb_name"] = "test-kb"
        entry.setdefault("sources", [])
        entry.setdefault("links", [])
        db.upsert_entry(entry)
        db.backend.upsert_embedding(entry["id"], "test-kb", embedder.embed_text(entry["title"]))
    assert db.backend.has_embeddings(), "fixture must have embeddings for the vector leg"


@pytest.fixture
def stub_embeddings(monkeypatch):
    """Swap sentence-transformers for the deterministic stub."""
    import pyrite.services.embedding_service as es

    monkeypatch.setattr(es, "is_available", lambda: True)
    monkeypatch.setattr(es.EmbeddingService, "_get_model", lambda self: _StubEmbedder())
    monkeypatch.setattr(es.EmbeddingService, "embed_text", _StubEmbedder().embed_text)


@pytest.fixture
def svc_db(stub_embeddings):
    """A PyriteDB with vec support, the entries above, and stub embeddings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db = PyriteDB(Path(tmpdir) / "test.db")
        if not db.vec_available:
            db.close()
            pytest.skip("sqlite-vec not available")
        db.register_kb("test-kb", KBType.RESEARCH, "/tmp/test-kb")
        _populate(db)
        yield db
        db.close()


@pytest.fixture
def cli_index(stub_embeddings, tmp_path, monkeypatch):
    """A real on-disk index plus the PyriteConfig the CLI will load for it."""
    from pyrite.config import KBConfig, PyriteConfig, Settings

    kb_path = tmp_path / "test-kb"
    kb_path.mkdir()
    index_path = tmp_path / "index.db"

    db = PyriteDB(index_path)
    if not db.vec_available:
        db.close()
        pytest.skip("sqlite-vec not available")
    db.register_kb("test-kb", KBType.RESEARCH, str(kb_path))
    _populate(db)
    db.close()

    config = PyriteConfig(
        knowledge_bases=[KBConfig(name="test-kb", path=kb_path, kb_type="research")],
        settings=Settings(index_path=index_path),
    )
    # The staleness probe compares the index against files on disk; there are
    # no files here (entries were inserted directly), so silence it.
    monkeypatch.setattr("pyrite.cli.search_commands._warn_if_stale", lambda *a, **kw: None)
    yield config, index_path


@pytest.fixture
def svc(svc_db):
    return SearchService(svc_db)


def _ids(results):
    return {r["id"] for r in results}


# =========================================================================
# The matrix: every filter, every mode
# =========================================================================


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    "filter_name,valid,expected_ids,bogus",
    FILTER_CASES,
    ids=[c[0] for c in FILTER_CASES],
)
def test_bogus_filter_value_returns_nothing(svc, mode, filter_name, valid, expected_ids, bogus):
    """A filter value nothing matches must return 0 results in every mode.

    This is the #56/#53 reproduction: in hybrid and semantic these returned a
    full, plausible-looking result set.
    """
    results = svc.search("detention", kb_name="test-kb", mode=mode, **{filter_name: bogus})
    assert results == [], f"{filter_name}={bogus!r} in mode={mode} leaked {_ids(results)}"


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    "filter_name,valid,expected_ids,bogus",
    FILTER_CASES,
    ids=[c[0] for c in FILTER_CASES],
)
def test_valid_filter_value_returns_only_matches(
    svc, mode, filter_name, valid, expected_ids, bogus
):
    """A valid filter value must return only matching entries in every mode.

    ``--type theme`` returning a ``mechanism`` proves the leak independently of
    the bogus-value test (#53).
    """
    results = svc.search("detention", kb_name="test-kb", mode=mode, **{filter_name: valid})
    assert _ids(results) == expected_ids, (
        f"{filter_name}={valid!r} in mode={mode} returned {_ids(results)}"
    )


@pytest.mark.parametrize("mode", MODES)
def test_combined_filters_intersect(svc, mode):
    """Two filters together narrow to their intersection, in every mode."""
    results = svc.search(
        "detention", kb_name="test-kb", mode=mode, entry_type="mechanism", state="MI"
    )
    assert _ids(results) == {"mech-bypass"}

    # Contradictory pair — mechanism is MI, not LA — must be empty, not fused.
    results = svc.search(
        "detention", kb_name="test-kb", mode=mode, entry_type="mechanism", state="LA"
    )
    assert results == []


@pytest.mark.parametrize("mode", MODES)
def test_no_filter_returns_everything(svc, mode):
    """Guard against over-filtering: with no filters all three entries match."""
    results = svc.search("detention", kb_name="test-kb", mode=mode, limit=10)
    assert _ids(results) == {"mech-bypass", "theme-capture", "task-ticket"}


def test_semantic_leg_alone_honours_filters(svc_db):
    """The vector leg itself filters — not just the service that fuses it.

    Pinned at the backend boundary so a future caller of ``search_semantic``
    cannot reintroduce the leak by bypassing SearchService.
    """
    embedding = _StubEmbedder().embed_text("detention")
    rows = svc_db.backend.search_semantic(
        embedding, kb_name="test-kb", limit=10, entry_type="mechanism"
    )
    assert {r["id"] for r in rows} == {"mech-bypass"}

    rows = svc_db.backend.search_semantic(
        embedding, kb_name="test-kb", limit=10, entry_type="zzz-not-a-real-type"
    )
    assert rows == []


def _undeclare_filtered_semantic(backend, monkeypatch):
    """Model a backend whose vector leg cannot honour filters.

    The service asks the backend's declared capability set, so that is what a
    stand-in must change. Raising ``TypeError`` from ``search_semantic`` — what
    an earlier draft of these tests did — no longer models anything: it is a
    genuine bug, and the service is now required to let it through.
    """
    from pyrite.storage.backends.capabilities import BackendCapability

    cls = type(backend)
    reduced = set(cls.capabilities) - {BackendCapability.FILTERED_SEMANTIC}
    monkeypatch.setattr(cls, "capabilities", reduced)


# =========================================================================
# Warnings: a filter a leg cannot honour is named, never dropped silently
# =========================================================================


def test_no_warnings_when_every_filter_is_honoured(svc):
    """The happy path carries no warnings — warnings mean something was dropped."""
    warnings: list[str] = []
    svc.search(
        "detention", kb_name="test-kb", mode="hybrid", entry_type="mechanism", warnings=warnings
    )
    assert warnings == []


def test_warning_when_a_leg_cannot_honour_a_filter(svc, monkeypatch):
    """A backend whose vector leg cannot filter reports it rather than lying.

    Simulates a backend without filtered-KNN support — one that does not
    declare ``FILTERED_SEMANTIC``: the semantic leg is dropped from the fused
    set and the caller is told which filters caused it.
    """
    _undeclare_filtered_semantic(svc.db.backend, monkeypatch)

    warnings: list[str] = []
    results = svc.search(
        "detention", kb_name="test-kb", mode="hybrid", entry_type="mechanism", warnings=warnings
    )
    # Still correct — never entries the filter excluded.
    assert _ids(results) <= {"mech-bypass"}
    assert warnings, "a dropped semantic leg must be reported, not silent"
    assert any("entry_type" in w for w in warnings), warnings


def test_unfilterable_backend_never_leaks_in_semantic_mode(svc, monkeypatch):
    """In pure semantic mode a leg that cannot filter returns nothing, not lies.

    There is no keyword leg to fall back on, so the honest answer is zero
    results plus a warning — never the unfiltered set that caused #56.
    """
    _undeclare_filtered_semantic(svc.db.backend, monkeypatch)

    warnings: list[str] = []
    results = svc.search(
        "detention", kb_name="test-kb", mode="semantic", entry_type="mechanism", warnings=warnings
    )
    assert results == []
    assert any("entry_type" in w for w in warnings), warnings


@pytest.mark.parametrize(
    "filters", [{}, {"entry_type": "mechanism"}], ids=["unfiltered", "filtered"]
)
def test_a_backend_type_error_always_propagates(svc, monkeypatch, filters):
    """A ``TypeError`` from the backend is a bug, filter or no filter.

    There is no rescue left to scope: whether the vector leg can filter is a
    declared capability, checked before the call, so an exception out of the
    call itself is never evidence about capabilities. The filtered case is the
    regression — it used to be swallowed and relabelled.
    """

    def _broken(self, embedding, kb_name=None, limit=20, max_distance=1.3, **kwargs):
        raise TypeError("a real bug in the backend")

    monkeypatch.setattr(type(svc.db.backend), "search_semantic", _broken)

    with pytest.raises(TypeError, match="a real bug"):
        svc.search("detention", kb_name="test-kb", mode="semantic", **filters)


def test_warnings_reach_the_mcp_response(svc_db, monkeypatch):
    """``kb_search`` carries ``warnings`` when a leg was dropped, and omits the
    key entirely on the happy path (#56 acceptance 4)."""
    from pyrite.server.mcp_server import PyriteMCPServer

    server = PyriteMCPServer.__new__(PyriteMCPServer)
    server._search_svc_cache = SearchService(svc_db)
    monkeypatch.setattr(
        type(server), "search_svc", property(lambda self: self._search_svc_cache), raising=False
    )

    clean = server._kb_search({"query": "detention", "kb_name": "test-kb", "mode": "hybrid"})
    assert "warnings" not in clean, clean

    _undeclare_filtered_semantic(svc_db.backend, monkeypatch)
    noisy = server._kb_search(
        {
            "query": "detention",
            "kb_name": "test-kb",
            "mode": "hybrid",
            "entry_type": "mechanism",
        }
    )
    assert noisy["warnings"], noisy
    assert any("entry_type" in w for w in noisy["warnings"])


# =========================================================================
# The public entry points reach the same service
# =========================================================================


@pytest.fixture
def rest_client(svc_db):
    """A TestClient whose /api/search reaches the populated index."""
    from fastapi.testclient import TestClient

    from pyrite.server.api import (
        create_app,
        get_kb_service,
        get_readable_kbs,
        get_search_service,
    )

    app = create_app()
    app.dependency_overrides[get_search_service] = lambda: SearchService(svc_db)
    app.dependency_overrides[get_readable_kbs] = lambda: None

    class _StubKBService:
        def count_entries(self, *a, **kw):
            return len(ENTRIES)

    app.dependency_overrides[get_kb_service] = lambda: _StubKBService()
    return TestClient(app)


def test_rest_search_endpoint_honours_type_filter_in_hybrid(rest_client):
    """GET /api/search with mode=hybrid applies ``type`` (#56 acceptance 3)."""
    client = rest_client
    resp = client.get(
        "/api/search", params={"q": "detention", "kb": "test-kb", "mode": "hybrid", "type": "theme"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert {r["id"] for r in body["results"]} == {"theme-capture"}

    resp = client.get(
        "/api/search",
        params={"q": "detention", "kb": "test-kb", "mode": "hybrid", "type": "zzz-not-a-real-type"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["results"] == []


def test_rest_search_omits_warnings_on_the_happy_path(rest_client):
    """``warnings`` is null/absent when every filter was applied everywhere."""
    resp = rest_client.get(
        "/api/search",
        params={"q": "detention", "kb": "test-kb", "mode": "hybrid", "type": "theme"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json().get("warnings") in (None, [])


def test_rest_search_reports_a_dropped_leg_in_warnings(rest_client, svc_db, monkeypatch):
    """A filter a leg cannot honour reaches the REST caller as ``warnings``."""

    _undeclare_filtered_semantic(svc_db.backend, monkeypatch)

    resp = rest_client.get(
        "/api/search",
        params={"q": "detention", "kb": "test-kb", "mode": "hybrid", "type": "mechanism"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["warnings"], body
    assert any("entry_type" in w for w in body["warnings"])
    # Correct despite the dropped leg — never an entry the filter excluded.
    assert {r["id"] for r in body["results"]} <= {"mech-bypass"}


def test_cli_search_honours_type_filter_in_hybrid(cli_index, monkeypatch):
    """``pyrite search --type`` applies in hybrid mode (#53 acceptance 3)."""
    import json
    from unittest.mock import patch

    from typer.testing import CliRunner

    from pyrite.cli import app

    config, _index_path = cli_index
    runner = CliRunner()
    with patch("pyrite.cli.search_commands.load_config", return_value=config):
        result = runner.invoke(
            app,
            [
                "search",
                "detention",
                "-k",
                "test-kb",
                "-m",
                "hybrid",
                "--type",
                "theme",
                "--format",
                "json",
            ],
        )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert {r["id"] for r in payload["results"]} == {"theme-capture"}

    with patch("pyrite.cli.search_commands.load_config", return_value=config):
        result = runner.invoke(
            app,
            [
                "search",
                "detention",
                "-k",
                "test-kb",
                "-m",
                "hybrid",
                "--type",
                "zzz-not-a-real-type",
                "--format",
                "json",
            ],
        )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["results"] == []


def test_a_bug_inside_the_vector_leg_propagates_even_with_a_filter(svc, monkeypatch):
    """The dropped-leg path must be a declared capability, not a caught TypeError.

    ``_semantic_search`` wrapped the whole of ``search_similar`` — embedding the
    query, the backend call, *and* snippet generation — in ``except TypeError``.
    With a filter active, any genuine ``TypeError`` from any of those turned
    into "this backend cannot filter" and a silently empty semantic leg. Here
    the backend filters perfectly and the bug is in snippet generation: it must
    reach the caller, not be relabelled.
    """
    import pyrite.services.embedding_service as es

    def _boom(*args, **kwargs):
        raise TypeError("a real bug in snippet generation")

    monkeypatch.setattr(es, "_generate_snippet", _boom)

    with pytest.raises(TypeError, match="a real bug in snippet generation"):
        svc.search("detention", kb_name="test-kb", mode="semantic", entry_type="mechanism")


def test_backend_without_the_capability_drops_the_leg_with_a_warning(svc, monkeypatch):
    """A backend that does not declare FILTERED_SEMANTIC is checked up front.

    No exception is raised and none is caught: the capability set says the
    vector leg cannot honour the filter, so the leg is dropped before it runs
    and the caller is told which filters cost it.
    """
    from pyrite.storage.backends.capabilities import BackendCapability

    backend_cls = type(svc.db.backend)
    reduced = set(backend_cls.capabilities) - {BackendCapability.FILTERED_SEMANTIC}
    monkeypatch.setattr(backend_cls, "capabilities", reduced)

    warnings: list[str] = []
    results = svc.search(
        "detention", kb_name="test-kb", mode="semantic", entry_type="mechanism", warnings=warnings
    )
    assert results == []
    assert any("entry_type" in w for w in warnings), warnings


def test_sqlite_declares_filtered_semantic(svc):
    """The in-tree backends honour every filter on the vector leg, so they say so."""
    from pyrite.storage.backends.capabilities import BackendCapability

    assert BackendCapability.FILTERED_SEMANTIC in type(svc.db.backend).capabilities
