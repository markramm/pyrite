"""
Plugin Registry

Discovers and manages pyrite plugins via Python entry points.

Plugins register via pyproject.toml:

    [project.entry-points."pyrite.plugins"]
    my_plugin = "my_package.plugin:MyPlugin"
"""

import logging
from collections.abc import Callable
from typing import Any

from .context import PluginContext
from .protocol import PyritePlugin

logger = logging.getLogger(__name__)

# Singleton registry
_registry: "PluginRegistry | None" = None


class PluginRegistry:
    """
    Discovers and manages pyrite plugins.

    Lazy singleton — call get_registry() to access.
    """

    ENTRY_POINT_GROUP = "pyrite.plugins"

    def __init__(self):
        self._plugins: dict[str, PyritePlugin] = {}
        self._discovered = False

    def discover(self) -> None:
        """Discover plugins via entry points."""
        if self._discovered:
            return

        try:
            from importlib.metadata import entry_points

            eps = entry_points()
            # Python 3.12+ returns SelectableGroups
            if hasattr(eps, "select"):
                plugin_eps = eps.select(group=self.ENTRY_POINT_GROUP)
            else:
                plugin_eps = eps.get(self.ENTRY_POINT_GROUP, [])

            for ep in plugin_eps:
                try:
                    plugin_class = ep.load()
                    plugin = plugin_class()
                    if hasattr(plugin, "name"):
                        self._plugins[plugin.name] = plugin
                        logger.info("Loaded plugin: %s", plugin.name)
                    else:
                        logger.warning("Plugin %s has no 'name' attribute, skipping", ep.name)
                except Exception as e:
                    logger.warning("Failed to load plugin %s: %s", ep.name, e)

        except Exception as e:
            logger.warning("Plugin discovery failed: %s", e)

        self._discovered = True

    def register(self, plugin: PyritePlugin) -> None:
        """Manually register a plugin (for testing or programmatic use)."""
        self._plugins[plugin.name] = plugin

    def set_context(self, ctx: PluginContext) -> None:
        """Inject shared context into all discovered plugins."""
        self.discover()
        for plugin in self._plugins.values():
            if hasattr(plugin, "set_context"):
                try:
                    plugin.set_context(ctx)
                except Exception as e:
                    logger.warning("Plugin %s set_context failed: %s", plugin.name, e)

    def get_plugin(self, name: str) -> PyritePlugin | None:
        """Get a plugin by name."""
        self.discover()
        return self._plugins.get(name)

    def list_plugins(self) -> list[str]:
        """List all discovered plugin names."""
        self.discover()
        return list(self._plugins.keys())

    # =========================================================================
    # Aggregation methods — collect capabilities from all plugins
    # =========================================================================

    def _merge_dict(
        self, target: dict, source: dict, plugin_name: str, kind: str
    ) -> None:
        """Merge source into target, warning on key collisions."""
        for key, value in source.items():
            if key in target:
                logger.warning(
                    "Plugin '%s' registers %s '%s' which conflicts with an "
                    "existing registration — last writer wins",
                    plugin_name,
                    kind,
                    key,
                )
            target[key] = value

    def get_all_entry_types(self) -> dict[str, type]:
        """Get all custom entry types from all plugins."""
        self.discover()
        types = {}
        for plugin in self._plugins.values():
            if hasattr(plugin, "get_entry_types"):
                try:
                    plugin_types = plugin.get_entry_types()
                    if plugin_types:
                        self._merge_dict(types, plugin_types, plugin.name, "entry type")
                except Exception as e:
                    logger.warning("Plugin %s get_entry_types failed: %s", plugin.name, e)
        return types

    def get_all_kb_types(self) -> list[str]:
        """Get all custom KB types from all plugins."""
        self.discover()
        kb_types = []
        for plugin in self._plugins.values():
            if hasattr(plugin, "get_kb_types"):
                try:
                    plugin_types = plugin.get_kb_types()
                    if plugin_types:
                        kb_types.extend(plugin_types)
                except Exception as e:
                    logger.warning("Plugin %s get_kb_types failed: %s", plugin.name, e)
        return kb_types

    def get_all_cli_commands(self) -> list[tuple[str, Any]]:
        """Get all CLI commands from all plugins."""
        self.discover()
        commands = []
        for plugin in self._plugins.values():
            if hasattr(plugin, "get_cli_commands"):
                try:
                    plugin_commands = plugin.get_cli_commands()
                    if plugin_commands:
                        commands.extend(plugin_commands)
                except Exception as e:
                    logger.warning("Plugin %s get_cli_commands failed: %s", plugin.name, e)
        return commands

    def get_all_mcp_tools(self, tier: str) -> dict[str, dict]:
        """Get all MCP tools for the given tier from all plugins."""
        self.discover()
        tools = {}
        for plugin in self._plugins.values():
            if hasattr(plugin, "get_mcp_tools"):
                try:
                    plugin_tools = plugin.get_mcp_tools(tier)
                    if plugin_tools:
                        self._merge_dict(tools, plugin_tools, plugin.name, "MCP tool")
                except Exception as e:
                    logger.warning("Plugin %s get_mcp_tools failed: %s", plugin.name, e)
        return tools

    def get_all_db_columns(self) -> list[dict]:
        """Get all additional DB columns from all plugins."""
        self.discover()
        columns = []
        for plugin in self._plugins.values():
            if hasattr(plugin, "get_db_columns"):
                try:
                    plugin_columns = plugin.get_db_columns()
                    if plugin_columns:
                        columns.extend(plugin_columns)
                except Exception as e:
                    logger.warning("Plugin %s get_db_columns failed: %s", plugin.name, e)
        return columns

    def get_all_relationship_types(self) -> dict[str, dict]:
        """Get all relationship types from all plugins."""
        self.discover()
        rel_types = {}
        for plugin in self._plugins.values():
            if hasattr(plugin, "get_relationship_types"):
                try:
                    plugin_rels = plugin.get_relationship_types()
                    if plugin_rels:
                        self._merge_dict(rel_types, plugin_rels, plugin.name, "relationship type")
                except Exception as e:
                    logger.warning("Plugin %s get_relationship_types failed: %s", plugin.name, e)
        return rel_types

    def get_all_workflows(self) -> dict[str, dict]:
        """Get all workflow definitions from all plugins."""
        self.discover()
        workflows = {}
        for plugin in self._plugins.values():
            if hasattr(plugin, "get_workflows"):
                try:
                    plugin_workflows = plugin.get_workflows()
                    if plugin_workflows:
                        self._merge_dict(workflows, plugin_workflows, plugin.name, "workflow")
                except Exception as e:
                    logger.warning("Plugin %s get_workflows failed: %s", plugin.name, e)
        return workflows

    def validate_transition(
        self, workflow_name: str, current_state: str, target_state: str, user_role: str = ""
    ) -> bool:
        """Check if a workflow transition is allowed."""
        workflows = self.get_all_workflows()
        workflow = workflows.get(workflow_name)
        if not workflow:
            return False

        for transition in workflow.get("transitions", []):
            if transition["from"] == current_state and transition["to"] == target_state:
                required_role = transition.get("requires", "")
                if not required_role or required_role == user_role:
                    return True
        return False

    def get_all_db_tables(self) -> list[dict]:
        """Get all custom DB table definitions from all plugins."""
        self.discover()
        tables = []
        for plugin in self._plugins.values():
            if hasattr(plugin, "get_db_tables"):
                try:
                    plugin_tables = plugin.get_db_tables()
                    if plugin_tables:
                        tables.extend(plugin_tables)
                except Exception as e:
                    logger.warning("Plugin %s get_db_tables failed: %s", plugin.name, e)
        return tables

    def get_all_hooks(self) -> dict[str, list[Callable]]:
        """Get all lifecycle hooks from all plugins, merged by hook name."""
        self.discover()
        hooks: dict[str, list[Callable]] = {}
        for plugin in self._plugins.values():
            if hasattr(plugin, "get_hooks"):
                try:
                    plugin_hooks = plugin.get_hooks()
                    if plugin_hooks:
                        for hook_name, hook_list in plugin_hooks.items():
                            hooks.setdefault(hook_name, []).extend(hook_list)
                except Exception as e:
                    logger.warning("Plugin %s get_hooks failed: %s", plugin.name, e)
        return hooks

    def run_hooks(self, hook_name: str, entry: Any, context: dict) -> Any:
        """Run all hooks for a given hook point. Returns the (possibly modified) entry.

        Raises if any before_* hook raises (to abort the operation).
        """
        hooks = self.get_all_hooks().get(hook_name, [])
        for hook in hooks:
            try:
                result = hook(entry, context)
                if result is not None:
                    entry = result
            except Exception:
                if hook_name.startswith("before_"):
                    raise  # Let before_* hooks abort operations
                logger.warning("Hook %s failed for %s", hook_name, hook.__name__, exc_info=True)
        return entry

    def get_all_kb_presets(self) -> dict[str, dict]:
        """Get all KB presets from all plugins."""
        self.discover()
        presets = {}
        for plugin in self._plugins.values():
            if hasattr(plugin, "get_kb_presets"):
                try:
                    plugin_presets = plugin.get_kb_presets()
                    if plugin_presets:
                        self._merge_dict(presets, plugin_presets, plugin.name, "KB preset")
                except Exception as e:
                    logger.warning("Plugin %s get_kb_presets failed: %s", plugin.name, e)
        return presets

    def get_all_type_metadata(self) -> dict[str, dict]:
        """Get type metadata from all plugins."""
        self.discover()
        metadata: dict[str, dict] = {}
        for plugin in self._plugins.values():
            if hasattr(plugin, "get_type_metadata"):
                try:
                    plugin_meta = plugin.get_type_metadata()
                    if plugin_meta:
                        for type_name, meta in plugin_meta.items():
                            metadata.setdefault(type_name, {})
                            if meta.get("ai_instructions"):
                                metadata[type_name]["ai_instructions"] = meta["ai_instructions"]
                            if meta.get("field_descriptions"):
                                metadata[type_name].setdefault("field_descriptions", {}).update(
                                    meta["field_descriptions"]
                                )
                            if meta.get("display"):
                                metadata[type_name].setdefault("display", {}).update(
                                    meta["display"]
                                )
                except Exception as e:
                    logger.warning("Plugin %s get_type_metadata failed: %s", plugin.name, e)
        return metadata

    def get_all_collection_types(self) -> dict[str, dict]:
        """Get all custom collection types from all plugins."""
        self.discover()
        types: dict[str, dict] = {}
        for plugin in self._plugins.values():
            if hasattr(plugin, "get_collection_types"):
                try:
                    plugin_types = plugin.get_collection_types()
                    if plugin_types:
                        self._merge_dict(types, plugin_types, plugin.name, "collection type")
                except Exception as e:
                    logger.warning("Plugin %s get_collection_types failed: %s", plugin.name, e)
        return types

    def get_all_field_schemas(self) -> dict[str, dict[str, dict]]:
        """Get all rich field schemas from all plugins.

        Returns:
            Dict mapping type name to dict of field definitions.
        """
        self.discover()
        schemas: dict[str, dict[str, dict]] = {}
        for plugin in self._plugins.values():
            if hasattr(plugin, "get_field_schemas"):
                try:
                    plugin_schemas = plugin.get_field_schemas()
                    if plugin_schemas:
                        for type_name, fields in plugin_schemas.items():
                            schemas.setdefault(type_name, {}).update(fields)
                except Exception as e:
                    logger.warning("Plugin %s get_field_schemas failed: %s", plugin.name, e)
        return schemas

    def get_all_validators(self) -> list[Callable]:
        """Get all validators from all plugins."""
        self.discover()
        validators = []
        for plugin in self._plugins.values():
            if hasattr(plugin, "get_validators"):
                try:
                    plugin_validators = plugin.get_validators()
                    if plugin_validators:
                        validators.extend(plugin_validators)
                except Exception as e:
                    logger.warning("Plugin %s get_validators failed: %s", plugin.name, e)
        return validators

    def _plugin_matches_kb_type(self, plugin: PyritePlugin, kb_type: str) -> bool:
        """Check if a plugin should be active for a given KB type.

        A plugin matches if:
        - kb_type is empty (no filtering)
        - plugin declares no kb_types (universal plugin)
        - kb_type is in the plugin's declared kb_types
        """
        if not kb_type:
            return True
        if not hasattr(plugin, "get_kb_types"):
            return True
        try:
            plugin_kb_types = plugin.get_kb_types()
            if not plugin_kb_types:
                return True
            return kb_type in plugin_kb_types
        except Exception:
            logger.warning("Failed to check KB type compatibility for plugin", exc_info=True)
            return True

    def get_validators_for_kb(self, kb_type: str = "") -> list[Callable]:
        """Get validators scoped to a specific KB type."""
        self.discover()
        validators = []
        for plugin in self._plugins.values():
            if not self._plugin_matches_kb_type(plugin, kb_type):
                continue
            if hasattr(plugin, "get_validators"):
                try:
                    plugin_validators = plugin.get_validators()
                    if plugin_validators:
                        validators.extend(plugin_validators)
                except Exception as e:
                    logger.warning("Plugin %s get_validators failed: %s", plugin.name, e)
        return validators

    def get_hooks_for_kb(self, kb_type: str = "") -> dict[str, list[Callable]]:
        """Get lifecycle hooks scoped to a specific KB type."""
        self.discover()
        hooks: dict[str, list[Callable]] = {}
        for plugin in self._plugins.values():
            if not self._plugin_matches_kb_type(plugin, kb_type):
                continue
            if hasattr(plugin, "get_hooks"):
                try:
                    plugin_hooks = plugin.get_hooks()
                    if plugin_hooks:
                        for hook_name, hook_list in plugin_hooks.items():
                            hooks.setdefault(hook_name, []).extend(hook_list)
                except Exception as e:
                    logger.warning("Plugin %s get_hooks failed: %s", plugin.name, e)
        return hooks

    def run_hooks_for_kb(
        self, hook_name: str, entry: Any, context: dict, kb_type: str = ""
    ) -> Any:
        """Run hooks for a given hook point, scoped to a KB type."""
        hooks = self.get_hooks_for_kb(kb_type).get(hook_name, [])
        for hook in hooks:
            try:
                result = hook(entry, context)
                if result is not None:
                    entry = result
            except Exception:
                if hook_name.startswith("before_"):
                    raise
                logger.warning("Hook %s failed for %s", hook_name, hook.__name__, exc_info=True)
        return entry


def get_registry() -> PluginRegistry:
    """Get the global plugin registry (lazy singleton)."""
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry
