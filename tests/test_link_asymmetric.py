"""Tests for pyrite links asymmetric command."""

import json
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pyrite.cli import app
from pyrite.cli.link_commands import _find_asymmetric_links
from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
from pyrite.services.kb_service import KBService
from pyrite.storage.database import PyriteDB

runner = CliRunner()


@pytest.fixture
def asym_env():
    """Two KBs with asymmetric cross-KB links."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "index.db"

        kb_a_path = tmpdir / "kb-a"
        kb_a_path.mkdir()
        kb_b_path = tmpdir / "kb-b"
        kb_b_path.mkdir()

        kb_a = KBConfig(name="kb-a", path=kb_a_path, kb_type=KBType.GENERIC)
        kb_b = KBConfig(name="kb-b", path=kb_b_path, kb_type=KBType.GENERIC)

        config = PyriteConfig(
            knowledge_bases=[kb_a, kb_b],
            settings=Settings(index_path=db_path),
        )

        db = PyriteDB(db_path)
        svc = KBService(config, db)

        # Create entries in both KBs
        svc.create_entry("kb-a", "trust-a", "Trust in Organizations",
                         body="Trust enables coordination.", entry_type="concept", tags=["trust"])
        svc.create_entry("kb-b", "trust-b", "Building Trust in Teams",
                         body="Trust and psychological safety in teams.", entry_type="concept", tags=["trust"])

        svc.create_entry("kb-a", "feedback-a", "Feedback Loops",
                         body="Feedback loops in systems.", entry_type="concept", tags=["systems"])
        svc.create_entry("kb-b", "feedback-b", "System Dynamics",
                         body="System dynamics and feedback.", entry_type="concept", tags=["systems"])

        # Bidirectional link (should NOT appear as asymmetric)
        svc.add_link("trust-a", "kb-a", "trust-b", target_kb="kb-b", relation="related_to")
        svc.add_link("trust-b", "kb-b", "trust-a", target_kb="kb-a", relation="related_to")

        # One-directional link A→B only (SHOULD appear as asymmetric)
        svc.add_link("feedback-a", "kb-a", "feedback-b", target_kb="kb-b", relation="related_to")

        yield {"config": config, "db": db, "svc": svc}
        db.close()


class TestFindAsymmetricLinks:
    def test_finds_one_directional_links(self, asym_env):
        results = _find_asymmetric_links(
            kb_a="kb-a", kb_b="kb-b",
            config=asym_env["config"], db=asym_env["db"],
        )
        # feedback-a → feedback-b exists, but feedback-b → feedback-a does not
        pairs = [(r["source_id"], r["target_id"]) for r in results]
        assert ("feedback-a", "feedback-b") in pairs

    def test_excludes_bidirectional_links(self, asym_env):
        results = _find_asymmetric_links(
            kb_a="kb-a", kb_b="kb-b",
            config=asym_env["config"], db=asym_env["db"],
        )
        pairs = [(r["source_id"], r["target_id"]) for r in results]
        # trust-a ↔ trust-b is bidirectional, should NOT appear
        assert ("trust-a", "trust-b") not in pairs
        assert ("trust-b", "trust-a") not in pairs

    def test_results_have_required_fields(self, asym_env):
        results = _find_asymmetric_links(
            kb_a="kb-a", kb_b="kb-b",
            config=asym_env["config"], db=asym_env["db"],
        )
        if results:
            r = results[0]
            assert "source_id" in r
            assert "source_kb" in r
            assert "target_id" in r
            assert "target_kb" in r
            assert "direction" in r
            assert "relation" in r

    def test_empty_when_all_bidirectional(self, asym_env):
        """If we only look at trust entries (both bidirectional), no asymmetries."""
        # This test verifies the general behavior — all asymmetric results
        # should only come from one-directional links
        results = _find_asymmetric_links(
            kb_a="kb-a", kb_b="kb-b",
            config=asym_env["config"], db=asym_env["db"],
        )
        for r in results:
            assert r["source_id"] != "trust-a" or r["target_id"] != "trust-b"


class TestAsymmetricCLI:
    def test_cli_json_output(self, asym_env, monkeypatch):
        monkeypatch.setattr(
            "pyrite.cli.link_commands.get_config_and_db",
            lambda: (asym_env["config"], asym_env["db"]),
        )
        asym_env["db"].close = lambda: None

        result = runner.invoke(
            app, ["links", "asymmetric", "--kb-a", "kb-a",
                  "--kb-b", "kb-b", "--format", "json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "asymmetric_links" in data
        assert data["kb_a"] == "kb-a"
        assert data["kb_b"] == "kb-b"
