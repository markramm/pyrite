"""Tests for QAAnalyticsService.coverage_stats — Tier A r2300.

`pyrite qa validate` catches per-entry STRUCTURAL issues (orphans,
broken links, missing fields). It does NOT answer aggregate questions
like "what percent of this KB is sourced?" or "what's the status
distribution?" — those are CURATION COVERAGE stats, useful for
planning a research session, not for fixing one entry.

This contract pins the smallest useful slice of r2300: aggregate
coverage numbers per KB and per type. The remaining ticket asks
(MCP tool, inline-reference source detection) are filed as follow-ups.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
from pyrite.models import NoteEntry, PersonEntry
from pyrite.services.qa_analytics_service import QAAnalyticsService
from pyrite.storage.database import PyriteDB
from pyrite.storage.index import IndexManager
from pyrite.storage.repository import KBRepository


@pytest.fixture
def analytics_setup():
    """Seed a KB with a known mix of types, statuses, bodies, links,
    and sources so the stats are calculable by hand."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        db_path = tmpdir / "index.db"
        kb_path = tmpdir / "kb"
        kb_path.mkdir()

        kb = KBConfig(name="test-kb", path=kb_path, kb_type=KBType.GENERIC)
        config = PyriteConfig(
            knowledge_bases=[kb],
            settings=Settings(index_path=db_path),
        )
        repo = KBRepository(kb)

        # 4 notes: 2 with body, 2 without; 2 with wikilinks, 2 without.
        repo.save(
            NoteEntry(
                id="note-a",
                title="Note A",
                body="A long enough body about [[note-b]] for coverage.",
            )
        )
        repo.save(NoteEntry(id="note-b", title="Note B", body=""))
        repo.save(
            NoteEntry(
                id="note-c",
                title="Note C",
                body="Another body referencing [[note-a]] and [[note-d]].",
            )
        )
        repo.save(NoteEntry(id="note-d", title="Note D", body=""))

        # 2 persons with bodies, no wikilinks.
        repo.save(
            PersonEntry.create(
                name="Person One",
                role="Researcher",
                importance=6,
            )
        )
        repo.save(
            PersonEntry.create(
                name="Person Two",
                role="Source",
                importance=8,
            )
        )

        db = PyriteDB(db_path)
        IndexManager(db, config).index_all()

        analytics = QAAnalyticsService(config, db)

        yield {
            "analytics": analytics,
            "db": db,
            "config": config,
        }

        db.close()


class TestCoverageStatsSmoke:
    """The contract: coverage_stats returns a dict with the right shape."""

    def test_returns_dict_with_required_keys(self, analytics_setup):
        stats = analytics_setup["analytics"].coverage_stats("test-kb")
        assert isinstance(stats, dict)
        # Required keys per the ticket
        for key in (
            "kb_name",
            "total_entries",
            "by_type",
            "by_status",
            "body_coverage",
            "link_coverage",
            "source_coverage",
        ):
            assert key in stats, f"missing key {key}: {list(stats)}"
        assert stats["kb_name"] == "test-kb"

    def test_total_entries_is_correct(self, analytics_setup):
        stats = analytics_setup["analytics"].coverage_stats("test-kb")
        # 4 notes + 2 persons
        assert stats["total_entries"] == 6


class TestByTypeBreakdown:
    """Per-type distribution — answers 'how many of each kind do we have'."""

    def test_by_type_counts_match(self, analytics_setup):
        stats = analytics_setup["analytics"].coverage_stats("test-kb")
        assert stats["by_type"].get("note") == 4
        assert stats["by_type"].get("person") == 2


class TestBodyCoverage:
    """What fraction of entries have non-empty body content."""

    def test_body_coverage_overall(self, analytics_setup):
        stats = analytics_setup["analytics"].coverage_stats("test-kb")
        bc = stats["body_coverage"]
        # Only note-a and note-c have non-empty bodies in the fixture
        # (PersonEntry.create defaults body=""). So 2 with, 4 without.
        assert bc["with_body"] == 2
        assert bc["without_body"] == 4
        assert bc["total"] == 6
        # 2/6 = 0.333...
        assert 0.3 <= bc["fraction"] <= 0.4


class TestLinkCoverage:
    """What fraction of entries have outbound wikilinks, and average density."""

    def test_link_coverage_overall(self, analytics_setup):
        stats = analytics_setup["analytics"].coverage_stats("test-kb")
        lc = stats["link_coverage"]
        # 2 notes have outlinks (note-a -> note-b; note-c -> note-a, note-d)
        # 4 entries (note-b, note-d, person 1, person 2) have none.
        assert lc["with_outlinks"] == 2
        # Sum of outbound links: note-a has 1, note-c has 2 -> 3 total
        assert lc["total_outlinks"] == 3
        # Average per entry: 3 / 6 = 0.5
        assert 0.4 <= lc["avg_per_entry"] <= 0.6


class TestSourceCoverage:
    """What fraction of entries have structured sources attached.

    Note: inline-reference source detection (configurable patterns) is
    a separate ticket / follow-up; this is structured sources only.
    """

    def test_source_coverage_when_none(self, analytics_setup):
        # No source rows were inserted, so 0% sourced
        stats = analytics_setup["analytics"].coverage_stats("test-kb")
        sc = stats["source_coverage"]
        assert sc["with_sources"] == 0
        assert sc["total"] == 6
        assert sc["fraction"] == 0.0


class TestPerTypeFilter:
    """The `entry_type=` filter restricts the report to one type."""

    def test_filter_to_note_only(self, analytics_setup):
        stats = analytics_setup["analytics"].coverage_stats(
            "test-kb", entry_type="note"
        )
        assert stats["total_entries"] == 4
        assert stats["by_type"] == {"note": 4}
        # 2 of the 4 notes have bodies (note-a, note-c); 2 are empty.
        bc = stats["body_coverage"]
        assert bc["with_body"] == 2
        assert bc["without_body"] == 2
        assert bc["total"] == 4

    def test_filter_to_unknown_type_returns_empty(self, analytics_setup):
        stats = analytics_setup["analytics"].coverage_stats(
            "test-kb", entry_type="nonexistent"
        )
        assert stats["total_entries"] == 0


class TestUnknownKB:
    """Calling against a KB that doesn't exist surfaces a clear empty result.

    The CLI surface will turn this into a NOT_FOUND error; at the service
    layer we just return total_entries=0 so callers can distinguish
    'empty' from 'not registered'.
    """

    def test_unknown_kb_returns_zero(self, analytics_setup):
        stats = analytics_setup["analytics"].coverage_stats("no-such-kb")
        assert stats["total_entries"] == 0
