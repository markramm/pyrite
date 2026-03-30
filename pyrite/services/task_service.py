"""Task service — operative task operations wrapping KBService."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from ..config import PyriteConfig
from ..storage.database import PyriteDB

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
            from .kb_service import KBService

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
        parent: str = "",
        priority: int = 5,
        assignee: str = "",
        dependencies: list[str] | None = None,
        tags: list[str] | None = None,
        *,
        # Legacy alias
        parent_task: str = "",
    ) -> dict[str, Any]:
        """Create a new task entry.

        Returns:
            Dict with created=True and entry details.
        """
        from ..schema import generate_entry_id

        # Support legacy parent_task parameter
        parent = parent or parent_task

        entry_id = generate_entry_id(title)
        kwargs: dict[str, Any] = {"status": "open", "priority": priority}
        if parent:
            kwargs["parent"] = parent
        if assignee:
            kwargs["assignee"] = assignee
        if dependencies:
            kwargs["dependencies"] = dependencies
        if tags:
            kwargs["tags"] = tags

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
            "parent": getattr(entry, "parent", ""),
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
        """List tasks with optional filters."""
        query = "SELECT id, title, kb_name, status, assignee, metadata FROM entry WHERE entry_type = 'task'"
        params: dict[str, str] = {}
        if kb_name:
            query += " AND kb_name = :kb_name"
            params["kb_name"] = kb_name
        if status:
            if status == "open":
                query += " AND (status = 'open' OR status IS NULL)"
            else:
                query += " AND status = :status"
                params["status"] = status
        if assignee:
            query += " AND assignee = :assignee"
            params["assignee"] = assignee
        if parent:
            query += " AND json_extract(metadata, '$.parent') = :parent"
            params["parent"] = parent
        query += " ORDER BY created_at DESC"

        rows = self._query(query, params)
        tasks = []
        for row in rows:
            meta = _parse_metadata(row.get("metadata"))
            tasks.append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "status": meta.get("status", "open"),
                    "assignee": meta.get("assignee", ""),
                    "priority": meta.get("priority", 5),
                    "parent": meta.get("parent", ""),
                    "kb_name": row["kb_name"],
                }
            )
        return tasks

    def claim_task(self, task_id: str, kb_name: str, assignee: str) -> dict[str, Any]:
        """Atomically claim an open task. Delegates to KBService.claim_entry()."""
        return self.kb_svc.claim_entry(task_id, kb_name, assignee)

    def decompose_task(
        self, parent_id: str, kb_name: str, children: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Decompose a parent task into child tasks."""
        parent = self.kb_svc.get_entry(parent_id, kb_name)
        if not parent:
            raise ValueError(f"Parent task '{parent_id}' not found in KB '{kb_name}'")

        specs = []
        for child in children:
            spec = {
                "entry_type": "task",
                "title": child["title"],
                "body": child.get("body", ""),
                "parent": parent_id,
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
        """Append a timestamped checkpoint to a task."""
        from ..storage.repository import KBRepository

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
        """Auto-complete a parent task if all children are done."""
        rows = self._query(
            """SELECT id, status
               FROM entry
               WHERE kb_name = :kb_name
               AND json_extract(metadata, '$.parent') = :parent_id""",
            {"kb_name": kb_name, "parent_id": parent_id},
        )

        if not rows:
            return None

        all_done = all(row["status"] == "done" for row in rows)
        if not all_done:
            return None

        parent_rows = self._query(
            """SELECT status
               FROM entry WHERE id = :parent_id AND kb_name = :kb_name""",
            {"parent_id": parent_id, "kb_name": kb_name},
        )
        if not parent_rows:
            return None
        parent_status = parent_rows[0]["status"]
        if parent_status in ("done", "failed"):
            return None

        entry = self.kb_svc.update_entry(parent_id, kb_name, status="done")

        result = {
            "rolled_up": True,
            "parent_id": parent_id,
            "children_count": len(rows),
        }

        # Cascade: check if the parent itself has a parent
        grandparent_id = getattr(entry, "parent", "")
        if grandparent_id:
            try:
                self.rollup_parent(grandparent_id, kb_name)
            except Exception as e:
                logger.warning("Cascading rollup failed for %s: %s", grandparent_id, e)

        return result


    def unblock_dependents(self, task_id: str, kb_name: str) -> list[dict[str, Any]]:
        """When a task completes, auto-unblock tasks that depended on it.

        Finds tasks with status='blocked' whose dependencies all resolve to done,
        and transitions them to 'open'.
        """
        # Find tasks that have this task as a dependency
        rows = self._query(
            """SELECT id, metadata FROM entry
               WHERE kb_name = :kb_name AND entry_type = 'task'
               AND status = 'blocked'""",
            {"kb_name": kb_name},
        )

        unblocked = []
        for row in rows:
            meta = _parse_metadata(row.get("metadata"))
            deps = meta.get("dependencies", [])
            if not deps or task_id not in deps:
                continue

            # Check if ALL dependencies are now done
            all_done = True
            for dep_id in deps:
                dep_rows = self._query(
                    "SELECT status FROM entry WHERE id = :id AND kb_name = :kb_name",
                    {"id": dep_id, "kb_name": kb_name},
                )
                if not dep_rows or dep_rows[0].get("status") != "done":
                    all_done = False
                    break

            if all_done:
                self.kb_svc.update_entry(row["id"], kb_name, status="in_progress")
                unblocked.append({"id": row["id"], "title": row.get("title", "")})

        return unblocked

    def aggregate_evidence_to_parent(self, task_id: str, kb_name: str) -> dict[str, Any] | None:
        """Aggregate evidence from a child task up to its parent.

        When a child task accumulates evidence links, copy them to the parent
        so querying the parent shows all evidence from its subtree.
        """
        task = self.get_task(task_id, kb_name)
        if not task:
            return None

        meta = _parse_metadata(task.get("metadata") or {})
        parent_id = meta.get("parent") or task.get("parent", "")
        if not parent_id:
            return None

        child_evidence = meta.get("evidence", []) or task.get("evidence", []) or []
        if not child_evidence:
            return None

        parent = self.get_task(parent_id, kb_name)
        if not parent:
            return None

        parent_meta = _parse_metadata(parent.get("metadata") or {})
        parent_evidence = parent_meta.get("evidence", []) or parent.get("evidence", []) or []

        # Merge without duplicates
        new_evidence = list(set(parent_evidence) | set(child_evidence))
        if len(new_evidence) == len(parent_evidence):
            return None  # Nothing new to add

        self.kb_svc.update_entry(parent_id, kb_name, evidence=new_evidence)
        added = len(new_evidence) - len(parent_evidence)
        return {"parent_id": parent_id, "evidence_added": added, "total_evidence": len(new_evidence)}

    def list_entries_needing_qa(self, kb_name: str | None = None) -> list[dict[str, Any]]:
        """Find entries that have open/unclaimed QA validation tasks.

        Returns entries (not tasks) that need QA review.
        """
        query = """SELECT DISTINCT e.id, e.title, e.kb_name, e.entry_type
                   FROM entry t
                   JOIN entry e ON json_extract(t.metadata, '$.target_entry') = e.id
                                AND t.kb_name = e.kb_name
                   WHERE t.entry_type = 'task'
                   AND t.status IN ('open', NULL)
                   AND (t.assignee IS NULL OR t.assignee = '')
                   AND json_extract(t.metadata, '$.task_type') = 'qa_validation'"""
        params: dict[str, str] = {}
        if kb_name:
            query += " AND t.kb_name = :kb_name"
            params["kb_name"] = kb_name
        query += " ORDER BY e.updated_at DESC"

        return self._query(query, params)

    def link_qa_assessment(
        self, task_id: str, assessment_id: str, kb_name: str
    ) -> dict[str, Any]:
        """Link a QA assessment entry as evidence on a QA task.

        When a QA agent creates an assessment entry, this links it
        to the corresponding task for traceability.
        """
        task = self.get_task(task_id, kb_name)
        if not task:
            return {"linked": False, "error": "Task not found"}

        meta = _parse_metadata(task.get("metadata") or {})
        evidence = meta.get("evidence", []) or task.get("evidence", []) or []

        if assessment_id not in evidence:
            evidence.append(assessment_id)
            self.kb_svc.update_entry(task_id, kb_name, evidence=evidence)

        return {
            "linked": True,
            "task_id": task_id,
            "assessment_id": assessment_id,
            "total_evidence": len(evidence),
        }

    # ── DAG traversal methods ──────────────────────────────────────

    def get_subtree(self, task_id: str, kb_name: str) -> list[dict[str, Any]]:
        """Get all descendants of a task (children, grandchildren, etc.)."""
        result: list[dict[str, Any]] = []
        visited: set[str] = set()

        def _collect(parent_id: str) -> None:
            children = self._query(
                """SELECT id, title, status, entry_type,
                          json_extract(metadata, '$.parent') as parent,
                          json_extract(metadata, '$.assignee') as assignee,
                          importance as priority
                   FROM entry
                   WHERE kb_name = :kb_name AND entry_type = 'task'
                   AND json_extract(metadata, '$.parent') = :parent_id""",
                {"kb_name": kb_name, "parent_id": parent_id},
            )
            for child in children:
                cid = child["id"]
                if cid in visited:
                    continue
                visited.add(cid)
                result.append(child)
                _collect(cid)

        _collect(task_id)
        return result

    def get_ancestors(self, task_id: str, kb_name: str) -> list[dict[str, Any]]:
        """Get parent chain from task to root. Returns [parent, grandparent, ...]."""
        result: list[dict[str, Any]] = []
        visited: set[str] = set()
        current_id = task_id

        while True:
            if current_id in visited:
                break
            visited.add(current_id)

            task = self.get_task(current_id, kb_name)
            if not task:
                break

            meta = _parse_metadata(task.get("metadata") or {})
            parent_id = meta.get("parent") or task.get("parent", "")
            if not parent_id:
                break

            parent = self.get_task(parent_id, kb_name)
            if not parent:
                break

            result.append({
                "id": parent["id"],
                "title": parent.get("title", ""),
                "status": parent.get("status", ""),
                "entry_type": parent.get("entry_type", "task"),
            })
            current_id = parent_id

        return result

    def get_blocked_by(self, task_id: str, kb_name: str) -> list[dict[str, Any]]:
        """Get transitive dependency chain — all tasks blocking this one."""
        result: list[dict[str, Any]] = []
        visited: set[str] = set()

        def _collect_deps(tid: str) -> None:
            if tid in visited:
                return
            visited.add(tid)

            task = self.get_task(tid, kb_name)
            if not task:
                return

            meta = _parse_metadata(task.get("metadata") or {})
            deps = meta.get("dependencies", []) or task.get("dependencies", []) or []

            for dep_id in deps:
                if dep_id in visited:
                    continue
                dep = self.get_task(dep_id, kb_name)
                if dep:
                    result.append({
                        "id": dep["id"],
                        "title": dep.get("title", ""),
                        "status": dep.get("status", ""),
                        "entry_type": dep.get("entry_type", "task"),
                    })
                    _collect_deps(dep_id)

        _collect_deps(task_id)
        return result

    def critical_path(self, task_id: str, kb_name: str) -> list[dict[str, Any]]:
        """Find the longest chain of unresolved dependencies (critical path).

        Returns the ordered list of tasks in the longest blocking chain.
        Handles cycles gracefully via visited set.
        """
        visited: set[str] = set()

        def _longest_chain(tid: str) -> list[dict[str, Any]]:
            if tid in visited:
                return []
            visited.add(tid)

            task = self.get_task(tid, kb_name)
            if not task:
                return []

            meta = _parse_metadata(task.get("metadata") or {})
            deps = meta.get("dependencies", []) or task.get("dependencies", []) or []

            if not deps:
                return []

            best_chain: list[dict[str, Any]] = []
            for dep_id in deps:
                dep = self.get_task(dep_id, kb_name)
                if not dep:
                    continue
                sub_chain = _longest_chain(dep_id)
                candidate = [{
                    "id": dep["id"],
                    "title": dep.get("title", ""),
                    "status": dep.get("status", ""),
                    "entry_type": dep.get("entry_type", "task"),
                }] + sub_chain
                if len(candidate) > len(best_chain):
                    best_chain = candidate

            return best_chain

        return _longest_chain(task_id)


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
