"""Tests for the shared CLI error helper (cli-error-shape-consistency)."""

import json

import pytest
import typer

from pyrite.utils.errors import build_error, cli_error


def test_build_error_shape():
    """build_error returns the canonical agent-facing error dict, matching the
    MCP _error() shape."""
    payload = build_error(
        "Entry 'foo' not found",
        "NOT_FOUND",
        suggestion="try `pyrite search foo`",
    )
    assert payload == {
        "error": "Entry 'foo' not found",
        "error_code": "NOT_FOUND",
        "suggestion": "try `pyrite search foo`",
        "retryable": False,
    }


def test_build_error_minimal():
    """Only message + code are required; optional fields omitted when unset."""
    payload = build_error("boom", "VALIDATION_FAILED")
    assert payload["error"] == "boom"
    assert payload["error_code"] == "VALIDATION_FAILED"
    assert "suggestion" not in payload
    assert payload["retryable"] is False


def test_cli_error_json_format(capsys):
    """In a machine format, cli_error emits the structured payload as JSON and
    exits non-zero."""
    with pytest.raises(typer.Exit) as exc:
        cli_error("KB not found: x", "json", error_code="KB_NOT_FOUND",
                  suggestion="run `pyrite kb list`")
    assert exc.value.exit_code == 1
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["error_code"] == "KB_NOT_FOUND"
    assert parsed["error"] == "KB not found: x"
    assert parsed["suggestion"] == "run `pyrite kb list`"


def test_cli_error_rich_format(capsys):
    """In rich format, cli_error prints a colored single line with the code."""
    with pytest.raises(typer.Exit):
        cli_error("KB not found: x", "rich", error_code="KB_NOT_FOUND")
    out = capsys.readouterr().out
    assert "KB_NOT_FOUND" in out
    assert "KB not found: x" in out


def test_search_unregistered_kb_returns_kb_not_found():
    """`pyrite search -k <unknown>` must fail with KB_NOT_FOUND, not an empty
    result set that looks like a query miss (cli-error-shape-consistency #4)."""
    from typer.testing import CliRunner

    from pyrite.cli import app

    runner = CliRunner()
    result = runner.invoke(
        app, ["search", "anything", "-k", "definitely-not-a-real-kb", "--format", "json"]
    )
    assert result.exit_code == 1
    parsed = json.loads(result.stdout)
    assert parsed["error_code"] == "KB_NOT_FOUND"
    assert "definitely-not-a-real-kb" in parsed["error"]
