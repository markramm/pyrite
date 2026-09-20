"""Semantic search on an unembedded KB says so instead of returning a silent [].

ADR-0035 §5. Once a write only *enqueues*, "semantic search found nothing" has
a new and very common cause: nothing has been embedded yet. Before this, the
two were indistinguishable from the outside -- `SearchService.search` recorded
`reason: "semantic_empty_no_embeddings"` in its internal trace and returned an
empty list, so a user on a fresh install saw `[]` and had no way to learn that
the fix was one `pyrite index embed` away.

This is the clause that makes ADR-0035 safe rather than merely fast: it is the
signal that would have surfaced, in the field, both of the ways the first pass
let the queue report zero debt while nothing was embedded.

It reuses the `warnings: list[str]` out-parameter and response field from PR
#145 -- no new mechanism. The convention that file established: an empty
`warnings` is *absent* on every surface (MCP omits the key, REST omits it, the
CLI prints nothing), so a caller may test presence but never truthiness.

No model is loaded anywhere here. `_semantic_search` returns early on
`has_embeddings()` being False, which is precisely the state under test.
"""

from __future__ import annotations

import pytest

from pyrite.config import KBType
from pyrite.services.search_service import SearchService
from pyrite.storage.database import PyriteDB


@pytest.fixture
def db_with_entries_but_no_embeddings(tmp_path):
    db = PyriteDB(tmp_path / "i.db")
    db.register_kb("t", KBType.GENERIC, str(tmp_path / "kb"))
    db.upsert_entry(
        {
            "id": "kestrel",
            "kb_name": "t",
            "entry_type": "note",
            "title": "Kestrel Notes",
            "summary": "",
            "body": "Field notes on a small falcon that hovers while hunting.",
            "tags": [],
        }
    )
    yield db
    db.close()


def _search(db, mode, warnings):
    return SearchService(db).search("birds of prey", mode=mode, warnings=warnings)


class TestTheEmptyResultExplainsItself:
    def test_semantic_search_warns_and_names_the_command(self, db_with_entries_but_no_embeddings):
        warnings: list[str] = []
        results = _search(db_with_entries_but_no_embeddings, "semantic", warnings)

        assert results == [], "precondition: nothing is embedded, so nothing matches"
        assert warnings, (
            "semantic search returned a silent [] on a KB with entries and no "
            "embeddings. ADR-0035 §5: this must say so."
        )
        joined = " ".join(warnings).lower()
        assert "pyrite index embed" in joined, (
            f"the warning must name the command that fixes it: {warnings}"
        )
        assert "embed" in joined

    def test_hybrid_search_warns_too(self, db_with_entries_but_no_embeddings):
        """Hybrid is the default mode for `kb_search`, so it matters most.

        Hybrid still returns the keyword leg's hits, which is exactly why the
        warning is needed: results come back and look fine, while half the
        search silently did not run.
        """
        warnings: list[str] = []
        # A query that really does hit the keyword leg, so the point of the
        # test is the *warning beside real results*, not an empty response.
        results = SearchService(db_with_entries_but_no_embeddings).search(
            "falcon", mode="hybrid", warnings=warnings
        )

        assert any(r["id"] == "kestrel" for r in results), (
            f"the keyword leg should still hit: {results}"
        )
        assert any("embed" in w.lower() for w in warnings), (
            f"hybrid ran with a dead vector leg and said nothing: {warnings}"
        )


class TestTheWarningIsNotNoise:
    """A warning that fires when embeddings exist would train people to ignore it."""

    def test_keyword_search_never_warns_about_embeddings(self, db_with_entries_but_no_embeddings):
        warnings: list[str] = []
        _search(db_with_entries_but_no_embeddings, "keyword", warnings)
        assert not any("embed" in w.lower() for w in warnings), warnings

    def test_no_warning_once_the_kb_has_embeddings(self, db_with_entries_but_no_embeddings):
        db = db_with_entries_but_no_embeddings
        if not db.vec_available:
            pytest.skip("sqlite-vec unavailable; cannot create an embedding")
        db.backend.upsert_embedding("kestrel", "t", [0.01] * 384)

        warnings: list[str] = []
        _search(db, "semantic", warnings)

        assert not any("index embed" in w.lower() for w in warnings), (
            f"warned about missing embeddings on a KB that has them: {warnings}"
        )

    def test_an_empty_kb_does_not_warn(self, tmp_path):
        """Nothing indexed at all is not an embedding problem.

        Telling someone to run `pyrite index embed` when the real answer is
        `pyrite index build` sends them down the wrong path.
        """
        db = PyriteDB(tmp_path / "empty.db")
        db.register_kb("t", KBType.GENERIC, str(tmp_path / "kb"))

        warnings: list[str] = []
        _search(db, "semantic", warnings)

        assert not any("index embed" in w.lower() for w in warnings), warnings
        db.close()


@pytest.mark.api
class TestTheWarningReachesTheRestSurface:
    """PR #145's response field is how a caller actually sees this."""

    def test_rest_search_includes_the_warning(self, tmp_path):
        pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient

        from pyrite.config import KBConfig, PyriteConfig, Settings
        from pyrite.server.api import create_app, get_config, get_db
        from pyrite.services.kb_service import KBService

        kb_path = tmp_path / "kb"
        kb_path.mkdir()
        config = PyriteConfig(
            knowledge_bases=[KBConfig(name="t", path=kb_path, kb_type="generic")],
            settings=Settings(index_path=tmp_path / "i.db", auto_embed=True),
        )
        db = PyriteDB(config.settings.index_path)
        KBService(config, db).create_entry("t", "kestrel", "Kestrel Notes", "note", "falcons")

        app = create_app(config=config)
        app.dependency_overrides[get_config] = lambda: config
        app.dependency_overrides[get_db] = lambda: db
        client = TestClient(app)

        body = client.get(
            "/api/search", params={"q": "birds of prey", "kb": "t", "mode": "semantic"}
        ).json()

        assert "warnings" in body, (
            f"a semantic search with nothing embedded returned no warnings key: {body}"
        )
        assert any("index embed" in w.lower() for w in body["warnings"]), body["warnings"]
        db.close()
