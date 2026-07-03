"""Contract test: README.md's MCP tool-tier table must match the real tool
sets in tool_schemas.py.

Regression coverage: the table's read-tier count went stale twice (11 ->
23 -> 29 actual) as orient/batch_read/task_DAG tools were added without
updating the README's hardcoded tier table alongside pyrite/server/
mcp_server.py's --help text (already self-correcting per
docs-operational-contracts-travel-with-tool item 5). This test locks the
README table the same way so it can't silently drift again.
"""

import re
from pathlib import Path

from pyrite.server.tool_schemas import ADMIN_TOOLS, READ_TOOLS, WRITE_TOOLS

README_PATH = Path(__file__).resolve().parent.parent / "README.md"
GETTING_STARTED_PATH = Path(__file__).resolve().parent.parent / "docs" / "getting-started.md"


def _extract_tier_row(readme_text: str, tier: str) -> tuple[int, list[str]]:
    """Parse `| **<tier>** (N) | tool, tool, ... |` (or `(+N)` for
    write/admin) into (declared_count, tool_names)."""
    pattern = rf"\|\s*\*\*{tier}\*\*\s*\(\+?(\d+)\)\s*\|(.+?)\|\s*\n"
    match = re.search(pattern, readme_text)
    assert match, f"could not find a '{tier}' tier row in README.md's MCP tool table"
    count = int(match.group(1))
    tools = re.findall(r"`([a-z_]+)`", match.group(2))
    return count, tools


def test_readme_read_tier_count_and_tools_match_actual():
    readme_text = README_PATH.read_text()
    declared_count, declared_tools = _extract_tier_row(readme_text, "read")

    assert declared_count == len(READ_TOOLS), (
        f"README says read tier has {declared_count} tools; "
        f"tool_schemas.READ_TOOLS actually has {len(READ_TOOLS)}"
    )
    assert set(declared_tools) == set(READ_TOOLS), (
        f"README's read-tier tool list doesn't match READ_TOOLS. "
        f"Missing from README: {set(READ_TOOLS) - set(declared_tools)}. "
        f"Extra in README: {set(declared_tools) - set(READ_TOOLS)}."
    )


def test_readme_write_tier_count_and_tools_match_actual():
    readme_text = README_PATH.read_text()
    declared_count, declared_tools = _extract_tier_row(readme_text, "write")

    assert declared_count == len(WRITE_TOOLS), (
        f"README says write tier adds {declared_count} tools; "
        f"tool_schemas.WRITE_TOOLS actually has {len(WRITE_TOOLS)}"
    )
    assert set(declared_tools) == set(WRITE_TOOLS), (
        f"README's write-tier tool list doesn't match WRITE_TOOLS. "
        f"Missing from README: {set(WRITE_TOOLS) - set(declared_tools)}. "
        f"Extra in README: {set(declared_tools) - set(WRITE_TOOLS)}."
    )


def test_readme_admin_tier_count_and_tools_match_actual():
    readme_text = README_PATH.read_text()
    declared_count, declared_tools = _extract_tier_row(readme_text, "admin")

    assert declared_count == len(ADMIN_TOOLS), (
        f"README says admin tier adds {declared_count} tools; "
        f"tool_schemas.ADMIN_TOOLS actually has {len(ADMIN_TOOLS)}"
    )
    assert set(declared_tools) == set(ADMIN_TOOLS), (
        f"README's admin-tier tool list doesn't match ADMIN_TOOLS. "
        f"Missing from README: {set(ADMIN_TOOLS) - set(declared_tools)}. "
        f"Extra in README: {set(declared_tools) - set(ADMIN_TOOLS)}."
    )


def test_getting_started_tool_counts_match_actual():
    """docs/getting-started.md has its own prose sentence with the same
    three tier counts (not a table, just inline numbers) -- same drift
    risk as the README table, verified separately since the text shape
    differs."""
    text = GETTING_STARTED_PATH.read_text()
    match = re.search(r"gets (\d+) read tools, (\d+) write tools, and (\d+) admin tools", text)
    assert match, "expected the '<N> read tools, <N> write tools, <N> admin tools' sentence"
    read_count, write_count, admin_count = (int(g) for g in match.groups())

    assert read_count == len(READ_TOOLS), (
        f"getting-started.md says {read_count} read tools; actual {len(READ_TOOLS)}"
    )
    assert write_count == len(WRITE_TOOLS), (
        f"getting-started.md says {write_count} write tools; actual {len(WRITE_TOOLS)}"
    )
    assert admin_count == len(ADMIN_TOOLS), (
        f"getting-started.md says {admin_count} admin tools; actual {len(ADMIN_TOOLS)}"
    )
