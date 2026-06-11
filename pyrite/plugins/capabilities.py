"""Plugin capability declarations (Tier A r1500 / ADR-0002 addendum).

Plugins declare which of the 5 plugin-protocol subsystems they extend
via a ``capabilities: ClassVar[set[Capability]]`` class attribute. The
registry consults the declared set before dispatching to each method,
skipping methods whose capability the plugin did not claim.

Locked design at commit 0b9b547 (Option B). The 5 members mirror the
5-subsystem split documented in r1500 — an eventual move to Option A
(splitting the Protocol into 5 capability protocols) is mechanical:
each Capability becomes its own Protocol with the same name.
"""

from __future__ import annotations

from enum import StrEnum


class Capability(StrEnum):
    """The 5 plugin-protocol subsystems a plugin can opt into.

    SCHEMA   — entry types, type metadata, collection types, field
               schemas, structural protocols.
    STORAGE  — db columns, db tables, migrations, validators, hooks.
    SURFACE  — CLI commands, MCP tools, KB presets, KB types.
    DOMAIN   — relationship types, workflows, rubric checkers.
    CONTEXT  — set_context, get_orient_supplement (runtime hooks).
    """

    SCHEMA = "schema"
    STORAGE = "storage"
    SURFACE = "surface"
    DOMAIN = "domain"
    CONTEXT = "context"
