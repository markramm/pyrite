"""Schema provisioning service — programmatic management of kb.yaml type schemas."""

from typing import Any

from pyrite.config import KBConfig, PyriteConfig
from pyrite.utils.yaml import dump_yaml_file, load_yaml_file


class SchemaService:
    """Manage kb.yaml schemas programmatically.

    Provides show/add/remove/set operations for type definitions
    in a KB's kb.yaml file.
    """

    def __init__(self, config: PyriteConfig):
        self.config = config

    def _get_kb(self, kb_name: str) -> KBConfig:
        """Get KB config or raise."""
        kb = self.config.get_kb(kb_name)
        if not kb:
            raise ValueError(f"KB '{kb_name}' not found")
        return kb

    def _load_kb_yaml(self, kb: KBConfig) -> dict[str, Any]:
        """Load kb.yaml, returning empty dict if missing."""
        if kb.kb_yaml_path.exists():
            return load_yaml_file(kb.kb_yaml_path)
        return {}

    def _save_kb_yaml(self, kb: KBConfig, data: dict[str, Any]) -> None:
        """Save kb.yaml and refresh in-memory config."""
        kb.kb_yaml_path.parent.mkdir(parents=True, exist_ok=True)
        dump_yaml_file(data, kb.kb_yaml_path)
        kb.load_kb_yaml()

    def show_schema(self, kb_name: str) -> dict[str, Any]:
        """Show the current schema for a KB."""
        kb = self._get_kb(kb_name)
        data = self._load_kb_yaml(kb)
        return {
            "kb_name": kb_name,
            "types": data.get("types", {}),
            "policies": data.get("policies", {}),
            "validation": data.get("validation", {}),
        }

    def add_type(
        self, kb_name: str, type_name: str, type_def: dict[str, Any]
    ) -> dict[str, Any]:
        """Add a type definition to kb.yaml.

        Args:
            kb_name: Knowledge base name.
            type_name: Type name to add.
            type_def: Type definition with description, required, optional, subdirectory.

        Returns:
            Result dict with added status.
        """
        kb = self._get_kb(kb_name)
        data = self._load_kb_yaml(kb)

        types = data.get("types", {})
        if type_name in types:
            return {"error": f"Type '{type_name}' already exists in KB '{kb_name}'"}

        types[type_name] = type_def
        data["types"] = types
        self._save_kb_yaml(kb, data)

        return {"added": True, "type_name": type_name, "kb_name": kb_name}

    def remove_type(self, kb_name: str, type_name: str) -> dict[str, Any]:
        """Remove a type definition from kb.yaml.

        Args:
            kb_name: Knowledge base name.
            type_name: Type name to remove.

        Returns:
            Result dict with removed status.
        """
        kb = self._get_kb(kb_name)
        data = self._load_kb_yaml(kb)

        types = data.get("types", {})
        if type_name not in types:
            return {"error": f"Type '{type_name}' not found in KB '{kb_name}'"}

        del types[type_name]
        data["types"] = types
        self._save_kb_yaml(kb, data)

        return {"removed": True, "type_name": type_name, "kb_name": kb_name}

    def set_schema(self, kb_name: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Replace the schema sections (types, policies, validation) in kb.yaml.

        Preserves name, description, and other top-level keys.

        Args:
            kb_name: Knowledge base name.
            schema: Dict with types, policies, validation keys.

        Returns:
            Result dict with set status.
        """
        kb = self._get_kb(kb_name)
        data = self._load_kb_yaml(kb)

        if "types" in schema:
            data["types"] = schema["types"]
        if "policies" in schema:
            data["policies"] = schema["policies"]
        if "validation" in schema:
            data["validation"] = schema["validation"]

        self._save_kb_yaml(kb, data)

        type_count = len(data.get("types", {}))
        return {"set": True, "kb_name": kb_name, "type_count": type_count}
