"""One projection rule, three read surfaces (#193, #179, #192).

REST `?fields=`, the MCP `fields` argument and the CLI `--fields` must return
the same key set for the same request: the named fields plus the identity pair,
and no invented keys. Nothing pinned that parity before; the four spellings had
already drifted (REST kept four fields, MCP two, the CLI none).
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from pyrite.cli import app
from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
from pyrite.models.core_types import EventEntry
from pyrite.server.api import create_app
from pyrite.services.read_shaping import IDENTITY_FIELDS, parse_fields_param, project_fields
from pyrite.storage.database import PyriteDB
from pyrite.storage.index import IndexManager
from pyrite.storage.repository import KBRepository

runner = CliRunner()
KB_NAME = "proj-parity"


class TestReadShapingUnit:
    """The helper's own contract, independent of any surface."""

    def test_identity_pair_always_kept(self):
        record = {"id": "a", "kb_name": "kb", "title": "T", "body": "b"}

        assert project_fields(record, ["title"]) == {"id": "a", "kb_name": "kb", "title": "T"}

    def test_unknown_fields_are_not_invented(self):
        record = {"id": "a", "kb_name": "kb"}

        assert project_fields(record, ["nope"]) == {"id": "a", "kb_name": "kb"}

    def test_falsy_fields_returns_the_record_unchanged(self):
        record = {"id": "a"}

        assert project_fields(record, None) is record
        assert project_fields(record, []) is record

    @pytest.mark.parametrize("value", [None, "", ",", " ", " , "])
    def test_degenerate_field_params_mean_no_projection(self, value):
        assert parse_fields_param(value) is None

    def test_duplicates_and_whitespace_are_cleaned(self):
        assert parse_fields_param(" title , title ,tags ") == ["title", "tags"]

    def test_required_is_a_parameter_not_a_constant(self):
        record = {"id": "a", "kb_name": "kb", "entry_type": "event"}

        assert project_fields(record, ["id"], required=("entry_type",)) == {
            "entry_type": "event",
            "id": "a",
        }


@pytest.fixture
def three_surface_env():
    """One KB with one entry, wired to REST, MCP and the CLI at once."""
    from pyrite.server.api import get_config, get_db, get_index_mgr
    from pyrite.server.mcp_server import PyriteMCPServer

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as raw:
        tmp = Path(raw)
        kb_path = tmp / "kb"
        kb_path.mkdir()
        db_path = tmp / "index.db"
        kb = KBConfig(name=KB_NAME, path=kb_path, kb_type=KBType.EVENTS)
        config = PyriteConfig(knowledge_bases=[kb], settings=Settings(index_path=db_path))

        entry = EventEntry.create(
            date="2025-01-10",
            title="Projection parity",
            body="A body about immigration policy.",
        )
        entry.tags = ["immigration"]
        KBRepository(kb).save(entry)

        db = PyriteDB(db_path)
        index_mgr = IndexManager(db, config)
        index_mgr.index_all()

        rest_app = create_app(config)
        rest_app.dependency_overrides[get_config] = lambda: config
        rest_app.dependency_overrides[get_db] = lambda: db
        rest_app.dependency_overrides[get_index_mgr] = lambda: index_mgr
        client = TestClient(rest_app)
        server = PyriteMCPServer(config, tier="read")
        try:
            yield {"client": client, "server": server, "config": config}
        finally:
            server.close()
            client.close()
            db.close()


def _rest_keys(env, fields):
    params = {"q": "immigration"}
    if fields is not None:
        params["fields"] = fields
    response = env["client"].get("/api/search", params=params)
    assert response.status_code == 200, response.text
    rows = response.json()["results"]
    assert rows, response.text
    return set(rows[0])


def _mcp_keys(env, fields):
    args = {"query": "immigration", "mode": "keyword"}
    if fields is not None:
        args["fields"] = parse_fields_param(fields)
    result = env["server"]._dispatch_tool("kb_search", args)
    rows = result.get("results") or []
    assert rows, result
    return set(rows[0])


def _cli_keys(env, fields):
    args = ["search", "immigration", "-k", KB_NAME, "--mode", "keyword", "--format", "json"]
    if fields is not None:
        args += ["--fields", fields]
    with (
        patch("pyrite.cli.context.load_config", return_value=env["config"]),
    ):
        result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    text = result.output.strip()
    payload = json.loads(text[text.index("{") :])
    rows = payload["results"]
    assert rows, payload
    return set(rows[0])


@pytest.mark.parametrize("fields", ["title", "nope", "tags,importance"])
def test_rest_mcp_and_cli_return_the_same_keys(three_surface_env, fields):
    rest = _rest_keys(three_surface_env, fields)
    mcp = _mcp_keys(three_surface_env, fields)
    cli = _cli_keys(three_surface_env, fields)

    assert rest == mcp == cli, {"rest": rest, "mcp": mcp, "cli": cli}
    assert set(IDENTITY_FIELDS) <= rest
