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

from ..exceptions import PluginError
from .context import PluginContext
from .protocol import PyritePlugin

logger = logging.getLogger(__name__)

# Core relationship types (platform-level, not plugin-provided)
CORE_RELATIONSHIP_TYPES: dict[str, dict] = {
    "subtask_of": {
        "inverse": "has_subtask",
        "description": "Task is a subtask of another task",
    },
    "has_subtask": {
        "inverse": "subtask_of",
        "description": "Task has a subtask",
    },
    "produces": {
        "inverse": "produced_by",
        "description": "Task produces an entry as evidence",
    },
    "produced_by": {
        "inverse": "produces",
        "description": "Entry was produced by a task",
    },
}

# Core KB presets (platform-level)
CORE_KB_PRESETS: dict[str, dict] = {}  # Populated lazily to avoid circular import

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

    def discover(self, strict: bool = False) -> None:
        """Discover plugins via entry points.

        Args:
            strict: If True, raise PluginError on any plugin load failure
                instead of logging a warning and continuing. Useful for
                development, CI, and ``pyrite ci``.
        """
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
                        msg = f"Plugin {ep.name} has no 'name' attribute"
                        if strict:
                            raise PluginError(msg)
                        logger.warning("%s, skipping", msg)
                except PluginError:
                    raise
                except Exception as e:
                    if strict:
                        raise PluginError(f"Failed to load plugin {ep.name}: {e}") from e
                    logger.warning("Failed to load plugin %s: %s", ep.name, e)

        except PluginError:
            raise
        except Exception as e:
            if strict:
                raise PluginError(f"Plugin discovery failed: {e}") from e
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
    # Generic aggregation helpers
    # =========================================================================

    def _merge_dict(self, target: dict, source: dict, plugin_name: str, kind: str) -> None:
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

    def _aggregate_dict(self, method_name: str, kind: str) -> dict:
        """Aggregate dict results from all plugins, warning on key collisions."""
        self.discover()
        result: dict = {}
        for plugin in self._plugins.values():
            if hasattr(plugin, method_name):
                try:
                    items = getattr(plugin, method_name)()
                    if items:
                        self._merge_dict(result, items, plugin.name, kind)
                except Exception as e:
                    logger.error(
                        "Plugin %s %s failed: %s — %s data from this plugin is missing",
                        plugin.name, method_name, e, kind,
                    )
        return result

    def _aggregate_list(self, method_name: str) -> list:
        """Aggregate list results from all plugins."""
        self.discover()
        result: list = []
        for plugin in self._plugins.values():
            if hasattr(plugin, method_name):
                try:
                    items = getattr(plugin, method_name)()
                    if items:
                        result.extend(items)
                except Exception as e:
                    logger.error(
                        "Plugin %s %s failed: %s — data from this plugin is missing",
                        plugin.name, method_name, e,
                    )
        return result

    def _aggregate_dict_of_lists(self, method_name: str) -> dict[str, list]:
        """Aggregate dict-of-list results, extending lists per key."""
        self.discover()
        result: dict[str, list] = {}
        for plugin in self._plugins.values():
            if hasattr(plugin, method_name):
                try:
                    items = getattr(plugin, method_name)()
                    if items:
                        for key, lst in items.items():
                            result.setdefault(key, []).extend(lst)
                except Exception as e:
                    logger.error(
                        "Plugin %s %s failed: %s — data from this plugin is missing",
                        plugin.name, method_name, e,
                    )
        return result

    # =========================================================================
    # Public aggregation methods — collect capabilities from all plugins
    # =========================================================================

    def get_all_entry_types(self) -> dict[str, type]:
        """Get all custom entry types from all plugins."""
        return self._aggregate_dict("get_entry_types", "entry type")

    def get_all_kb_types(self) -> list[str]:
        """Get all custom KB types from all plugins."""
        return self._aggregate_list("get_kb_types")

    def get_all_cli_commands(self) -> list[tuple[str, Any]]:
        """Get all CLI commands from all plugins."""
        return self._aggregate_list("get_cli_commands")

    def get_all_mcp_tools(self, tier: str) -> dict[str, dict]:
        """Get all MCP tools for the given tier from all plugins."""
        self.discover()
        tools: dict[str, dict] = {}
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
        return self._aggregate_list("get_db_columns")

    def get_all_relationship_types(self) -> dict[str, dict]:
        """Get all relationship types: core + plugins."""
        result = dict(CORE_RELATIONSHIP_TYPES)
        plugin_types = self._aggregate_dict("get_relationship_types", "relationship type")
        result.update(plugin_types)
        return result

    def get_all_workflows(self) -> dict[str, dict]:
        """Get all workflow definitions from all plugins."""
        return self._aggregate_dict("get_workflows", "workflow")

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
        return self._aggregate_list("get_db_tables")

    def get_all_hooks(self) -> dict[str, list[Callable]]:
        """Get all lifecycle hooks from all plugins, merged by hook name."""
        return self._aggregate_dict_of_lists("get_hooks")

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
        """Get all KB presets: core + plugins."""
        # Lazy-load core preset to avoid circular import
        if not CORE_KB_PRESETS:
            from ..models.task import TASK_KB_PRESET

            CORE_KB_PRESETS["task"] = TASK_KB_PRESET
        result = dict(CORE_KB_PRESETS)
        plugin_presets = self._aggregate_dict("get_kb_presets", "KB preset")
        result.update(plugin_presets)
        return result

    def get_all_type_metadata(self) -> dict[str, dict]:
        """Get type metadata from all plugins (deep-merged per type)."""
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
        return self._aggregate_dict("get_collection_types", "collection type")

    def get_all_field_schemas(self) -> dict[str, dict[str, dict]]:
        """Get all rich field schemas from all plugins (merged per type)."""
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

    def get_all_rubric_checkers(self) -> dict[str, Any]:
        """Collect named rubric checkers from core + all plugins."""
        from ..services.rubric_checkers import NAMED_CHECKERS

        checkers: dict[str, Any] = dict(NAMED_CHECKERS)
        plugin_checkers = self._aggregate_dict("get_rubric_checkers", "rubric checker")
        checkers.update(plugin_checkers)
        return checkers

    def get_orient_supplements(self, kb_name: str, kb_type: str) -> dict[str, Any]:
        """Collect orient supplements from all plugins."""
        self.discover()
        result: dict[str, Any] = {}
        for plugin in self._plugins.values():
            if hasattr(plugin, "get_orient_supplement"):
                try:
                    supplement = plugin.get_orient_supplement(kb_name, kb_type)
                    if supplement:
                        result.update(supplement)
                except Exception as e:
                    logger.warning("Plugin %s get_orient_supplement failed: %s", plugin.name, e)
        return result

    def get_all_validators(self) -> list[Callable]:
        """Get all validators from all plugins."""
        return self._aggregate_list("get_validators")

    def get_all_migrations(self) -> list[dict]:
        """Get all schema migrations from all plugins."""
        return self._aggregate_list("get_migrations")

    def get_all_protocols(self) -> dict[str, type]:
        """Get all protocol mixin classes: core 5 + plugin-provided (ADR-0017)."""
        from ..models.protocols import PROTOCOL_REGISTRY

        protocols = dict(PROTOCOL_REGISTRY)
        self.discover()
        for plugin in self._plugins.values():
            if hasattr(plugin, "get_protocols"):
                try:
                    plugin_protocols = plugin.get_protocols()
                    if plugin_protocols:
                        self._merge_dict(protocols, plugin_protocols, plugin.name, "protocol")
                except Exception as e:
                    logger.warning("Plugin %s get_protocols failed: %s", plugin.name, e)
        return protocols

    # =========================================================================
    # KB-type-scoped queries
    # =========================================================================

    def _plugin_matches_kb_type(self, plugin: PyritePlugin, kb_type: str) -> bool:
        """Check if a plugin should be active for a given KB type."""
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

    def _aggregate_list_for_kb(self, method_name: str, kb_type: str) -> list:
        """Aggregate list results from plugins matching a KB type."""
        self.discover()
        result: list = []
        for plugin in self._plugins.values():
            if not self._plugin_matches_kb_type(plugin, kb_type):
                continue
            if hasattr(plugin, method_name):
                try:
                    items = getattr(plugin, method_name)()
                    if items:
                        result.extend(items)
                except Exception as e:
                    logger.warning("Plugin %s %s failed: %s", plugin.name, method_name, e)
        return result

    def _aggregate_dict_of_lists_for_kb(self, method_name: str, kb_type: str) -> dict[str, list]:
        """Aggregate dict-of-list results from plugins matching a KB type."""
        self.discover()
        result: dict[str, list] = {}
        for plugin in self._plugins.values():
            if not self._plugin_matches_kb_type(plugin, kb_type):
                continue
            if hasattr(plugin, method_name):
                try:
                    items = getattr(plugin, method_name)()
                    if items:
                        for key, lst in items.items():
                            result.setdefault(key, []).extend(lst)
                except Exception as e:
                    logger.warning("Plugin %s %s failed: %s", plugin.name, method_name, e)
        return result

    def get_validators_for_kb(self, kb_type: str = "") -> list[Callable]:
        """Get validators scoped to a specific KB type."""
        return self._aggregate_list_for_kb("get_validators", kb_type)

    def get_hooks_for_kb(self, kb_type: str = "") -> dict[str, list[Callable]]:
        """Get lifecycle hooks scoped to a specific KB type."""
        return self._aggregate_dict_of_lists_for_kb("get_hooks", kb_type)

    def run_hooks_for_kb(self, hook_name: str, entry: Any, context: dict, kb_type: str = "") -> Any:
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
