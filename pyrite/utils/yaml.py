"""Round-trip safe YAML utilities using ruamel.yaml.

Preserves comments, quoting style, and key ordering — producing minimal
git diffs when only a single field changes.
"""

from io import StringIO
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML


def _get_yaml() -> YAML:
    """Get a configured YAML instance for round-trip processing."""
    y = YAML()
    y.preserve_quotes = True
    y.default_flow_style = False
    y.width = 4096  # prevent line wrapping
    return y


def load_yaml(text: str) -> dict[str, Any]:
    """Load YAML from a string.

    Returns a CommentedMap (dict-compatible MutableMapping) that preserves
    comments and quoting when later passed to ``dump_yaml``.  Returns an
    empty dict for blank / ``None`` input.
    """
    y = _get_yaml()
    result = y.load(text)
    return result if result is not None else {}


def dump_yaml(data: Any) -> str:
    """Dump a mapping to a YAML string, preserving style.

    The returned string has no trailing newline so it can be embedded
    directly inside YAML frontmatter fences.
    """
    y = _get_yaml()
    stream = StringIO()
    y.dump(data, stream)
    return stream.getvalue().rstrip("\n")


def load_yaml_file(path: str | Path) -> dict[str, Any]:
    """Load YAML from a file path.

    Returns a CommentedMap (dict-compatible) or empty dict.
    """
    p = Path(path)
    y = _get_yaml()
    with open(p) as f:
        result = y.load(f)
    return result if result is not None else {}


def dump_yaml_file(data: Any, path: str | Path) -> None:
    """Write a mapping to a YAML file, preserving style."""
    p = Path(path)
    y = _get_yaml()
    with open(p, "w") as f:
        y.dump(data, f)
