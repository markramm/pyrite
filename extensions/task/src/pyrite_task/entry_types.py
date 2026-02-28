"""Task entry type."""

from dataclasses import dataclass, field
from typing import Any

from pyrite.models.base import parse_datetime, parse_links, parse_sources
from pyrite.models.core_types import NoteEntry
from pyrite.schema import Provenance, generate_entry_id

TASK_STATUSES = ("open", "claimed", "in_progress", "blocked", "review", "done", "failed")
TASK_PRIORITIES = tuple(range(1, 11))  # 1-10


def _note_base_kwargs(meta: dict[str, Any], body: str) -> dict[str, Any]:
    prov_data = meta.get("provenance")
    provenance = Provenance.from_dict(prov_data) if prov_data else None
    entry_id = meta.get("id", "")
    if not entry_id:
        entry_id = generate_entry_id(meta.get("title", ""))
    return {
        "id": entry_id,
        "title": meta.get("title", ""),
        "body": body,
        "summary": meta.get("summary", ""),
        "tags": meta.get("tags", []) or [],
        "sources": parse_sources(meta.get("sources")),
        "links": parse_links(meta.get("links")),
        "provenance": provenance,
        "metadata": meta.get("metadata", {}),
        "created_at": parse_datetime(meta.get("created_at")),
        "updated_at": parse_datetime(meta.get("updated_at")),
    }


@dataclass
class TaskEntry(NoteEntry):
    """Agent-oriented task with workflow state machine."""

    status: str = "open"
    assignee: str = ""
    parent_task: str = ""
    dependencies: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    priority: int = 5
    due_date: str = ""
    agent_context: dict[str, Any] = field(default_factory=dict)

    @property
    def entry_type(self) -> str:
        return "task"

    def to_frontmatter(self) -> dict[str, Any]:
        meta = super().to_frontmatter()
        meta["type"] = "task"
        if self.status != "open":
            meta["status"] = self.status
        if self.assignee:
            meta["assignee"] = self.assignee
        if self.parent_task:
            meta["parent_task"] = self.parent_task
        if self.dependencies:
            meta["dependencies"] = self.dependencies
        if self.evidence:
            meta["evidence"] = self.evidence
        if self.priority != 5:
            meta["priority"] = self.priority
        if self.due_date:
            meta["due_date"] = self.due_date
        if self.agent_context:
            meta["agent_context"] = self.agent_context
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "TaskEntry":
        kwargs = _note_base_kwargs(meta, body)
        return cls(
            **kwargs,
            status=meta.get("status", "open"),
            assignee=meta.get("assignee", ""),
            parent_task=meta.get("parent_task", ""),
            dependencies=meta.get("dependencies", []) or [],
            evidence=meta.get("evidence", []) or [],
            priority=meta.get("priority", 5),
            due_date=meta.get("due_date", ""),
            agent_context=meta.get("agent_context", {}) or {},
        )
