"""Importer registry for bulk entry import."""

from typing import Any


class ImporterRegistry:
    """Registry of format importers."""

    def __init__(self):
        self._importers: dict[str, Any] = {}

    def register(self, name: str, importer):
        self._importers[name] = importer

    def get(self, name: str):
        return self._importers.get(name)

    def available_formats(self) -> list[str]:
        return list(self._importers.keys())


_registry: ImporterRegistry | None = None


def get_importer_registry() -> ImporterRegistry:
    global _registry
    if _registry is None:
        _registry = ImporterRegistry()
        _register_defaults(_registry)
    return _registry


def _register_defaults(registry: ImporterRegistry):
    from .csv_importer import import_csv
    from .json_importer import import_json
    from .markdown_importer import import_markdown

    registry.register("json", import_json)
    registry.register("markdown", import_markdown)
    registry.register("csv", import_csv)
