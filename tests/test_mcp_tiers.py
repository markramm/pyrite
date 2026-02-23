"""Tests for MCP server tier restrictions.

Verifies that read/write/admin tiers only expose appropriate tools.
"""

import tempfile
from pathlib import Path

import pytest

from pyrite.config import KBConfig, KBType, PyriteConfig, Settings
from pyrite.server.mcp_server import PyriteMCPServer


@pytest.mark.mcp
class TestMCPTierRestrictions:
    """Test that MCP tiers only expose appropriate tools."""

    @pytest.fixture
    def minimal_config(self):
        """Minimal config for tier testing (no sample data needed)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            kb_path = tmpdir / "kb"
            kb_path.mkdir()

            config = PyriteConfig(
                knowledge_bases=[KBConfig(name="test", path=kb_path, kb_type=KBType.EVENTS)],
                settings=Settings(index_path=tmpdir / "index.db"),
            )
            yield config

    def test_read_tier_has_read_tools(self, minimal_config):
        server = PyriteMCPServer(minimal_config, tier="read")
        try:
            assert "kb_list" in server.tools
            assert "kb_search" in server.tools
            assert "kb_get" in server.tools
            assert "kb_timeline" in server.tools
            assert "kb_backlinks" in server.tools
            assert "kb_tags" in server.tools
            assert "kb_stats" in server.tools
        finally:
            server.close()

    def test_read_tier_no_write_tools(self, minimal_config):
        server = PyriteMCPServer(minimal_config, tier="read")
        try:
            assert "kb_create" not in server.tools
            assert "kb_update" not in server.tools
            assert "kb_delete" not in server.tools
        finally:
            server.close()

    def test_read_tier_no_admin_tools(self, minimal_config):
        server = PyriteMCPServer(minimal_config, tier="read")
        try:
            assert "kb_index_sync" not in server.tools
            assert "kb_manage" not in server.tools
        finally:
            server.close()

    def test_write_tier_has_read_and_write(self, minimal_config):
        server = PyriteMCPServer(minimal_config, tier="write")
        try:
            # Has read tools
            assert "kb_list" in server.tools
            assert "kb_search" in server.tools
            # Has write tools
            assert "kb_create" in server.tools
            assert "kb_update" in server.tools
            assert "kb_delete" in server.tools
            # No admin tools
            assert "kb_index_sync" not in server.tools
            assert "kb_manage" not in server.tools
        finally:
            server.close()

    def test_admin_tier_has_all_tools(self, minimal_config):
        server = PyriteMCPServer(minimal_config, tier="admin")
        try:
            # Has read, write, and admin tools
            assert "kb_list" in server.tools
            assert "kb_create" in server.tools
            assert "kb_index_sync" in server.tools
            assert "kb_manage" in server.tools
        finally:
            server.close()

    def test_invalid_tier_raises(self, minimal_config):
        with pytest.raises(ValueError, match="Invalid tier"):
            PyriteMCPServer(minimal_config, tier="superadmin")

    def test_read_tier_tool_count(self, minimal_config):
        """Read tier should have fewer tools than write tier."""
        read_server = PyriteMCPServer(minimal_config, tier="read")
        write_server = PyriteMCPServer(minimal_config, tier="write")
        admin_server = PyriteMCPServer(minimal_config, tier="admin")
        try:
            read_count = len(read_server.tools)
            write_count = len(write_server.tools)
            admin_count = len(admin_server.tools)
            assert read_count < write_count < admin_count
        finally:
            read_server.close()
            write_server.close()
            admin_server.close()
