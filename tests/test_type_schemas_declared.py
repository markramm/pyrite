"""#392: `GET /api/entries/type-schemas` reports the KB's declared types.

`declared` is additive -- the existing `types` map is untouched, so a caller
that ignores the new field keeps working. It is the KB's own `kb.yaml`
vocabulary (`KBSchema.types`, the same set `_refuse_undeclared_type` checks
against, #378): non-empty only when the KB declares any type. A KB with no
`kb.yaml` types section (or no `kb.yaml` at all) reports `declared: []`, so
the web form knows to offer everything and never send `allow_undeclared`.

The second test is the acceptance line from the issue's Groom section: the
New-entry form's default payload, POSTed against a copy of Pyrite's own
`kb/kb.yaml`, succeeds without `allow_undeclared` -- because the default is
now a declared type, not the hardcoded `note`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")

from starlette.testclient import TestClient

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.server.api import create_app, get_config, get_db, get_index_worker
from pyrite.services.index_worker import IndexWorker
from pyrite.storage.database import PyriteDB
from pyrite.storage.index import IndexManager

#: Pyrite's own kb/kb.yaml -- declares component, adr, backlog_item, standard.
#: Not `note`: a web user of this repo is exactly the #197 hazard #392 closes.
PYRITE_KB_YAML = (Path(__file__).resolve().parent.parent / "kb" / "kb.yaml").read_text()

UNDECLARED_KB_YAML = "name: plain\n"


def _kb_env(tmp_path, name, kb_type, kb_yaml):
    kb_path = tmp_path / name
    kb_path.mkdir()
    (kb_path / "kb.yaml").write_text(kb_yaml)
    db_path = tmp_path / f"{name}.db"
    config = PyriteConfig(
        knowledge_bases=[KBConfig(name=name, path=kb_path, kb_type=kb_type)],
        settings=Settings(index_path=db_path, auto_embed=False),
    )
    db = PyriteDB(db_path)
    IndexManager(db, config).index_all()
    db.close()
    return {"config": config, "kb_path": kb_path, "tmp_path": tmp_path, "db_path": db_path}


@pytest.fixture
def software_env(tmp_path):
    return _kb_env(tmp_path, "sw", "software", PYRITE_KB_YAML)


@pytest.fixture
def undeclared_env(tmp_path):
    return _kb_env(tmp_path, "plain", "generic", UNDECLARED_KB_YAML)


def _rest_for(env):
    config = env["config"]
    application = create_app(config=config)
    db = PyriteDB(env["db_path"])
    application.dependency_overrides[get_config] = lambda: config
    application.dependency_overrides[get_db] = lambda: db
    worker = IndexWorker(db, config)
    application.dependency_overrides[get_index_worker] = lambda: worker
    closers = [db]
    state_db = getattr(application.state, "pyrite_db", None)
    if state_db is not None and state_db is not db:
        closers.append(state_db)

    def close():
        worker.wait_for_idle(timeout=10)
        for d in closers:
            d.close()

    return TestClient(application), close


def test_type_schemas_reports_declared_types_for_a_typed_kb(software_env):
    client, close = _rest_for(software_env)
    try:
        resp = client.get("/api/entries/type-schemas?kb=sw")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        # additive: the existing `types` map is untouched
        assert "note" in data["types"]
        assert set(data["declared"]) == {"component", "adr", "backlog_item", "standard"}
    finally:
        close()


def test_type_schemas_declared_is_empty_for_a_kb_with_no_declared_types(undeclared_env):
    client, close = _rest_for(undeclared_env)
    try:
        resp = client.get("/api/entries/type-schemas?kb=plain")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["declared"] == []
        # every core type is still offered
        assert "note" in data["types"]
    finally:
        close()


def test_type_schemas_declared_is_empty_with_no_kb_named(software_env):
    """No `kb` query param -> no schema to consult -> nothing declared."""
    client, close = _rest_for(software_env)
    try:
        resp = client.get("/api/entries/type-schemas")
        assert resp.status_code == 200, resp.text
        assert resp.json()["declared"] == []
    finally:
        close()


def test_rest_create_the_forms_default_payload_succeeds_without_allow_undeclared(software_env):
    """The acceptance line from #392's Groom section: POST the New-entry
    form's default payload -- a declared type, not the hardcoded `note` --
    against a copy of Pyrite's own kb.yaml, and it succeeds with no
    `allow_undeclared` sent at all."""
    client, close = _rest_for(software_env)
    try:
        schemas = client.get("/api/entries/type-schemas?kb=sw").json()
        declared = schemas["declared"]
        assert declared, "software KB must declare at least one type"
        default_type = sorted(declared)[0]

        form = {"kb": "sw", "entry_type": default_type, "title": "From the form", "body": ""}
        resp = client.post("/api/entries", json=form)
        assert resp.status_code == 200, resp.text
        # Not a hardcoded filename: the default declared type (`adr`, #391)
        # can have its own `file_pattern`, so the file is not necessarily
        # `<id>.md` -- assert by frontmatter id instead of by name.
        entry_id = resp.json()["id"]
        id_line = f"id: {entry_id}"
        matches = [
            p
            for p in software_env["kb_path"].rglob("*.md")
            if any(line.strip() == id_line for line in p.read_text().splitlines())
        ]
        assert len(matches) == 1, (
            f"expected exactly one file with id: {entry_id!r}, found {matches}"
        )
    finally:
        close()
