"""investigation search (CLI) and investigation_search_all (MCP) honour the
core search-query cap: an over-long query is refused explicitly, a query at
the cap still searches. Both reach sanitizing through `cross_kb_search`."""

import json

import pytest
from pyrite_journalism_investigation.cli import investigation_app
from pyrite_journalism_investigation.cross_kb_search import cross_kb_search
from typer.testing import CliRunner

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.exceptions import QueryTooLongError
from pyrite.services.kb_service import KBService
from pyrite.services.search_service import MAX_SEARCH_QUERY_LENGTH
from pyrite.storage.database import PyriteDB

AT_CAP = "sanctions".ljust(MAX_SEARCH_QUERY_LENGTH)
OVER_CAP = "sanctions".ljust(MAX_SEARCH_QUERY_LENGTH + 1)


class _NoDB:
    def search(self, *args, **kwargs):  # pragma: no cover - reaching it is the failure
        raise AssertionError("an over-long query reached the database")


@pytest.fixture
def kb_env(tmp_path, monkeypatch):
    kb_path = tmp_path / "test-kb"
    kb_path.mkdir()
    kb = KBConfig(name="test", path=kb_path, kb_type="journalism-investigation")
    config = PyriteConfig(knowledge_bases=[kb], settings=Settings(index_path=tmp_path / "index.db"))
    db = PyriteDB(tmp_path / "index.db")
    KBService(config, db).create_entry(
        "test",
        "sanctions-2022",
        "Sanctions Announced",
        "investigation_event",
        body="EU sanctions",
        date="2022-02-24",
        importance=9,
    )
    monkeypatch.setattr("pyrite_journalism_investigation.cli.load_config", lambda: config)
    yield db
    db.close()


def test_cross_kb_search_refuses_before_the_database():
    with pytest.raises(QueryTooLongError):
        cross_kb_search(_NoDB(), OVER_CAP)


def test_cross_kb_search_at_cap_searches(kb_env):
    assert cross_kb_search(kb_env, AT_CAP)["total_count"] >= 1


def test_cli_over_cap_is_a_clear_error(kb_env):
    result = CliRunner().invoke(investigation_app, ["search", OVER_CAP, "--json"])
    assert result.exit_code == 1, result.output
    data = json.loads(result.output)
    assert data["error_code"] == "QUERY_TOO_LONG", data
    assert data["retryable"] is False


def test_cli_over_cap_rich_is_a_clear_error(kb_env):
    result = CliRunner().invoke(investigation_app, ["search", OVER_CAP])
    assert result.exit_code == 1, result.output
    assert "QUERY_TOO_LONG" in result.output


def test_cli_at_cap_searches(kb_env):
    result = CliRunner().invoke(investigation_app, ["search", AT_CAP, "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["total_count"] >= 1
