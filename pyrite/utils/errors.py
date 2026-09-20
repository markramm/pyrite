"""Shared agent-facing error shape for the CLI.

A single canonical structure so that errors look the same whether they come from
the CLI, MCP (`mcp_server._error`), or the REST PyriteError handler:

    {
      "error": "human message",
      "error_code": "MACHINE_CODE",
      "suggestion": "optional fix hint",   # omitted when not provided
      "retryable": false,
    }

Promoted from the duplicated `_cli_error` helpers in entry_commands.py and
browse_commands.py (cli-error-shape-consistency).
"""

from __future__ import annotations

import json
from typing import Any

import typer


def build_error(
    message: str,
    error_code: str,
    *,
    suggestion: str | None = None,
    retryable: bool = False,
) -> dict[str, Any]:
    """Build the canonical error dict. `suggestion` is omitted when unset."""
    payload: dict[str, Any] = {
        "error": message,
        "error_code": error_code,
        "retryable": retryable,
    }
    if suggestion:
        payload["suggestion"] = suggestion
    return payload


def cli_error(
    message: str,
    output_format: str = "rich",
    *,
    error_code: str = "ERROR",
    suggestion: str | None = None,
    retryable: bool = False,
) -> None:
    """Print a structured (machine formats) or colored single-line (rich) error
    and raise ``typer.Exit(1)``.

    Machine formats (anything other than ``rich``) get the JSON payload on
    stdout so scripts/agents can parse it; rich gets a human line:

        ERROR [KB_NOT_FOUND]: KB not found: x
            hint: run `pyrite kb list`
    """
    payload = build_error(message, error_code, suggestion=suggestion, retryable=retryable)
    if output_format != "rich":
        typer.echo(json.dumps(payload))
    else:
        from rich.console import Console
        from rich.text import Text

        console = Console()
        # The styled labels are ours and stay markup; `message` and
        # `suggestion` are data -- an extra like `pyrite[semantic]`, a JSON
        # example, an entry id -- and Rich would parse their brackets as style
        # tags. `pip install pyrite[semantic]` rendered as `pip install
        # pyrite`, a command that does not fix the error it is offered for.
        # Wrapping them in `Text` is what keeps them literal -- passing them as
        # a separate argument is NOT enough, Rich parses each string argument.
        console.print(f"[red]ERROR[/red] [[yellow]{error_code}[/yellow]]:", Text(message))
        if suggestion:
            console.print("    [dim]hint:[/dim]", Text(suggestion))
    raise typer.Exit(1)
