"""A tool's tier is a property of the tool, not of the server instance
listing it (#234).

Core tools (`_build_read_tools`/`_build_write_tools`/`_build_admin_tools`)
label themselves unconditionally by which method registered them, so they
are stable by construction. Plugin tools are not: `_register_plugin_tools`
*infers* each plugin tool's tier from which of `registry.get_all_mcp_tools`
first returns it, walking tiers up to `self.tier`. That inference runs once
per server construction, over whatever `self.tier` happens to be -- so a
plugin whose `get_mcp_tools(tier)` is not cumulative (a write-tier call that
does not also return everything the read tier returns, for instance) could
have a tool labelled "read" on one server and "write" on another, silently,
because the label is never checked across constructions in one place.

Modeled on `tests/test_mcp_tool_registry_is_scoped.py`'s `servers` fixture:
one real `PyriteMCPServer` per tier, real plugin tools included, because a
hand list of tool names is exactly what let a mislabel through before
(#341 fixed the read/write split for one server; nothing asserted it holds
*across* server constructions).
"""

import tempfile
from pathlib import Path

import pytest

from pyrite.config import KBConfig, PyriteConfig, Settings
from pyrite.server.mcp_server import PyriteMCPServer

TIERS = ("read", "write", "admin")


@pytest.fixture(scope="module")
def servers():
    """One real `PyriteMCPServer` per tier, with plugin tools registered."""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        (tmp / "gate-kb").mkdir()
        config = PyriteConfig(
            knowledge_bases=[KBConfig(name="gate-kb", path=tmp / "gate-kb", kb_type="generic")],
            settings=Settings(index_path=tmp / "index.db"),
        )
        built = {t: PyriteMCPServer(config=config, tier=t) for t in TIERS}
        try:
            yield built
        finally:
            for s in built.values():
                s.close()


def test_every_tool_reports_the_same_tier_across_every_construction_it_appears_in(servers):
    """For each tool present in more than one tier's server, `_tool_tiers[name]`
    must agree across all constructions that expose it. `sw_backlog` is the
    concrete case the acceptance criteria name: it must report the same tier
    whether it is reached through a read-tier or an admin-tier server."""
    tiers_seen: dict[str, set[str]] = {}
    for server in servers.values():
        for tool_name in server.tools:
            tiers_seen.setdefault(tool_name, set()).add(server._tool_tiers[tool_name])

    unstable = {name: labels for name, labels in tiers_seen.items() if len(labels) > 1}
    assert not unstable, f"tools whose reported tier differs by server construction: {unstable}"


def test_sw_backlog_reports_the_same_tier_through_a_read_or_admin_server(servers):
    """The concrete case named in the acceptance criteria, spelled out on its
    own so a regression here fails with an obvious message rather than
    needing to be found inside the aggregate report above."""
    if "sw_backlog" not in servers["read"].tools:
        pytest.skip("sw_backlog not registered (software-kb plugin not installed)")
    read_tier = servers["read"]._tool_tiers["sw_backlog"]
    admin_tier = servers["admin"]._tool_tiers["sw_backlog"]
    assert read_tier == admin_tier == "read"


def test_each_tools_label_is_the_lowest_construction_that_exposes_it(servers):
    """A tool's declared tier is which tier's `get_mcp_tools(tier)` *first*
    returns it (#341's inference, accepted as the declaration) -- so the
    label must be the lowest tier index among the servers that expose the
    tool at all, never a higher one."""
    tier_index = {name: i for i, name in enumerate(TIERS)}

    for tool_name in servers["admin"].tools:
        exposing_tiers = [t for t in TIERS if tool_name in servers[t].tools]
        lowest = min(exposing_tiers, key=tier_index.get)
        label = servers[lowest]._tool_tiers[tool_name]
        assert label == lowest, (
            f"{tool_name}: exposed starting at tier {lowest!r} but labelled {label!r}"
        )
