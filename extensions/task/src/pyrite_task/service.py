"""Task service — operative task operations wrapping KBService."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from pyrite.config import PyriteConfig
from pyrite.storage.database import PyriteDB

logger = logging.getLogger(__name__)


class TaskService:
    """Service for task-specific operations.

    Wraps KBService for standard CRUD and adds task-specific
    atomic operations: claim, decompose, checkpoint, rollup.
    """

    def __init__(self, config: PyriteConfig, db: PyriteDB):
        self.config = config
        self.db = db
        self._kb_svc = None

    @property
    def kb_svc(self):
        if self._kb_svc is None:
            from pyrite.services.kb_service import KBService

            self._kb_svc = KBService(self.config, self.db)
        return self._kb_svc

    def _query(self, sql: str, params: dict | None = None) -> list[dict]:
        """Execute SQL through session connection for consistency with ORM writes."""
        return self.db.execute_sql(sql, params)

    def create_task(
        self,
        kb_name: str,
        title: str,
        body: str = "",
        parent_task: str = "",
        priority: int = 5,
        assignee: str = "",
        dependencies: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new task entry.

        Returns:
            Dict with created=True and entry details.
        """
        from pyrite.schema import generate_entry_id

        entry_id = generate_entry_id(title)
        kwargs: dict[str, Any] = {"status": "open", "priority": priority}
        if parent_task:
            kwargs["parent_task"] = parent_task
        if assignee:
            kwargs["assignee"] = assignee
        if dependencies:
            kwargs["dependencies"] = dependencies

        entry = self.kb_svc.create_entry(
            kb_name=kb_name,
            entry_id=entry_id,
            title=title,
            entry_type="task",
            body=body,
            **kwargs,
        )
        return {
            "created": True,
            "entry_id": entry.id,
            "title": entry.title,
            "status": getattr(entry, "status", "open"),
            "priority": getattr(entry, "priority", 5),
            "parent_task": getattr(entry, "parent_task", ""),
            "assignee": getattr(entry, "assignee", ""),
            "kb_name": kb_name,
        }

    def update_task(self, task_id: str, kb_name: str, **updates) -> dict[str, Any]:
        """Update task fields.

        Returns:
            Dict with updated=True and entry details.
        """
        entry = self.kb_svc.update_entry(task_id, kb_name, **updates)
        return {
            "updated": True,
            "task_id": entry.id,
            "title": entry.title,
            "status": getattr(entry, "status", "open"),
            "priority": getattr(entry, "priority", 5),
            "assignee": getattr(entry, "assignee", ""),
            "updates": updates,
        }

    def get_task(self, task_id: str, kb_name: str | None = None) -> dict[str, Any] | None:
        """Get task details from the index."""
        return self.kb_svc.get_entry(task_id, kb_name)

    def list_tasks(
        self,
        kb_name: str | None = None,
        status: str | None = None,
        assignee: str | None = None,
        parent: str | None = None,
    ) -> list[dict[str, Any]]:
        """List tasks with optional filters.

        Queries the index via session connection for consistency with ORM writes.
        """
        query = "SELECT id, title, kb_name, metadata FROM entry WHERE entry_type = 'task'"
        params: dict[str, str] = {}
        if kb_name:
            query += " AND kb_name = :kb_name"
            params["kb_name"] = kb_name
        if status:
            if status == "open":
                # to_frontmatter omits status when it's "open" (default),
                # so match both NULL and explicit 'open'
                query += " AND (json_extract(metadata, '$.status') = 'open' OR json_extract(metadata, '$.status') IS NULL)"
            else:
                query += " AND json_extract(metadata, '$.status') = :status"
                params["status"] = status
        if assignee:
            query += " AND json_extract(metadata, '$.assignee') = :assignee"
            params["assignee"] = assignee
        if parent:
            query += " AND json_extract(metadata, '$.parent_task') = :parent"
            params["parent"] = parent
        query += " ORDER BY created_at DESC"

        rows = self._query(query, params)
        tasks = []
        for row in rows:
            meta = _parse_metadata(row.get("metadata"))
            tasks.append({
                "id": row["id"],
                "title": row["title"],
                "status": meta.get("status", "open"),
                "assignee": meta.get("assignee", ""),
                "priority": meta.get("priority", 5),
                "parent_task": meta.get("parent_task", ""),
                "kb_name": row["kb_name"],
            })
        return tasks

    def claim_task(self, task_id: str, kb_name: str, assignee: str) -> dict[str, Any]:
        """Atomically claim an open task.

        Uses CAS (compare-and-swap) on the index to ensure only one
        agent can claim a task. On success, updates the markdown file.

        Returns:
            Dict with claimed=True on success, or error details.
        """
        # Use session connection for CAS to be consistent with ORM writes
        from sqlalchemy import text

        session = self.db.session

        # CAS: only update if status is currently 'open'
        # to_frontmatter omits status when it's "open" (default),
        # so metadata may have status=NULL or status='open'
        result = session.execute(
            text("""UPDATE entry
               SET metadata = json_set(
                   COALESCE(metadata, '{}'),
                   '$.status', 'claimed',
                   '$.assignee', :assignee
               )
               WHERE id = :task_id AND kb_name = :kb_name
               AND (json_extract(metadata, '$.status') = 'open'
                    OR json_extract(metadata, '$.status') IS NULL)"""),
            {"assignee": assignee, "task_id": task_id, "kb_name": kb_name},
        )
        session.commit()

        if result.rowcount == 0:
            # Check why — not found or wrong status
            rows = self._query(
                "SELECT metadata FROM entry WHERE id = :task_id AND kb_name = :kb_name",
                {"task_id": task_id, "kb_name": kb_name},
            )
            if not rows:
                return {"claimed": False, "error": f"Task '{task_id}' not found in KB '{kb_name}'"}
            meta = _parse_metadata(rows[0].get("metadata"))
            current = meta.get("status", "open")
            return {
                "claimed": False,
                "error": f"Task '{task_id}' is '{current}', not 'open'",
                "current_status": current,
            }

        # Update the markdown file to match
        try:
            self.kb_svc.update_entry(task_id, kb_name, status="claimed", assignee=assignee)
        except Exception as e:
            # Rollback index CAS on file error
            logger.warning("File update failed for claim on %s, rolling back: %s", task_id, e)
            session.execute(
                text("""UPDATE entry
                   SET metadata = json_remove(
                       json_set(metadata, '$.status', 'open'),
                       '$.assignee'
                   )
                   WHERE id = :task_id AND kb_name = :kb_name"""),
                {"task_id": task_id, "kb_name": kb_name},
            )
            session.commit()
            return {"claimed": False, "error": f"File update failed: {e}"}

        return {
            "claimed": True,
            "task_id": task_id,
            "assignee": assignee,
            "status": "claimed",
        }

    def decompose_task(
        self, parent_id: str, kb_name: str, children: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Decompose a parent task into child tasks.

        Args:
            parent_id: Parent task entry ID
            kb_name: KB name
            children: List of child specs, each with at least 'title'

        Returns:
            List of per-child result dicts.
        """
        # Verify parent exists
        parent = self.kb_svc.get_entry(parent_id, kb_name)
        if not parent:
            raise ValueError(f"Parent task '{parent_id}' not found in KB '{kb_name}'")

        # Build entry specs for bulk creation
        specs = []
        for child in children:
            spec = {
                "entry_type": "task",
                "title": child["title"],
                "body": child.get("body", ""),
                "parent_task": parent_id,
                "status": "open",
                "priority": child.get("priority", 5),
            }
            if child.get("assignee"):
                spec["assignee"] = child["assignee"]
            specs.append(spec)

        return self.kb_svc.bulk_create_entries(kb_name, specs)

    def checkpoint_task(
        self,
        task_id: str,
        kb_name: str,
        message: str,
        confidence: float = 0.0,
        partial_evidence: list[str] | None = None,
    ) -> dict[str, Any]:
        """Append a timestamped checkpoint to a task.

        Checkpoints are appended to the task body as markdown sections
        and the agent_context is updated with the latest info.

        Returns:
            Dict with checkpoint details.
        """
        from pyrite.storage.repository import KBRepository

        kb_config = self.config.get_kb(kb_name)
        if not kb_config:
            raise ValueError(f"KB not found: {kb_name}")

        repo = KBRepository(kb_config)
        entry = repo.load(task_id)
        if not entry:
            raise ValueError(f"Task '{task_id}' not found in KB '{kb_name}'")

        timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Build checkpoint section
        section = f"\n\n## Checkpoint {timestamp}\n\n{message}"
        if confidence > 0:
            section += f"\n\n**Confidence**: {int(confidence * 100)}%"
        if partial_evidence:
            evidence_str = ", ".join(f"`{e}`" for e in partial_evidence)
            section += f"\n\n**Evidence**: {evidence_str}"

        new_body = (entry.body or "") + section

        # Update agent_context
        agent_ctx = dict(getattr(entry, "agent_context", {}) or {})
        agent_ctx["last_checkpoint"] = timestamp
        agent_ctx["last_message"] = message
        if confidence > 0:
            agent_ctx["confidence"] = confidence
        if partial_evidence:
            existing = agent_ctx.get("evidence", [])
            agent_ctx["evidence"] = list(set(existing + partial_evidence))

        updates: dict[str, Any] = {"body": new_body, "agent_context": agent_ctx}
        if partial_evidence:
            existing_evidence = list(getattr(entry, "evidence", []) or [])
            merged = list(set(existing_evidence + partial_evidence))
            updates["evidence"] = merged

        self.kb_svc.update_entry(task_id, kb_name, **updates)

        return {
            "checkpointed": True,
            "task_id": task_id,
            "timestamp": timestamp,
            "message": message,
            "confidence": confidence,
            "evidence": partial_evidence or [],
        }

    def rollup_parent(self, parent_id: str, kb_name: str) -> dict[str, Any] | None:
        """Auto-complete a parent task if all children are done.

        Returns:
            Dict with rollup details if parent was completed, None otherwise.
        """
        # Query through session connection for consistency with ORM writes
        rows = self._query(
            """SELECT id, json_extract(metadata, '$.status') as status
               FROM entry
               WHERE kb_name = :kb_name
               AND json_extract(metadata, '$.parent_task') = :parent_id""",
            {"kb_name": kb_name, "parent_id": parent_id},
        )

        if not rows:
            return None

        # Check if all children are done
        all_done = all(row["status"] == "done" for row in rows)
        if not all_done:
            return None

        # Check parent status — skip if already done/failed
        parent_rows = self._query(
            """SELECT json_extract(metadata, '$.status') as status
               FROM entry WHERE id = :parent_id AND kb_name = :kb_name""",
            {"parent_id": parent_id, "kb_name": kb_name},
        )
        if not parent_rows:
            return None
        parent_status = parent_rows[0]["status"]
        if parent_status in ("done", "failed"):
            return None

        # Complete the parent
        entry = self.kb_svc.update_entry(parent_id, kb_name, status="done")

        result = {
            "rolled_up": True,
            "parent_id": parent_id,
            "children_count": len(rows),
        }

        # Cascade: check if the parent itself has a parent that should roll up
        grandparent_id = getattr(entry, "parent_task", "")
        if grandparent_id:
            try:
                self.rollup_parent(grandparent_id, kb_name)
            except Exception as e:
                logger.warning("Cascading rollup failed for %s: %s", grandparent_id, e)

        return result


def _parse_metadata(raw) -> dict[str, Any]:
    """Parse metadata JSON from a DB row."""
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
