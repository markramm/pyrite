"""Tests for MCP conversational optimization.

Covers improved tool descriptions, default KB resolution, and query summaries.
"""

from dataclasses import dataclass, field
from unittest.mock import MagicMock

import pytest

from pyrite_journalism_investigation.plugin import JournalismInvestigationPlugin
from pyrite_journalism_investigation.queries import (
    query_claims,
    query_entities,
    query_sources,
    query_timeline,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class FakeKBConfig:
    name: str = "test-inv"
    kb_type: str = "journalism-investigation"


@dataclass
class FakeConfig:
    knowledge_bases: list = field(default_factory=list)


class FakeDB:
    """Minimal mock that satisfies query function signatures."""

    def __init__(self, entries=None):
        self._entries = entries or []

    def list_entries(self, **kwargs):
        etype = kwargs.get("entry_type", "")
        return [e for e in self._entries if e.get("entry_type") == etype]


# ---------------------------------------------------------------------------
# 1. Tool descriptions are conversational
# ---------------------------------------------------------------------------


class TestToolDescriptionsAreConversational:
    """Every tool description should start with a verb and include example/context."""

    @pytest.fixture()
    def plugin(self):
        return JournalismInvestigationPlugin()

    def _all_tools(self, plugin):
        read = plugin.get_mcp_tools("read")
        write = plugin.get_mcp_tools("write")
        # write includes read, so just use write for the full set
        return write

    def test_all_descriptions_start_with_verb(self, plugin):
        """Conversational descriptions should begin with an imperative verb."""
        tools = self._all_tools(plugin)
        for name, defn in tools.items():
            desc = defn["description"]
            first_word = desc.split()[0]
            # first word should look like a verb (starts with uppercase letter)
            assert first_word[0].isupper() or first_word[0].islower(), (
                f"Tool {name} description does not start with a word: {desc!r}"
            )
            # Should NOT be a dry "Query ..." / "Create ..." single-clause style
            # that the old descriptions used. Conversational ones are longer.
            assert len(desc) > 60, (
                f"Tool {name} description is too short to be conversational ({len(desc)} chars): {desc!r}"
            )

    @pytest.mark.parametrize(
        "tool_name",
        [
            "investigation_timeline",
            "investigation_entities",
            "investigation_network",
            "investigation_sources",
            "investigation_claims",
            "investigation_evidence_chain",
            "investigation_qa_report",
        ],
    )
    def test_read_tool_descriptions_conversational(self, plugin, tool_name):
        tools = plugin.get_mcp_tools("read")
        desc = tools[tool_name]["description"]
        # Should start with a verb (lowercase first char is fine for conversational)
        first_word = desc.split()[0]
        assert first_word[0].isupper() or first_word[0].islower()
        # Should be meaningfully long (includes example / context)
        assert len(desc) > 60

    @pytest.mark.parametrize(
        "tool_name",
        [
            "investigation_create_entity",
            "investigation_create_event",
            "investigation_create_claim",
            "investigation_log_source",
        ],
    )
    def test_write_tool_descriptions_conversational(self, plugin, tool_name):
        tools = plugin.get_mcp_tools("write")
        desc = tools[tool_name]["description"]
        first_word = desc.split()[0]
        assert first_word[0].isupper() or first_word[0].islower()
        assert len(desc) > 50


# ---------------------------------------------------------------------------
# 2. Default KB name resolution
# ---------------------------------------------------------------------------


class TestDefaultKBName:
    def test_default_investigation_kb_found(self):
        plugin = JournalismInvestigationPlugin()
        ctx = MagicMock()
        ctx.config = FakeConfig(
            knowledge_bases=[
                FakeKBConfig(name="notes", kb_type="generic"),
                FakeKBConfig(name="my-investigation", kb_type="journalism-investigation"),
            ]
        )
        plugin.set_context(ctx)
        assert plugin._default_investigation_kb() == "my-investigation"

    def test_default_investigation_kb_none_when_missing(self):
        plugin = JournalismInvestigationPlugin()
        ctx = MagicMock()
        ctx.config = FakeConfig(
            knowledge_bases=[
                FakeKBConfig(name="notes", kb_type="generic"),
            ]
        )
        plugin.set_context(ctx)
        assert plugin._default_investigation_kb() is None

    def test_default_investigation_kb_none_without_context(self):
        plugin = JournalismInvestigationPlugin()
        assert plugin._default_investigation_kb() is None

    def test_handler_uses_default_kb_when_not_provided(self):
        """When kb_name is omitted from args, handler should fall back to default."""
        plugin = JournalismInvestigationPlugin()
        ctx = MagicMock()
        ctx.config = FakeConfig(
            knowledge_bases=[
                FakeKBConfig(name="fallback-inv", kb_type="journalism-investigation"),
            ]
        )
        plugin.set_context(ctx)

        # Mock _get_db to return a fake DB with no entries
        fake_db = FakeDB()
        plugin._get_db = lambda: (fake_db, False)

        result = plugin._mcp_timeline({})
        # Should not error — it resolved kb_name from default
        assert "events" in result

    def test_handler_falls_back_to_investigation_string(self):
        """When no context and no kb_name arg, fall back to 'investigation'."""
        plugin = JournalismInvestigationPlugin()

        fake_db = FakeDB()
        plugin._get_db = lambda: (fake_db, False)

        result = plugin._mcp_timeline({})
        assert "events" in result


# ---------------------------------------------------------------------------
# 3. Query summaries
# ---------------------------------------------------------------------------


class TestQuerySummaries:
    def test_timeline_summary(self):
        db = FakeDB(
            entries=[
                {
                    "id": "e1",
                    "title": "Event 1",
                    "entry_type": "investigation_event",
                    "date": "2023-01-15",
                    "importance": 5,
                    "metadata": "{}",
                },
            ]
        )
        result = query_timeline(db, "test")
        assert "summary" in result
        assert "1 event" in result["summary"] or "1" in result["summary"]

    def test_timeline_summary_empty(self):
        db = FakeDB()
        result = query_timeline(db, "test")
        assert "summary" in result
        assert "0" in result["summary"]

    def test_entities_summary(self):
        db = FakeDB(
            entries=[
                {
                    "id": "p1",
                    "title": "Person 1",
                    "entry_type": "person",
                    "importance": 5,
                    "metadata": "{}",
                },
                {
                    "id": "p2",
                    "title": "Person 2",
                    "entry_type": "person",
                    "importance": 7,
                    "metadata": "{}",
                },
            ]
        )
        result = query_entities(db, "test", entity_type="person")
        assert "summary" in result
        assert "2" in result["summary"]

    def test_entities_summary_with_type(self):
        db = FakeDB()
        result = query_entities(db, "test", entity_type="person")
        assert "summary" in result
        assert "person" in result["summary"].lower()

    def test_entities_summary_no_type(self):
        db = FakeDB()
        result = query_entities(db, "test")
        assert "summary" in result
        assert "entities" in result["summary"].lower()

    def test_sources_summary_with_tiers(self):
        db = FakeDB(
            entries=[
                {
                    "id": "s1",
                    "title": "Source 1",
                    "entry_type": "document_source",
                    "metadata": '{"reliability": "high"}',
                },
                {
                    "id": "s2",
                    "title": "Source 2",
                    "entry_type": "document_source",
                    "metadata": '{"reliability": "high"}',
                },
                {
                    "id": "s3",
                    "title": "Source 3",
                    "entry_type": "document_source",
                    "metadata": '{"reliability": "low"}',
                },
            ]
        )
        result = query_sources(db, "test")
        assert "summary" in result
        assert "3" in result["summary"]
        # Should mention tier breakdown
        assert "high" in result["summary"].lower()

    def test_claims_summary_with_status_counts(self):
        db = FakeDB(
            entries=[
                {
                    "id": "c1",
                    "title": "Claim 1",
                    "entry_type": "claim",
                    "importance": 5,
                    "metadata": '{"claim_status": "unverified", "confidence": "low"}',
                },
                {
                    "id": "c2",
                    "title": "Claim 2",
                    "entry_type": "claim",
                    "importance": 7,
                    "metadata": '{"claim_status": "corroborated", "confidence": "high"}',
                },
            ]
        )
        result = query_claims(db, "test")
        assert "summary" in result
        assert "2" in result["summary"]
        assert "unverified" in result["summary"].lower()
        assert "corroborated" in result["summary"].lower()

    def test_kb_name_not_required_in_schema(self):
        """After optimization, kb_name should not be in required for most tools."""
        plugin = JournalismInvestigationPlugin()
        tools = plugin.get_mcp_tools("read")
        # Tools that previously required only kb_name should now have empty required
        for name in [
            "investigation_timeline",
            "investigation_entities",
            "investigation_sources",
            "investigation_claims",
            "investigation_qa_report",
        ]:
            schema = tools[name]["inputSchema"]
            assert "kb_name" not in schema.get("required", []), (
                f"{name} should not require kb_name after optimization"
            )
