"""
Pyrite Plugin System

Plugins extend pyrite with custom entry types, CLI commands, MCP tools,
DB columns, validators, and relationship types.

Plugins are discovered via Python entry points:

    [project.entry-points."pyrite.plugins"]
    my_plugin = "my_package.plugin:MyPlugin"

See PyritePlugin protocol for the interface plugins must implement.
"""

from .protocol import PyritePlugin
from .registry import PluginRegistry, get_registry

__all__ = ["PyritePlugin", "PluginRegistry", "get_registry"]
