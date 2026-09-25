"""The KBService write pipeline, through its surfaces (#378, #359, #366).

`tests/test_write_surface_parity.py` pins that every create surface refuses the
same spec with the same code. This file pins the rest of the theme:

- bulk create refuses an existing id per item, including a duplicate inside
  one batch, and leaves the existing file byte-identical (#359);
- bulk create applies schema *and plugin* validation per item, with the
  message `kb_create` gives, siblings still created in order (#366);
- MCP `kb_update` takes the entry type's own field set from the registry and
  the KB schema, not a hand-kept allowlist (#378 acceptance 5);
- REST create and update return the pipeline's warnings;
- `pyrite add` goes through the same pipeline (undeclared types refused).
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")

from typer.testing import CliRunner

from pyrite.cli import app as cli_app
from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.storage.database import PyriteDB
from pyrite.storage.index import IndexManager

runner = CliRunner()

KB = "pipe"

KB_YAML = """\
name: pipe
validation:
  enforce: true
types:
  person:
    fields:
      role:
        type: select
        options: [author, editor]
  finding:
    fields:
      severity:
        type: select
        options: [low, high]
  note:
    fields:
      mood:
        type: select
        options: [calm, busy]
        allow_other: true
"""


@pytest.fixture
def env(tmp_path):
    kb_path = tmp_path / KB
    kb_path.mkdir()
    (kb_path / "kb.yaml").write_text(KB_YAML)
    db_path = tmp_path / "index.db"
    config = PyriteConfig(
        knowledge_bases=[KBConfig(name=KB, path=kb_path, kb_type="generic")],
        settings=Settings(index_path=db_path, auto_embed=False),
    )
    db = PyriteDB(db_path)
    IndexManager(db, config).index_all()
    db.close()
    return {"config": config, "kb_path": kb_path, "tmp_path": tmp_path, "db_path": db_path}


@pytest.fixture
def mcp(env):
    from pyrite.server.mcp_server import PyriteMCPServer

    server = PyriteMCPServer(env["config"], tier="admin")
    yield server
    server.close()


def _cli(env, args):
    with (
        patch("pyrite.cli.load_config", return_value=env["config"]),
        patch("pyrite.cli.context.load_config", return_value=env["config"]),
    ):
        return runner.invoke(cli_app, args)


def _stop_enforcing(env):
    """Drop `validation.enforce`: with it on, an unknown type is a schema error
    even when the undeclared-type refusal is overridden (that is what enforce
    means), so the override is only observable in a non-enforcing KB."""
    (env["kb_path"] / "kb.yaml").write_text(KB_YAML.replace("validation:\n  enforce: true\n", ""))
    env["config"].get_kb(KB).invalidate_schema_cache()


def _file(env, entry_id):
    found = list(env["kb_path"].rglob(f"{entry_id}.md"))
    assert len(found) <= 1, found
    return found[0] if found else None


# ---------------------------------------------------------------------------
# #359: bulk create never replaces
# ---------------------------------------------------------------------------


def test_bulk_create_refuses_an_existing_id_and_leaves_the_file_byte_identical(env, mcp):
    first = mcp._dispatch_tool(
        "kb_bulk_create",
        {"kb_name": KB, "entries": [{"entry_type": "person", "title": "Ok", "body": "ORIGINAL"}]},
    )
    assert first["created"] == 1, first
    original = _file(env, "ok").read_bytes()

    res = mcp._dispatch_tool(
        "kb_bulk_create",
        {
            "kb_name": KB,
            "entries": [
                {"entry_type": "person", "title": "Before", "body": "b"},
                {"entry_type": "person", "title": "Ok", "body": "REPLACED"},
                {"entry_type": "person", "title": "After", "body": "b"},
            ],
        },
    )
    assert [r["created"] for r in res["results"]] == [True, False, True], res
    assert res["results"][1]["error_code"] == "ENTRY_EXISTS"
    single = mcp._dispatch_tool(
        "kb_create", {"kb_name": KB, "entry_type": "person", "title": "Ok", "body": "x"}
    )
    assert res["results"][1]["error"] == single["error"]
    assert _file(env, "ok").read_bytes() == original


def test_bulk_create_two_items_with_one_id_creates_the_first_and_refuses_the_second(env, mcp):
    res = mcp._dispatch_tool(
        "kb_bulk_create",
        {
            "kb_name": KB,
            "entries": [
                {"entry_type": "person", "title": "Twin", "body": "FIRST"},
                {"entry_type": "person", "title": "Twin", "body": "SECOND"},
            ],
        },
    )
    assert res["results"][0] == {"created": True, "entry_id": "twin"}, res
    assert res["results"][1]["error_code"] == "ENTRY_EXISTS", res
    assert "FIRST" in _file(env, "twin").read_text()


def test_cli_import_refuses_an_existing_id(env):
    path = env["tmp_path"] / "a.json"
    path.write_text(json.dumps([{"entry_type": "person", "title": "Dup", "body": "ORIGINAL"}]))
    assert _cli(env, ["import", str(path), "-k", KB]).exit_code == 0
    original = _file(env, "dup").read_bytes()

    path.write_text(json.dumps([{"entry_type": "person", "title": "Dup", "body": "REPLACED"}]))
    result = _cli(env, ["import", str(path), "-k", KB])
    assert result.exit_code == 1, result.output
    assert "[ENTRY_EXISTS]" in result.output, result.output
    assert _file(env, "dup").read_bytes() == original


# ---------------------------------------------------------------------------
# #366: bulk create validates each item
# ---------------------------------------------------------------------------


def test_bulk_create_refuses_a_schema_violation_per_item_with_the_create_message(env, mcp):
    bad = {"entry_type": "person", "title": "Bad Role", "body": "b", "role": "chore"}
    res = mcp._dispatch_tool(
        "kb_bulk_create",
        {
            "kb_name": KB,
            "entries": [
                {"entry_type": "person", "title": "Good One", "body": "b", "role": "author"},
                bad,
                {"entry_type": "person", "title": "Good Two", "body": "b"},
            ],
        },
    )
    assert [r["created"] for r in res["results"]] == [True, False, True], res
    assert res["results"][1]["error_code"] == "SCHEMA_VIOLATION"
    single = mcp._dispatch_tool("kb_create", {"kb_name": KB, **bad})
    assert res["results"][1]["error"] == single["error"], (res, single)
    assert _file(env, "bad-role") is None


def test_bulk_create_runs_plugin_validators(env, mcp, monkeypatch):
    """#366 names plugin validation too: a plugin validator's error refuses the item."""
    from pyrite.plugins import get_registry

    def no_blue(entry_type, fields, ctx):
        if fields.get("title", "").startswith("Blue"):
            return [{"field": "title", "rule": "no_blue", "expected": "not blue", "got": "blue"}]
        return []

    monkeypatch.setattr(get_registry(), "get_validators_for_kb", lambda kb_type: [no_blue])
    res = mcp._dispatch_tool(
        "kb_bulk_create",
        {
            "kb_name": KB,
            "entries": [
                {"entry_type": "person", "title": "Blue Person", "body": "b"},
                {"entry_type": "person", "title": "Red Person", "body": "b"},
            ],
        },
    )
    assert [r["created"] for r in res["results"]] == [False, True], res
    assert res["results"][0]["error_code"] == "SCHEMA_VIOLATION"
    assert "no_blue" in res["results"][0]["error"]


def test_cli_import_refuses_a_schema_violation(env):
    path = env["tmp_path"] / "v.json"
    path.write_text(
        json.dumps(
            [
                {"type": "person", "title": "Probe Bulk", "role": "bogus"},
                {"type": "person", "title": "Probe Fine", "role": "editor"},
            ]
        )
    )
    result = _cli(env, ["import", str(path), "-k", KB])
    assert result.exit_code == 1, result.output
    assert "[SCHEMA_VIOLATION]" in result.output
    assert _file(env, "probe-bulk") is None
    assert "role: editor" in _file(env, "probe-fine").read_text()


def test_cli_import_dry_run_reports_refusals_without_writing(env):
    path = env["tmp_path"] / "d.json"
    path.write_text(json.dumps([{"type": "person", "title": "Dry Bad", "role": "bogus"}]))
    result = _cli(env, ["import", str(path), "-k", KB, "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "Would refuse [SCHEMA_VIOLATION]" in result.output, result.output
    assert _file(env, "dry-bad") is None


# ---------------------------------------------------------------------------
# #378 acceptance 5: kb_update's field set comes from the type
# ---------------------------------------------------------------------------


def _create(mcp, **spec):
    res = mcp._dispatch_tool("kb_create", {"kb_name": KB, **spec})
    assert res.get("created"), res
    return res["entry_id"]


def test_kb_update_writes_a_model_field_the_old_allowlist_dropped(env, mcp):
    """A document's `url` is its model's field; the hand-kept allowlist omitted it."""
    eid = _create(mcp, entry_type="document", title="Doc", body="b", allow_undeclared=True)
    res = mcp._dispatch_tool(
        "kb_update", {"kb_name": KB, "entry_id": eid, "url": "https://example.org/d"}
    )
    assert res.get("updated"), res
    assert "url: https://example.org/d" in _file(env, eid).read_text()


def test_kb_update_writes_a_kb_yaml_declared_field_of_a_custom_type(env, mcp):
    """A kb.yaml-only type's declared field is updatable, and validated."""
    path = env["kb_path"] / "f1.md"
    path.write_text("---\nid: f1\ntitle: F1\ntype: finding\nseverity: low\n---\n\nb\n")
    mcp.index_mgr.index_all()

    res = mcp._dispatch_tool("kb_update", {"kb_name": KB, "entry_id": "f1", "severity": "high"})
    assert res.get("updated"), res
    assert "severity: high" in path.read_text()

    bad = mcp._dispatch_tool("kb_update", {"kb_name": KB, "entry_id": "f1", "severity": "odd"})
    assert bad.get("error_code") == "SCHEMA_VIOLATION", bad
    assert "severity: high" in path.read_text()


def test_kb_update_ignores_identity_and_bookkeeping_fields(env, mcp):
    """An agent echoing a read result back cannot rewrite id, path or created_at."""
    eid = _create(mcp, entry_type="person", title="Keep Me", body="b")
    got = mcp._dispatch_tool("kb_get", {"kb_name": KB, "entry_id": eid})
    before = _file(env, eid)
    created_line = [ln for ln in before.read_text().splitlines() if ln.startswith("created_at")]
    res = mcp._dispatch_tool(
        "kb_update",
        {
            **got,
            "kb_name": KB,
            "entry_id": eid,
            "id": "hijacked",
            "file_path": "/tmp/elsewhere.md",
            "created_at": "1999-01-01T00:00:00Z",
            "links": [{"target": "nowhere"}],
            "body": "edited",
        },
    )
    assert res.get("updated"), res
    after = _file(env, eid)
    assert after == before, "the entry moved"
    text = after.read_text()
    assert "id: keep-me" in text and "hijacked" not in text
    assert "1999" not in text and "nowhere" not in text
    assert [ln for ln in text.splitlines() if ln.startswith("created_at")] == created_line
    assert "edited" in text


def test_kb_update_field_set_names_no_extension_vocabulary(env, mcp):
    """`funder` was in the core allowlist; a person has no such field."""
    eid = _create(mcp, entry_type="person", title="No Funder", body="b")
    assert "funder" not in mcp.svc.updatable_fields(eid, KB)
    assert {"role", "title", "body", "lifecycle"} <= mcp.svc.updatable_fields(eid, KB)


# ---------------------------------------------------------------------------
# Warnings reach REST; `pyrite add` shares the pipeline
# ---------------------------------------------------------------------------


@pytest.fixture
def rest(env):
    from starlette.testclient import TestClient

    from pyrite.server.api import create_app, get_config, get_db, get_index_worker
    from pyrite.services.index_worker import IndexWorker

    config = env["config"]
    application = create_app(config=config)
    db = PyriteDB(env["db_path"])
    application.dependency_overrides[get_config] = lambda: config
    application.dependency_overrides[get_db] = lambda: db
    worker = IndexWorker(db, config)
    application.dependency_overrides[get_index_worker] = lambda: worker
    yield TestClient(application)
    worker.wait_for_idle(timeout=10)
    db.close()
    state_db = getattr(application.state, "pyrite_db", None)
    if state_db is not None and state_db is not db:
        state_db.close()


def test_rest_create_and_update_return_the_pipeline_warnings(env, rest):
    resp = rest.post(
        "/api/entries",
        json={"kb": KB, "entry_type": "note", "title": "Moody", "metadata": {"mood": "wild"}},
    )
    assert resp.status_code == 200, resp.text
    warnings = resp.json()["warnings"]
    assert any(w.get("field") == "mood" for w in warnings), warnings

    resp = rest.put("/api/entries/moody", json={"kb": KB, "metadata": {"mood": "wilder"}})
    assert resp.status_code == 200, resp.text
    assert any(w.get("got") == "wilder" for w in resp.json()["warnings"]), resp.json()


def test_rest_create_duplicate_is_a_conflict(env, rest):
    body = {"kb": KB, "entry_type": "person", "title": "Once", "body": "b"}
    assert rest.post("/api/entries", json=body).status_code == 200
    resp = rest.post("/api/entries", json=body)
    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"]["code"] == "ENTRY_EXISTS"


def test_rest_create_allow_undeclared_overrides_the_refusal(env, rest):
    _stop_enforcing(env)
    body = {"kb": KB, "entry_type": "widget", "title": "Allowed Widget", "body": "b"}
    refused = rest.post("/api/entries", json=body)
    assert refused.status_code == 400
    assert refused.json()["detail"]["declared_types"] == ["finding", "note", "person"]
    resp = rest.post("/api/entries", json={**body, "allow_undeclared": True})
    assert resp.status_code == 200, resp.text
    assert _file(env, "allowed-widget") is not None


def test_cli_add_refuses_an_undeclared_type_unless_allowed(env):
    _stop_enforcing(env)
    src = env["tmp_path"] / "w.md"
    src.write_text("---\ntitle: Added Widget\ntype: widget\n---\n\nbody\n")
    result = _cli(env, ["add", str(src), "-k", KB])
    assert result.exit_code == 1, result.output
    assert "[UNDECLARED_TYPE]" in result.output
    assert _file(env, "added-widget") is None

    result = _cli(env, ["add", str(src), "-k", KB, "--allow-undeclared"])
    assert result.exit_code == 0, result.output
    assert _file(env, "added-widget") is not None


def test_cli_add_refuses_a_truncated_body(env):
    src = env["tmp_path"] / "t.md"
    src.write_text("---\ntitle: Added Chunk\ntype: person\nbody_truncated: true\n---\n\npartial\n")
    result = _cli(env, ["add", str(src), "-k", KB])
    assert result.exit_code == 1, result.output
    assert "[VALIDATION_FAILED]" in result.output
    assert _file(env, "added-chunk") is None


def test_rest_import_allow_undeclared_overrides_the_refusal(env, rest):
    _stop_enforcing(env)
    spec = [{"entry_type": "widget", "title": "Imported Widget", "body": "b"}]
    payload = json.dumps(spec).encode()
    files = {"file": ("i.json", payload, "application/json")}
    refused = rest.post(f"/api/entries/import?kb={KB}&format=json", files=files).json()
    assert refused["error_details"][0]["error_code"] == "UNDECLARED_TYPE", refused
    files = {"file": ("i.json", payload, "application/json")}
    resp = rest.post(f"/api/entries/import?kb={KB}&format=json&allow_undeclared=true", files=files)
    assert resp.json()["imported"] == 1, resp.json()


def test_cli_import_dry_run_works_on_a_read_only_kb(env):
    """A dry run writes nothing, so a read-only KB can still be checked."""
    env["config"].get_kb(KB).read_only = True
    path = env["tmp_path"] / "ro.json"
    path.write_text(json.dumps([{"type": "person", "title": "Ro Check", "role": "bogus"}]))
    result = _cli(env, ["import", str(path), "-k", KB, "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "Would refuse [SCHEMA_VIOLATION]" in result.output, result.output


def test_bulk_create_missing_title_is_a_validation_refusal(env, mcp):
    """#358's per-item title failure now carries the pipeline's code too."""
    res = mcp._dispatch_tool(
        "kb_bulk_create",
        {"kb_name": KB, "entries": [{"entry_type": "person", "body": "untitled"}]},
    )
    assert res["results"][0] == {
        "created": False,
        "error": "title is required",
        "error_code": "VALIDATION_FAILED",
    }, res


def test_cli_add_validate_only_reports_a_refusal_without_writing(env):
    src = env["tmp_path"] / "v.md"
    src.write_text("---\ntitle: Checked Person\ntype: person\nrole: bogus\n---\n\nbody\n")
    result = _cli(env, ["add", str(src), "-k", KB, "--validate-only"])
    assert result.exit_code == 1, result.output
    assert "Validation failed" in result.output and "role" in result.output, result.output
    assert _file(env, "checked-person") is None
