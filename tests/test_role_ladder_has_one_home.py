"""The role ladder is written out once, in `pyrite/services/access_policy.py` (#383).

A grep ratchet (ADR-0037 §5.3, theme 1's half of it): the ladder literal
(`{"read": 0, ...}`) and the list of valid roles (`("read", "write",
"admin")`, in any bracket) appear in the policy module and nowhere else under
`pyrite/`. Everything else imports `ROLES` / `ROLE_LEVELS` or asks
`role_at_least`, so a change to the ladder is one edit, and a copy that
drifts from it cannot be written without this test failing.

Extensions (`extensions/*`) are separate packages and outside this ratchet;
the plugin contract is #384's.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE = REPO_ROOT / "pyrite"
HOME = "pyrite/services/access_policy.py"

LADDER = re.compile(r"""\{\s*["']read["']\s*:\s*0""")
ROLE_LIST = re.compile(
    r"""[(\[{]\s*["']read["']\s*,\s*["']write["']\s*,\s*["']admin["']\s*,?\s*[)\]}]"""
)


def _hits(pattern: re.Pattern[str]) -> dict[str, int]:
    found: dict[str, int] = {}
    for path in sorted(PACKAGE.rglob("*.py")):
        count = len(pattern.findall(path.read_text()))
        if count:
            found[path.relative_to(REPO_ROOT).as_posix()] = count
    return found


def test_the_ladder_literal_is_only_in_the_policy():
    assert _hits(LADDER) == {HOME: 1}


def test_the_role_list_literal_is_only_in_the_policy():
    assert _hits(ROLE_LIST) == {HOME: 1}


@pytest.mark.control(reason="tests the ratchet's own patterns: true on either side of the change")
def test_the_patterns_catch_every_spelling():
    for text in (
        '{"read": 0, "write": 1, "admin": 2}',
        "{'read':0}",
    ):
        assert LADDER.search(text), text
    for text in (
        '("read", "write", "admin")',
        '["read", "write", "admin"]',
        "{'read','write','admin'}",
        '(\n    "read",\n    "write",\n    "admin",\n)',
    ):
        assert ROLE_LIST.search(text), text
