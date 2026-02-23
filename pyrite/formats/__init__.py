"""Format registry and content negotiation for Pyrite API responses."""

from dataclasses import dataclass
from typing import Any


@dataclass
class FormatSpec:
    """Specification for an output format."""

    name: str
    media_type: str
    file_extension: str
    serializer: Any  # callable: (data: Any, **kwargs) -> str


class FormatRegistry:
    """Registry of available output formats."""

    def __init__(self):
        self._formats: dict[str, FormatSpec] = {}

    def register(self, spec: FormatSpec):
        self._formats[spec.name] = spec

    def get(self, name: str) -> FormatSpec | None:
        return self._formats.get(name)

    def get_by_media_type(self, media_type: str) -> FormatSpec | None:
        for spec in self._formats.values():
            if spec.media_type == media_type:
                return spec
        return None

    def available_formats(self) -> list[str]:
        return list(self._formats.keys())


# Global registry singleton
_registry: FormatRegistry | None = None


def get_format_registry() -> FormatRegistry:
    global _registry
    if _registry is None:
        _registry = FormatRegistry()
        _register_defaults(_registry)
    return _registry


def _register_defaults(registry: FormatRegistry):
    from .csv_fmt import csv_serialize
    from .json_fmt import json_serialize
    from .markdown_fmt import markdown_serialize
    from .yaml_fmt import yaml_serialize

    registry.register(FormatSpec("json", "application/json", "json", json_serialize))
    registry.register(FormatSpec("markdown", "text/markdown", "md", markdown_serialize))
    registry.register(FormatSpec("csv", "text/csv", "csv", csv_serialize))
    registry.register(FormatSpec("yaml", "text/yaml", "yaml", yaml_serialize))


def negotiate_format(accept_header: str) -> str | None:
    """Parse Accept header and return best matching format name.

    Returns 'json' as default. Returns None if Accept specifies something
    we don't support and doesn't include */*.
    """
    if not accept_header or accept_header == "*/*":
        return "json"

    registry = get_format_registry()

    # Parse accept header (simplified -- handle basic cases)
    # Accept: text/markdown, application/json;q=0.9, */*;q=0.1
    parts = [p.strip() for p in accept_header.split(",")]

    # Sort by quality factor
    weighted = []
    for part in parts:
        if ";q=" in part:
            media, q = part.split(";q=", 1)
            try:
                weight = float(q)
            except ValueError:
                weight = 1.0
            weighted.append((media.strip(), weight))
        else:
            weighted.append((part.strip(), 1.0))

    weighted.sort(key=lambda x: x[1], reverse=True)

    for media_type, _ in weighted:
        if media_type == "*/*":
            return "json"
        spec = registry.get_by_media_type(media_type)
        if spec:
            return spec.name

    return None  # 406 Not Acceptable


def format_response(data: Any, format_name: str, **kwargs) -> tuple[str, str]:
    """Serialize data to the specified format.

    Returns (content_string, media_type).
    """
    registry = get_format_registry()
    spec = registry.get(format_name)
    if not spec:
        raise ValueError(f"Unknown format: {format_name}")
    return spec.serializer(data, **kwargs), spec.media_type
