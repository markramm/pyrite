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


def test_getting_started_points_to_generated_counts_instead_of_retyping_them():
    """docs/getting-started.md used to state its own "<N> read tools, <N>
    write tools, <N> admin tools" sentence, which drifted the same way the
    README table and `pyrite mcp --help` did (#229: the undocumented 41+
    plugin tools per tier made any hardcoded core-only count wrong by
    2.4x). Per kb/backlog/docs-counts-generated-or-asserted-from-code.md
    rule 1 ("don't state what will drift"), the sentence was replaced with
    a pointer to `pyrite mcp --help`, whose counts are generated from the
    live tool registry (see test_mcp_help_tool_counts.py). This test pins
    that the pointer exists and that the old drift-prone sentence shape is
    gone, rather than re-asserting numbers here that would just be a third
    place to drift."""
    text = GETTING_STARTED_PATH.read_text()

    assert "pyrite mcp --help" in text, (
        "expected getting-started.md to point readers at the generated "
        "tool-count source instead of stating its own numbers"
    )

    stale_sentence = re.search(r"gets \d+ read tools, \d+ write tools, and \d+ admin tools", text)
    assert stale_sentence is None, (
        "getting-started.md re-introduced a hardcoded tool-count sentence "
        f"that will drift again: {stale_sentence.group(0) if stale_sentence else ''}"
    )
