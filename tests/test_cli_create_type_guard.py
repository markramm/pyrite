"""`pyrite create -t <type>` must refuse a type the KB does not declare (#197).

Regression: core types were exempt from the write-side guard
(`entry_type not in CORE_TYPES`), so `-t note` against a software KB skipped the
refusal and plugin type resolution then promoted it to the most-derived
`NoteEntry` subclass -- an ADR, written under `kb/adrs/` with `adr_number: 0`.
"""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from pyrite.cli import app
from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
from pyrite.storage.database import PyriteDB

runner = CliRunner()

KB_YAML = """name: sw-kb
kb_type: generic
types:
  component:
    description: A software component
  adr:
    description: An architecture decision record
  backlog_item:
    description: A backlog work item
  standard:
    description: A standard
"""


def _make_env(tmp_path: Path) -> tuple[PyriteConfig, Path]:
    kb_path = tmp_path / "kb"
    kb_path.mkdir()
    (kb_path / "kb.yaml").write_text(KB_YAML, encoding="utf-8")
    db_path = tmp_path / "index.db"
    PyriteDB(db_path).close()
    kb = KBConfig(name="sw-kb", path=kb_path, kb_type=KBType.GENERIC)
    config = PyriteConfig(knowledge_bases=[kb], settings=Settings(index_path=db_path))
    return config, kb_path


def _invoke(config: PyriteConfig, args: list[str]):
    with patch("pyrite.cli.context.load_config", return_value=config):
        return runner.invoke(app, args)


def test_create_refuses_a_core_type_the_kb_does_not_declare(tmp_path):
    config, kb_path = _make_env(tmp_path)

    result = _invoke(
        config, ["create", "-k", "sw-kb", "-t", "note", "--title", "Probe note", "-b", "body"]
    )

    assert result.exit_code != 0, result.output
    # The refusal names the requested type and the KB's declared vocabulary.
    assert "note" in result.output, result.output
    assert "component" in result.output, result.output
    assert "backlog_item" in result.output, result.output
    # Nothing was written -- in particular no ADR under kb/adrs/.
    assert list(kb_path.rglob("*.md")) == []


def test_create_still_creates_a_declared_type(tmp_path):
    config, kb_path = _make_env(tmp_path)

    result = _invoke(
        config,
        ["create", "-k", "sw-kb", "-t", "component", "--title", "Probe component", "-b", "body"],
    )

    assert result.exit_code == 0, result.output
    written = list(kb_path.rglob("*.md"))
    assert len(written) == 1, written
    assert written[0].parent.name == "components"
    assert "type: component" in written[0].read_text(encoding="utf-8")


def test_create_allows_an_undeclared_type_with_the_override(tmp_path):
    config, kb_path = _make_env(tmp_path)

    result = _invoke(
        config,
        [
            "create",
            "-k",
            "sw-kb",
            "-t",
            "note",
            "--title",
            "Override note",
            "-b",
            "body",
            "--allow-undeclared",
        ],
    )

    assert result.exit_code == 0, result.output
    # The override still writes the entry (and `pyrite index health` flags it).
    assert len(list(kb_path.rglob("*.md"))) == 1
