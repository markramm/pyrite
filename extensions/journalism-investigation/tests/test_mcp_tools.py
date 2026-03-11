"""Tests for journalism-investigation MCP tools."""

from pyrite_journalism_investigation.plugin import JournalismInvestigationPlugin


class TestMCPToolRegistration:
    def test_read_tier_tools_registered(self):
        plugin = JournalismInvestigationPlugin()
        tools = plugin.get_mcp_tools("read")
        assert "investigation_timeline" in tools
        assert "investigation_entities" in tools
        assert "investigation_network" in tools
        assert "investigation_sources" in tools

    def test_write_tier_inherits_read(self):
        plugin = JournalismInvestigationPlugin()
        tools = plugin.get_mcp_tools("write")
        assert "investigation_timeline" in tools

    def test_no_tools_for_invalid_tier(self):
        plugin = JournalismInvestigationPlugin()
        tools = plugin.get_mcp_tools("invalid")
        assert tools == {}

    def test_timeline_tool_schema(self):
        plugin = JournalismInvestigationPlugin()
        tools = plugin.get_mcp_tools("read")
        schema = tools["investigation_timeline"]["inputSchema"]
        props = schema["properties"]
        assert "from_date" in props
        assert "to_date" in props
        assert "actor" in props
        assert "event_type" in props
        assert "min_importance" in props
        assert "limit" in props
        assert "kb_name" in props

    def test_entities_tool_schema(self):
        plugin = JournalismInvestigationPlugin()
        tools = plugin.get_mcp_tools("read")
        schema = tools["investigation_entities"]["inputSchema"]
        props = schema["properties"]
        assert "entity_type" in props
        assert "min_importance" in props
        assert "jurisdiction" in props
        assert "kb_name" in props

    def test_network_tool_schema(self):
        plugin = JournalismInvestigationPlugin()
        tools = plugin.get_mcp_tools("read")
        schema = tools["investigation_network"]["inputSchema"]
        assert "entry_id" in schema["required"]
        assert "kb_name" in schema["required"]

    def test_sources_tool_schema(self):
        plugin = JournalismInvestigationPlugin()
        tools = plugin.get_mcp_tools("read")
        schema = tools["investigation_sources"]["inputSchema"]
        props = schema["properties"]
        assert "reliability" in props
        assert "classification" in props
        assert "kb_name" in props

    def test_all_tools_have_handler(self):
        plugin = JournalismInvestigationPlugin()
        tools = plugin.get_mcp_tools("read")
        for name, tool in tools.items():
            assert "handler" in tool, f"{name} missing handler"
            assert callable(tool["handler"]), f"{name} handler not callable"

    def test_all_tools_have_description(self):
        plugin = JournalismInvestigationPlugin()
        tools = plugin.get_mcp_tools("read")
        for name, tool in tools.items():
            assert "description" in tool, f"{name} missing description"
            assert len(tool["description"]) > 10, f"{name} description too short"
