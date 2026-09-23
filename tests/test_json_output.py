"""Machine-readable JSON output must survive being piped (issue #321).

These tests are deliberately isolated: they import one leaf module,
``pyrite.utils.json_utils``, which is pure stdlib and whose package ``__init__``
is empty. Only builtin fixtures (``capsys``, ``monkeypatch``) are used, so the
file runs with nothing installed but pytest itself -- no CLI, no database, no
extension, and none of the rest of the suite::

    pytest tests/test_json_output.py --noconftest -q

``--noconftest`` is what buys that: ``tests/conftest.py`` imports
``pyrite.config``, ``pyrite.models`` and ``pyrite.storage`` at module scope, so
without it pytest would load the whole application just to reach these tests.
They also pass as part of a normal full-suite run.
"""

import json
import re
from pathlib import Path

import pytest

from pyrite.utils.json_utils import echo_json

REPO_ROOT = Path(__file__).resolve().parents[1]

# Longer than Rich's 80-column fallback, so a regression wraps and corrupts it.
LONG_VALUE = "x" * 150


def test_long_value_is_not_wrapped(capsys):
    """Rich hard-wraps at 80 columns when stdout is not a terminal."""
    echo_json({"title": LONG_VALUE})

    out = capsys.readouterr().out
    assert json.loads(out)["title"] == LONG_VALUE


def test_no_line_exceeds_the_value_it_holds(capsys):
    """A wrapped value shows up as a newline inside the string, not just bad JSON."""
    echo_json({"url": "https://example.com/" + "a" * 200})

    out = capsys.readouterr().out
    assert json.loads(out)["url"].count("\n") == 0


@pytest.mark.parametrize("env_value", ["1", "true"])
def test_no_ansi_escapes_under_force_color(monkeypatch, capsys, env_value):
    """Rich syntax-highlights JSON under FORCE_COLOR; that also breaks json.loads."""
    monkeypatch.setenv("FORCE_COLOR", env_value)
    payload = {"title": LONG_VALUE, "count": 42, "ok": True, "missing": None}

    echo_json(payload)

    out = capsys.readouterr().out
    assert "\x1b[" not in out, "ANSI escape found: output went through Rich"
    assert json.loads(out) == payload


def test_round_trips_nested_and_escaped_content(capsys):
    payload = {
        "entries": [{"id": i, "body": f"line one\nline two {LONG_VALUE}"} for i in range(3)],
        "quote": 'he said "hi"',
        "tab": "a\tb",
        "unicode": "café — ☕",
    }

    echo_json(payload)

    assert json.loads(capsys.readouterr().out) == payload


def test_indent_is_two_by_default_and_overridable(capsys):
    echo_json({"a": {"b": 1}})
    assert '\n  "a"' in capsys.readouterr().out

    echo_json({"a": {"b": 1}}, indent=None)
    out = capsys.readouterr().out
    assert out == '{"a": {"b": 1}}\n'


def test_emits_exactly_one_trailing_newline(capsys):
    echo_json({"a": 1})

    out = capsys.readouterr().out
    assert out.endswith("}\n") and not out.endswith("}\n\n")


def test_no_source_file_prints_json_through_rich():
    """Acceptance criterion: the grep in issue #321 must return nothing.

    Guards all 19 converted call sites at once, without importing any of them.
    """
    offender = re.compile(r"console\.print\(\s*(?:json|json_mod)\.dumps")
    hits = []
    for package in ("pyrite", "extensions"):
        for path in sorted((REPO_ROOT / package).rglob("*.py")):
            if "/tests/" in path.as_posix():
                continue
            if offender.search(path.read_text(encoding="utf-8")):
                hits.append(str(path.relative_to(REPO_ROOT)))

    assert hits == [], f"JSON still printed through Rich in: {hits}"
