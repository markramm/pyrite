"""A tool's tier is a property of the tool, not of the server instance
listing it (#234).

Core tools (`_build_read_tools`/`_build_write_tools`/`_build_admin_tools`)
label themselves unconditionally by which method registered them, so they
are stable by construction. Plugin tools were not, before #341: the old
`_register_plugin_tools` labelled *every* plugin tool it registered with
`self.tier` -- the constructing server's own tier -- rather than the tool's
own tier. So a plugin's read-only tool (say `sw_backlog`) was labelled
"read" on a read-tier server, correctly, but "write" on a write-tier server
and "admin" on an admin-tier server, because each server stamped its own
tier onto every plugin tool it saw, including the read ones it re-registers
at every higher tier. That mislabel matters beyond cosmetics: the per-KB
write check and the rate limiter both key off `_tool_tiers[name]`, so a
read-only plugin tool reached through a write- or admin-tier server was
checked -- and rate-limited -- as if it were a write.

#341 fixed the labelling (a tool's tier is now the *lowest* tier whose
`get_mcp_tools` returns it), but nothing asserted the fix across every
server construction in one place -- only
`tests/test_mcp_write_scoping.py::test_plugin_read_tools_are_classified_read`,
which checks plugin read tools on a *write*-tier server alone. This file is
that guard: it builds all three tiers for real (core and plugin tools
included, modeled on `tests/test_mcp_tool_registry_is_scoped.py`'s `servers`
fixture, because a hand list of tool names is exactly what let the mislabel
through before) and checks every tool's label agrees across every
construction that exposes it -- so a regression of the #341 shape (or a new
one like it) fails here rather than shipping silently again.
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
    tool at all, never a higher one.

    Checked at the *admin* server deliberately, not at the lowest exposing
    tier: the pre-#341 bug (`for name in plugin_tools: self._tool_tiers[name]
    = self.tier`) still labels a tool correctly at the one server that
    constructs it at its true tier -- a read tool's own read-tier server
    always says "read", bug or no bug. The bug only shows up on a *higher*
    tier's server, which relabels every plugin tool it re-registers with its
    own tier instead of preserving the lower one. Reading the label from
    `servers["admin"]` (the highest tier, so every tool is present there) is
    what makes this test fail under that bug; reading it from the lowest
    exposing tier's own server would pass either way, as this test did
    before it was corrected.
    """
    tier_index = {name: i for i, name in enumerate(TIERS)}

    for tool_name, expected in servers["admin"]._tool_tiers.items():
        exposing_tiers = [t for t in TIERS if tool_name in servers[t].tools]
        lowest = min(exposing_tiers, key=tier_index.get)
        assert expected == lowest, (
            f"{tool_name}: exposed starting at tier {lowest!r} but the admin "
            f"server labels it {expected!r}"
        )
