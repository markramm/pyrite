"""A kb.yaml-only type keeps every field it was given (#386).

`pyrite.models.factory.build_entry`'s `if resolved_cls is GenericEntry:`
branch constructed the entry with only `tags`, `summary` and `metadata`;
every other keyword -- anything passed as a bare `key=value`, not nested
under an explicit `metadata:` -- was silently dropped. `build_entry` is the
single choke point `KBService.create_entry` and `bulk_create_entries` call
through, so every write surface lost the data: CLI `create -f`, MCP
`kb_create`, and bulk/import (which calls `bulk_create_entries` directly, the
same path `pyrite import` uses).

Because the field never reached `to_frontmatter()`, the schema validator
that `_validate_write` runs on it never saw the value either -- so a
`validation.enforce: true` KB failed to refuse a bad enum value on a
kb.yaml-only type (the write silently *succeeded* with the bad value
dropped, rather than being refused).

`entry_from_frontmatter` (used by `pyrite add` and the indexer) already
routes unknown keys into `metadata` via `GenericEntry.from_frontmatter`, so
the same data survived that path and not this one -- this file is the direct
`build_entry` regression the issue names, plus one regression test per
write surface that reaches it.
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner
from unittest.mock import patch

from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
from pyrite.exceptions import ValidationError
from pyrite.models.factory import build_entry
from pyrite.models.generic import GenericEntry
from pyrite.server.mcp_server import PyriteMCPServer
from pyrite.storage.database import PyriteDB

# A kb.yaml-only type: no Python model class, so `get_entry_class` falls
# back to `GenericEntry`. `severity` is a `select` field so `validation:
# enforce: true` can refuse an off-enum value once the field reaches the
# validator at all.
KB_YAML = """\
name: t
kb_type: generic
validation:
  enforce: true
types:
  finding:
    description: A finding
    fields:
      severity:
        type: select
        options: [low, medium, high]
"""


def _make_kb(tmp_path: Path) -> tuple[PyriteConfig, KBConfig]:
    kb_path = tmp_path / "kb"
    kb_path.mkdir()
    (kb_path / "kb.yaml").write_text(KB_YAML, encoding="utf-8")
    db_path = tmp_path / "index.db"
    PyriteDB(db_path).close()
    kb_config = KBConfig(name="t", path=kb_path, kb_type=KBType.GENERIC)
    config = PyriteConfig(
        knowledge_bases=[kb_config], settings=Settings(index_path=db_path, auto_embed=False)
    )
    return config, kb_config


class TestBuildEntryDirect:
    """The factory function itself: the exact reproduction from the issue."""

    def test_generic_type_keeps_a_bare_kwarg(self):
        entry = build_entry("finding", entry_id="x", title="X", severity="high")
        assert isinstance(entry, GenericEntry)
        fm = entry.to_frontmatter()
        assert fm.get("severity") == "high", (
            f"expected 'severity' to survive build_entry for a GenericEntry; got {fm}"
        )

    def test_generic_type_still_keeps_tags_summary_metadata(self):
        """The three keys the old branch handled must keep working."""
        entry = build_entry(
            "finding",
            entry_id="x",
            title="X",
            tags=["a"],
            summary="s",
            metadata={"m": 1},
        )
        assert entry.tags == ["a"]
        assert entry.summary == "s"
        assert entry.metadata.get("m") == 1


class TestCreateEntrySurface:
    """`KBService.create_entry` -- what CLI `create -f` and MCP `kb_create` call."""

    def test_create_entry_keeps_the_field(self, tmp_path):
        config, kb_config = _make_kb(tmp_path)
        db = PyriteDB(config.settings.index_path)
        from pyrite.services.kb_service import KBService

        svc = KBService(config, db)
        try:
            entry = svc.create_entry("t", "x", "X", "finding", "body", severity="high")
        finally:
            db.close()
        assert entry.to_frontmatter().get("severity") == "high"

    def test_create_entry_refuses_an_off_enum_value(self, tmp_path):
        """Acceptance 2: enforce=true refuses a bad select value on a
        kb.yaml-only type -- only possible once the field reaches the
        validator, i.e. once acceptance 1 holds."""
        config, kb_config = _make_kb(tmp_path)
        db = PyriteDB(config.settings.index_path)
        from pyrite.services.kb_service import KBService

        svc = KBService(config, db)
        try:
            with pytest.raises(ValidationError, match="severity"):
                svc.create_entry("t", "x", "X", "finding", "body", severity="critical")
        finally:
            db.close()
        assert not (kb_config.path / "x.md").exists(), "a refused create must not write the file"


class TestCLICreateSurface:
    """`pyrite create -f severity=high`."""

    runner = CliRunner()

    def test_cli_create_dash_f_keeps_the_field(self, tmp_path):
        from pyrite.cli import app

        config, kb_config = _make_kb(tmp_path)
        with patch("pyrite.cli.context.load_config", return_value=config):
            result = self.runner.invoke(
                app,
                [
                    "create",
                    "-k",
                    "t",
                    "-t",
                    "finding",
                    "--title",
                    "X",
                    "-b",
                    "body",
                    "-f",
                    "severity=high",
                ],
            )
        assert result.exit_code == 0, result.output
        written = (kb_config.path / "x.md").read_text(encoding="utf-8")
        assert "severity" in written and "high" in written, written

    def test_cli_create_dash_f_refuses_off_enum(self, tmp_path):
        from pyrite.cli import app

        config, kb_config = _make_kb(tmp_path)
        with patch("pyrite.cli.context.load_config", return_value=config):
            result = self.runner.invoke(
                app,
                [
                    "create",
                    "-k",
                    "t",
                    "-t",
                    "finding",
                    "--title",
                    "X",
                    "-b",
                    "body",
                    "-f",
                    "severity=critical",
                ],
            )
        assert result.exit_code != 0, result.output
        assert not (kb_config.path / "x.md").exists()


class TestMCPKBCreateSurface:
    """MCP `kb_create` with `severity` as a top-level arg."""

    def test_kb_create_keeps_the_field(self, tmp_path):
        config, kb_config = _make_kb(tmp_path)
        server = PyriteMCPServer(config, tier="write")
        try:
            result = server._dispatch_tool(
                "kb_create",
                {
                    "kb_name": "t",
                    "entry_type": "finding",
                    "title": "X",
                    "body": "body",
                    "severity": "high",
                },
            )
            assert result.get("created") is True, result
            # The DB-indexed `kb_get` view keeps unknown fields nested under
            # `metadata`, same as `test_kb_create_with_metadata_generic_type`
            # asserts for an explicit `metadata=` kwarg -- the file on disk is
            # the unambiguous check that the field itself, not just the
            # write's success flag, survived.
            written = Path(result["file_path"]).read_text(encoding="utf-8")
            assert "severity" in written and "high" in written, written
        finally:
            server.close()

    def test_kb_create_refuses_off_enum(self, tmp_path):
        config, kb_config = _make_kb(tmp_path)
        server = PyriteMCPServer(config, tier="write")
        try:
            result = server._dispatch_tool(
                "kb_create",
                {
                    "kb_name": "t",
                    "entry_type": "finding",
                    "title": "X",
                    "body": "body",
                    "severity": "critical",
                },
            )
            assert result.get("created") is not True, result
            assert not (kb_config.path / "x.md").exists()
        finally:
            server.close()


class TestBulkAndImportSurface:
    """`bulk_create_entries` -- shared by MCP `kb_bulk_create` and `pyrite import`."""

    def test_bulk_create_keeps_the_field(self, tmp_path):
        config, kb_config = _make_kb(tmp_path)
        db = PyriteDB(config.settings.index_path)
        from pyrite.services.kb_service import KBService

        svc = KBService(config, db)
        try:
            results = svc.bulk_create_entries(
                "t",
                [{"entry_type": "finding", "title": "X", "body": "body", "severity": "high"}],
            )
        finally:
            db.close()
        assert results[0]["created"] is True, results
        written = (kb_config.path / "x.md").read_text(encoding="utf-8")
        assert "severity" in written and "high" in written, written

    # No off-enum refusal test for `bulk_create_entries` here: unlike
    # `create_entry`, it never calls `_validate_write` at all (confirmed by
    # reading `KBService.bulk_create_entries` -- there is no `_validate_write`
    # or `entry.validate()` call in its loop, and `test_write_path_enforces_
    # schema.py`'s enforce coverage only exercises `create_entry`/
    # `update_entry`). That is a real gap, but its root cause is in
    # `kb_service.py`'s bulk loop, not in `build_entry` -- this ticket's
    # touch is `factory.py` only. Filed separately rather than folded in here
    # (see the report's Unsure/Left).
