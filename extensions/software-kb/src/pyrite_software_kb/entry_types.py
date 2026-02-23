"""Software KB entry types."""

from dataclasses import dataclass, field
from typing import Any

from pyrite.models.base import parse_datetime, parse_links, parse_sources
from pyrite.models.core_types import DocumentEntry, NoteEntry
from pyrite.schema import Provenance, generate_entry_id

# Enum tuples
ADR_STATUSES = ("proposed", "accepted", "deprecated", "superseded")
DESIGN_DOC_STATUSES = ("draft", "review", "approved", "implemented", "obsolete")
STANDARD_CATEGORIES = ("coding", "testing", "api", "git", "documentation", "security", "deployment")
COMPONENT_KINDS = ("module", "service", "package", "library", "cli", "api", "database")
BACKLOG_KINDS = ("feature", "bug", "tech_debt", "improvement", "spike")
BACKLOG_STATUSES = ("proposed", "accepted", "in_progress", "done", "wont_do")
BACKLOG_PRIORITIES = ("critical", "high", "medium", "low")
BACKLOG_EFFORTS = ("XS", "S", "M", "L", "XL")
RUNBOOK_KINDS = ("howto", "troubleshooting", "setup", "operations", "onboarding")


# Helper for NoteEntry-based from_frontmatter
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
class ADREntry(NoteEntry):
    """Architecture Decision Record."""

    adr_number: int = 0
    status: str = "proposed"
    deciders: list[str] = field(default_factory=list)
    date: str = ""
    superseded_by: str = ""

    @property
    def entry_type(self) -> str:
        return "adr"

    def to_frontmatter(self) -> dict[str, Any]:
        meta = super().to_frontmatter()
        meta["type"] = "adr"
        if self.adr_number:
            meta["adr_number"] = self.adr_number
        if self.status != "proposed":
            meta["status"] = self.status
        if self.deciders:
            meta["deciders"] = self.deciders
        if self.date:
            meta["date"] = self.date
        if self.superseded_by:
            meta["superseded_by"] = self.superseded_by
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "ADREntry":
        kwargs = _note_base_kwargs(meta, body)
        return cls(
            **kwargs,
            adr_number=int(meta.get("adr_number", 0)),
            status=meta.get("status", "proposed"),
            deciders=meta.get("deciders", []) or [],
            date=meta.get("date", ""),
            superseded_by=meta.get("superseded_by", ""),
        )


@dataclass
class DesignDocEntry(DocumentEntry):
    """Design document or specification."""

    status: str = "draft"
    reviewers: list[str] = field(default_factory=list)

    @property
    def entry_type(self) -> str:
        return "design_doc"

    def to_frontmatter(self) -> dict[str, Any]:
        meta = super().to_frontmatter()
        meta["type"] = "design_doc"
        if self.status != "draft":
            meta["status"] = self.status
        if self.reviewers:
            meta["reviewers"] = self.reviewers
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "DesignDocEntry":
        prov_data = meta.get("provenance")
        provenance = Provenance.from_dict(prov_data) if prov_data else None
        entry_id = meta.get("id", "")
        if not entry_id:
            entry_id = generate_entry_id(meta.get("title", ""))
        return cls(
            id=entry_id,
            title=meta.get("title", ""),
            body=body,
            summary=meta.get("summary", ""),
            tags=meta.get("tags", []) or [],
            sources=parse_sources(meta.get("sources")),
            links=parse_links(meta.get("links")),
            provenance=provenance,
            metadata=meta.get("metadata", {}),
            created_at=parse_datetime(meta.get("created_at")),
            updated_at=parse_datetime(meta.get("updated_at")),
            date=meta.get("date", ""),
            author=meta.get("author", ""),
            document_type=meta.get("document_type", ""),
            url=meta.get("url", ""),
            importance=int(meta.get("importance", 5)),
            status=meta.get("status", "draft"),
            reviewers=meta.get("reviewers", []) or [],
        )


@dataclass
class StandardEntry(NoteEntry):
    """Coding standard or convention."""

    category: str = ""
    enforced: bool = False

    @property
    def entry_type(self) -> str:
        return "standard"

    def to_frontmatter(self) -> dict[str, Any]:
        meta = super().to_frontmatter()
        meta["type"] = "standard"
        if self.category:
            meta["category"] = self.category
        if self.enforced:
            meta["enforced"] = self.enforced
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "StandardEntry":
        kwargs = _note_base_kwargs(meta, body)
        return cls(
            **kwargs,
            category=meta.get("category", ""),
            enforced=bool(meta.get("enforced", False)),
        )


@dataclass
class ComponentEntry(NoteEntry):
    """Module or service documentation."""

    kind: str = ""
    path: str = ""
    owner: str = ""
    dependencies: list[str] = field(default_factory=list)

    @property
    def entry_type(self) -> str:
        return "component"

    def to_frontmatter(self) -> dict[str, Any]:
        meta = super().to_frontmatter()
        meta["type"] = "component"
        if self.kind:
            meta["kind"] = self.kind
        if self.path:
            meta["path"] = self.path
        if self.owner:
            meta["owner"] = self.owner
        if self.dependencies:
            meta["dependencies"] = self.dependencies
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "ComponentEntry":
        kwargs = _note_base_kwargs(meta, body)
        return cls(
            **kwargs,
            kind=meta.get("kind", ""),
            path=meta.get("path", ""),
            owner=meta.get("owner", ""),
            dependencies=meta.get("dependencies", []) or [],
        )


@dataclass
class BacklogItemEntry(NoteEntry):
    """Feature, bug, or tech debt tracking item."""

    kind: str = ""
    status: str = "proposed"
    priority: str = "medium"
    assignee: str = ""
    effort: str = ""

    @property
    def entry_type(self) -> str:
        return "backlog_item"

    def to_frontmatter(self) -> dict[str, Any]:
        meta = super().to_frontmatter()
        meta["type"] = "backlog_item"
        if self.kind:
            meta["kind"] = self.kind
        if self.status != "proposed":
            meta["status"] = self.status
        if self.priority != "medium":
            meta["priority"] = self.priority
        if self.assignee:
            meta["assignee"] = self.assignee
        if self.effort:
            meta["effort"] = self.effort
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "BacklogItemEntry":
        kwargs = _note_base_kwargs(meta, body)
        return cls(
            **kwargs,
            kind=meta.get("kind", ""),
            status=meta.get("status", "proposed"),
            priority=meta.get("priority", "medium"),
            assignee=meta.get("assignee", ""),
            effort=meta.get("effort", ""),
        )


@dataclass
class RunbookEntry(NoteEntry):
    """How-to guide or operational procedure."""

    runbook_kind: str = ""
    audience: str = ""

    @property
    def entry_type(self) -> str:
        return "runbook"

    def to_frontmatter(self) -> dict[str, Any]:
        meta = super().to_frontmatter()
        meta["type"] = "runbook"
        if self.runbook_kind:
            meta["runbook_kind"] = self.runbook_kind
        if self.audience:
            meta["audience"] = self.audience
        return meta

    @classmethod
    def from_frontmatter(cls, meta: dict[str, Any], body: str) -> "RunbookEntry":
        kwargs = _note_base_kwargs(meta, body)
        return cls(
            **kwargs,
            runbook_kind=meta.get("runbook_kind", ""),
            audience=meta.get("audience", ""),
        )
