"""JSON encoding utilities."""

import json
from datetime import date, datetime
from pathlib import PurePath
from typing import Any


class SafeEncoder(json.JSONEncoder):
    """JSON encoder that serializes date/datetime/Path objects safely."""

    def default(self, o):
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        if isinstance(o, PurePath):
            return str(o)
        return super().default(o)


def echo_json(data: Any, *, indent: int = 2) -> None:
    """Write machine-readable JSON to stdout, bypassing Rich.

    ``console.print`` renders its argument as rich text, which corrupts JSON two
    different ways. With stdout attached to a pipe Rich cannot detect a terminal
    width, falls back to 80 columns and hard-wraps, putting real newlines inside
    string values; and under ``FORCE_COLOR`` (which many CI systems set) it
    syntax-highlights the result with ANSI escapes. Either one makes
    ``json.loads`` fail for the caller that asked for ``--json``.

    ``print`` rather than ``typer.echo`` is deliberate: this module is imported
    by installs that do not have the ``cli`` extra, so it must not depend on
    typer or rich.
    """
    print(json.dumps(data, indent=indent))
