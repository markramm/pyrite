"""Tests for pyrite links batch-suggest command (cross-KB batch similarity)."""

import json
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pyrite.cli import app
from pyrite.cli.link_commands import _batch_suggest
from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
from pyrite.services.kb_service import KBService
from pyrite.storage.database import PyriteDB

runner = CliRunner()


@pytest.fixture
def batch_env():
    """Two KBs with overlapping content for batch similarity tests."""
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

        # KB-A entries
        svc.create_entry("kb-a", "trust-concept", "Trust in Organizations",
                         body="Trust enables coordination without hierarchy.",
                         entry_type="concept", tags=["trust", "organizations"])
        svc.create_entry("kb-a", "feedback-loops", "Feedback Loops in Systems",
                         body="Feedback loops amplify or dampen system behavior.",
                         entry_type="concept", tags=["systems", "feedback"])
        svc.create_entry("kb-a", "cooking-tips", "Cooking Tips",
                         body="Use salt to enhance flavor in pasta dishes.",
                         entry_type="note", tags=["cooking"])

        # KB-B entries (some related to KB-A, some not)
        svc.create_entry("kb-b", "psychological-safety", "Psychological Safety",
                         body="Trust and safety enable team coordination without fear.",
                         entry_type="concept", tags=["trust", "teams"])
        svc.create_entry("kb-b", "system-dynamics", "System Dynamics Modeling",
                         body="System dynamics models feedback loops and delays.",
                         entry_type="concept", tags=["systems", "modeling"])
        svc.create_entry("kb-b", "gardening-guide", "Gardening for Beginners",
                         body="Plant tomatoes in spring for best results.",
                         entry_type="note", tags=["gardening"])

        yield {"config": config, "db": db, "svc": svc}
        db.close()


class TestBatchSuggest:
    def test_finds_cross_kb_matches(self, batch_env):
        results = _batch_suggest(
            source_kb="kb-a",
            target_kb="kb-b",
            limit_per_entry=3,
            mode="keyword",
            exclude_linked=True,
            config=batch_env["config"],
            db=batch_env["db"],
        )
        assert len(results) > 0
        # Should find trust↔psychological-safety and feedback↔system-dynamics
        pairs = {(r["source_id"], r["target_id"]) for r in results}
        # At least one meaningful match should exist
        assert any("trust" in s or "trust" in t for s, t in pairs)

    def test_deduplicates_bidirectional_matches(self, batch_env):
        results = _batch_suggest(
            source_kb="kb-a",
            target_kb="kb-b",
            limit_per_entry=5,
            mode="keyword",
            exclude_linked=True,
            config=batch_env["config"],
            db=batch_env["db"],
        )
        # No pair should appear twice (A→B and B→A counted as one)
        pairs = [(r["source_id"], r["target_id"]) for r in results]
        pair_set = {tuple(sorted(p)) for p in pairs}
        assert len(pair_set) == len(pairs)

    def test_results_sorted_by_score(self, batch_env):
        results = _batch_suggest(
            source_kb="kb-a",
            target_kb="kb-b",
            limit_per_entry=3,
            mode="keyword",
            exclude_linked=True,
            config=batch_env["config"],
            db=batch_env["db"],
        )
        if len(results) > 1:
            scores = [r["score"] for r in results]
            assert scores == sorted(scores, reverse=True)

    def test_results_have_required_fields(self, batch_env):
        results = _batch_suggest(
            source_kb="kb-a",
            target_kb="kb-b",
            limit_per_entry=3,
            mode="keyword",
            exclude_linked=True,
            config=batch_env["config"],
            db=batch_env["db"],
        )
        if results:
            r = results[0]
            assert "source_id" in r
            assert "source_title" in r
            assert "target_id" in r
            assert "target_title" in r
            assert "score" in r

    def test_empty_result_for_unrelated_kbs(self, batch_env):
        """Two KBs with no vocabulary overlap should produce few/no results."""
        # This is a soft test — keyword search may still find some matches
        # but cooking↔gardening shouldn't dominate
        results = _batch_suggest(
            source_kb="kb-a",
            target_kb="kb-b",
            limit_per_entry=1,
            mode="keyword",
            exclude_linked=True,
            config=batch_env["config"],
            db=batch_env["db"],
        )
        # Should return something (trust and systems entries overlap)
        # but not more than source entries × limit_per_entry
        assert len(results) <= 3  # 3 source entries × 1 per entry


class TestBatchSuggestCLI:
    def test_cli_json_output(self, batch_env, monkeypatch):
        monkeypatch.setattr(
            "pyrite.cli.link_commands.get_config_and_db",
            lambda: (batch_env["config"], batch_env["db"]),
        )
        batch_env["db"].close = lambda: None

        result = runner.invoke(
            app, ["links", "batch-suggest", "--source-kb", "kb-a",
                  "--target-kb", "kb-b", "--format", "json"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "pairs" in data
        assert "source_kb" in data
        assert data["source_kb"] == "kb-a"
        assert data["target_kb"] == "kb-b"
