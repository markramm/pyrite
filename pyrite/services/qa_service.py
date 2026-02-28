"""
QA Service — structural validation for knowledge bases.

Validates KB integrity without LLM involvement:
- Bulk SQL checks (missing titles, empty bodies, broken links, orphans)
- Per-entry schema validation via KBSchema.validate_entry()
- Aggregate health metrics
"""

from __future__ import annotations

import logging
from typing import Any

from ..config import PyriteConfig
from ..schema import KBSchema, validate_date, validate_importance
from ..storage.database import PyriteDB

logger = logging.getLogger(__name__)


class QAService:
    """Structural quality assurance for knowledge bases."""

    def __init__(self, config: PyriteConfig, db: PyriteDB):
        self.config = config
        self.db = db

    # =========================================================================
    # Public API
    # =========================================================================

    def validate_entry(self, entry_id: str, kb_name: str) -> dict[str, Any]:
        """Validate a single entry. Returns {entry_id, kb_name, issues: [...]}."""
        issues: list[dict[str, Any]] = []

        row = self.db._raw_conn.execute(
            "SELECT id, kb_name, entry_type, title, date, importance, body, status, metadata "
            "FROM entry WHERE id = ? AND kb_name = ?",
            (entry_id, kb_name),
        ).fetchone()

        if not row:
            return {
                "entry_id": entry_id,
                "kb_name": kb_name,
                "issues": [
                    {
                        "entry_id": entry_id,
                        "kb_name": kb_name,
                        "rule": "entry_not_found",
                        "severity": "error",
                        "field": "id",
                        "message": f"Entry '{entry_id}' not found in KB '{kb_name}'",
                    }
                ],
            }

        entry = dict(row)
        self._check_entry_fields(entry, issues)
        self._check_entry_links(entry_id, kb_name, issues)
        self._check_schema_validation(entry, issues)

        return {"entry_id": entry_id, "kb_name": kb_name, "issues": issues}

    def validate_kb(self, kb_name: str) -> dict[str, Any]:
        """Validate all entries in a KB. Returns {kb_name, total, checked, issues: [...]}."""
        issues: list[dict[str, Any]] = []

        # Count entries
        total = self.db._raw_conn.execute(
            "SELECT COUNT(*) FROM entry WHERE kb_name = ?", (kb_name,)
        ).fetchone()[0]

        # Bulk SQL pass — fast structural checks
        self._check_missing_titles(issues, kb_name)
        self._check_empty_bodies(issues, kb_name)
        self._check_events_missing_dates(issues, kb_name)
        self._check_invalid_dates(issues, kb_name)
        self._check_importance_range(issues, kb_name)
        self._check_broken_links(issues, kb_name)
        self._check_orphans(issues, kb_name)

        # Per-entry schema pass (only if kb.yaml exists)
        self._check_schema_all(issues, kb_name)

        return {
            "kb_name": kb_name,
            "total": total,
            "checked": total,
            "issues": issues,
        }

    def validate_all(self) -> dict[str, Any]:
        """Validate all KBs. Returns {kbs: [{kb_name, total, checked, issues}]}."""
        kbs = []
        for kb in self.config.knowledge_bases:
            result = self.validate_kb(kb.name)
            kbs.append(result)
        return {"kbs": kbs}

    def get_status(self, kb_name: str | None = None) -> dict[str, Any]:
        """Get QA status dashboard."""
        if kb_name:
            result = self.validate_kb(kb_name)
            issues = result["issues"]
            total_entries = result["total"]
        else:
            all_result = self.validate_all()
            issues = []
            total_entries = 0
            for kb in all_result["kbs"]:
                issues.extend(kb["issues"])
                total_entries += kb["total"]

        # Aggregate
        issues_by_severity: dict[str, int] = {}
        issues_by_rule: dict[str, int] = {}
        for issue in issues:
            sev = issue.get("severity", "info")
            rule = issue.get("rule", "unknown")
            issues_by_severity[sev] = issues_by_severity.get(sev, 0) + 1
            issues_by_rule[rule] = issues_by_rule.get(rule, 0) + 1

        return {
            "total_entries": total_entries,
            "total_issues": len(issues),
            "issues_by_severity": issues_by_severity,
            "issues_by_rule": issues_by_rule,
        }

    # =========================================================================
    # Bulk SQL checks
    # =========================================================================

    def _check_missing_titles(
        self, issues: list[dict[str, Any]], kb_name: str | None = None
    ) -> None:
        sql = "SELECT id, kb_name, entry_type FROM entry WHERE (title IS NULL OR title = '')"
        params: list[Any] = []
        if kb_name:
            sql += " AND kb_name = ?"
            params.append(kb_name)

        for row in self.db._raw_conn.execute(sql, params).fetchall():
            issues.append(
                {
                    "entry_id": row["id"],
                    "kb_name": row["kb_name"],
                    "rule": "missing_title",
                    "severity": "error",
                    "field": "title",
                    "message": f"Entry '{row['id']}' has no title",
                }
            )

    def _check_empty_bodies(
        self, issues: list[dict[str, Any]], kb_name: str | None = None
    ) -> None:
        sql = (
            "SELECT id, kb_name, entry_type, title FROM entry "
            "WHERE (body IS NULL OR body = '') "
            "AND entry_type NOT IN ('collection', 'relationship')"
        )
        params: list[Any] = []
        if kb_name:
            sql += " AND kb_name = ?"
            params.append(kb_name)

        for row in self.db._raw_conn.execute(sql, params).fetchall():
            issues.append(
                {
                    "entry_id": row["id"],
                    "kb_name": row["kb_name"],
                    "rule": "empty_body",
                    "severity": "warning",
                    "field": "body",
                    "message": f"Entry '{row['id']}' ({row['entry_type']}) has no body",
                }
            )

    def _check_events_missing_dates(
        self, issues: list[dict[str, Any]], kb_name: str | None = None
    ) -> None:
        sql = (
            "SELECT id, kb_name, title FROM entry "
            "WHERE entry_type = 'event' AND (date IS NULL OR date = '')"
        )
        params: list[Any] = []
        if kb_name:
            sql += " AND kb_name = ?"
            params.append(kb_name)

        for row in self.db._raw_conn.execute(sql, params).fetchall():
            issues.append(
                {
                    "entry_id": row["id"],
                    "kb_name": row["kb_name"],
                    "rule": "event_missing_date",
                    "severity": "error",
                    "field": "date",
                    "message": f"Event '{row['id']}' has no date",
                }
            )

    def _check_invalid_dates(
        self, issues: list[dict[str, Any]], kb_name: str | None = None
    ) -> None:
        sql = "SELECT id, kb_name, entry_type, date FROM entry WHERE date IS NOT NULL AND date != ''"
        params: list[Any] = []
        if kb_name:
            sql += " AND kb_name = ?"
            params.append(kb_name)

        for row in self.db._raw_conn.execute(sql, params).fetchall():
            if not validate_date(row["date"]):
                issues.append(
                    {
                        "entry_id": row["id"],
                        "kb_name": row["kb_name"],
                        "rule": "invalid_date",
                        "severity": "error",
                        "field": "date",
                        "message": f"Entry '{row['id']}' has invalid date: '{row['date']}'",
                    }
                )

    def _check_importance_range(
        self, issues: list[dict[str, Any]], kb_name: str | None = None
    ) -> None:
        sql = "SELECT id, kb_name, entry_type, importance FROM entry WHERE importance IS NOT NULL"
        params: list[Any] = []
        if kb_name:
            sql += " AND kb_name = ?"
            params.append(kb_name)

        for row in self.db._raw_conn.execute(sql, params).fetchall():
            if not validate_importance(row["importance"]):
                issues.append(
                    {
                        "entry_id": row["id"],
                        "kb_name": row["kb_name"],
                        "rule": "importance_range",
                        "severity": "warning",
                        "field": "importance",
                        "message": f"Entry '{row['id']}' has importance {row['importance']} (must be 1-10)",
                    }
                )

    def _check_broken_links(
        self, issues: list[dict[str, Any]], kb_name: str | None = None
    ) -> None:
        sql = (
            "SELECT l.source_id, l.source_kb, l.target_id, l.target_kb, l.relation "
            "FROM link l LEFT JOIN entry e ON l.target_id = e.id AND l.target_kb = e.kb_name "
            "WHERE e.id IS NULL"
        )
        params: list[Any] = []
        if kb_name:
            sql += " AND l.source_kb = ?"
            params.append(kb_name)

        for row in self.db._raw_conn.execute(sql, params).fetchall():
            issues.append(
                {
                    "entry_id": row["source_id"],
                    "kb_name": row["source_kb"],
                    "rule": "broken_link",
                    "severity": "error",
                    "field": "links",
                    "message": (
                        f"Entry '{row['source_id']}' links to non-existent "
                        f"'{row['target_id']}' in '{row['target_kb']}' ({row['relation']})"
                    ),
                }
            )

    def _check_orphans(
        self, issues: list[dict[str, Any]], kb_name: str | None = None
    ) -> None:
        orphans = self.db.get_orphans(kb_name=kb_name)
        for entry in orphans:
            issues.append(
                {
                    "entry_id": entry["id"],
                    "kb_name": entry["kb_name"],
                    "rule": "orphan_entry",
                    "severity": "info",
                    "field": None,
                    "message": f"Entry '{entry['id']}' has no links in either direction",
                }
            )

    # =========================================================================
    # Per-entry checks
    # =========================================================================

    def _check_entry_fields(self, entry: dict[str, Any], issues: list[dict[str, Any]]) -> None:
        """Check individual entry field validity."""
        entry_id = entry["id"]
        kb_name = entry["kb_name"]
        entry_type = entry.get("entry_type", "")

        # Missing title
        if not entry.get("title"):
            issues.append(
                {
                    "entry_id": entry_id,
                    "kb_name": kb_name,
                    "rule": "missing_title",
                    "severity": "error",
                    "field": "title",
                    "message": f"Entry '{entry_id}' has no title",
                }
            )

        # Empty body (skip collections and relationships)
        if entry_type not in ("collection", "relationship") and not entry.get("body"):
            issues.append(
                {
                    "entry_id": entry_id,
                    "kb_name": kb_name,
                    "rule": "empty_body",
                    "severity": "warning",
                    "field": "body",
                    "message": f"Entry '{entry_id}' ({entry_type}) has no body",
                }
            )

        # Event missing date
        if entry_type == "event" and not entry.get("date"):
            issues.append(
                {
                    "entry_id": entry_id,
                    "kb_name": kb_name,
                    "rule": "event_missing_date",
                    "severity": "error",
                    "field": "date",
                    "message": f"Event '{entry_id}' has no date",
                }
            )

        # Invalid date
        date_val = entry.get("date")
        if date_val and not validate_date(str(date_val)):
            issues.append(
                {
                    "entry_id": entry_id,
                    "kb_name": kb_name,
                    "rule": "invalid_date",
                    "severity": "error",
                    "field": "date",
                    "message": f"Entry '{entry_id}' has invalid date: '{date_val}'",
                }
            )

        # Importance range
        importance = entry.get("importance")
        if importance is not None and not validate_importance(importance):
            issues.append(
                {
                    "entry_id": entry_id,
                    "kb_name": kb_name,
                    "rule": "importance_range",
                    "severity": "warning",
                    "field": "importance",
                    "message": f"Entry '{entry_id}' has importance {importance} (must be 1-10)",
                }
            )

    def _check_entry_links(
        self, entry_id: str, kb_name: str, issues: list[dict[str, Any]]
    ) -> None:
        """Check links from a single entry for broken targets."""
        outlinks = self.db.get_outlinks(entry_id, kb_name)
        for link in outlinks:
            if link.get("title") is None:
                # LEFT JOIN returned NULL title = target doesn't exist
                issues.append(
                    {
                        "entry_id": entry_id,
                        "kb_name": kb_name,
                        "rule": "broken_link",
                        "severity": "error",
                        "field": "links",
                        "message": (
                            f"Entry '{entry_id}' links to non-existent "
                            f"'{link['id']}' in '{link['kb_name']}' ({link.get('relation', 'related_to')})"
                        ),
                    }
                )

    def _check_schema_validation(
        self, entry: dict[str, Any], issues: list[dict[str, Any]]
    ) -> None:
        """Run KBSchema.validate_entry() on a single entry."""
        kb_name = entry["kb_name"]
        kb_config = self.config.get_kb(kb_name)
        if not kb_config:
            return

        kb_yaml = kb_config.path / "kb.yaml"
        if not kb_yaml.exists():
            return

        schema = KBSchema.from_yaml(kb_yaml)
        entry_type = entry.get("entry_type", "")

        # Build fields dict for validation
        fields = {k: v for k, v in entry.items() if v is not None and k not in ("id", "kb_name")}

        result = schema.validate_entry(
            entry_type, fields, context={"kb_type": kb_config.kb_type}
        )

        for err in result.get("errors", []):
            issues.append(
                {
                    "entry_id": entry["id"],
                    "kb_name": kb_name,
                    "rule": "schema_violation",
                    "severity": "error",
                    "field": err.get("field", ""),
                    "message": (
                        f"Schema error on '{entry['id']}': "
                        f"field '{err.get('field', '')}' — {err.get('rule', '')} "
                        f"(expected {err.get('expected', '')}, got {err.get('got', '')})"
                    ),
                }
            )

        for warn in result.get("warnings", []):
            issues.append(
                {
                    "entry_id": entry["id"],
                    "kb_name": kb_name,
                    "rule": "schema_violation",
                    "severity": "warning",
                    "field": warn.get("field", ""),
                    "message": (
                        f"Schema warning on '{entry['id']}': "
                        f"field '{warn.get('field', '')}' — {warn.get('rule', '')} "
                        f"(expected {warn.get('expected', '')}, got {warn.get('got', '')})"
                    ),
                }
            )

    # =========================================================================
    # Schema pass (all entries)
    # =========================================================================

    def _check_schema_all(
        self, issues: list[dict[str, Any]], kb_name: str
    ) -> None:
        """Run schema validation on all entries in a KB (only if kb.yaml exists)."""
        kb_config = self.config.get_kb(kb_name)
        if not kb_config:
            return

        kb_yaml = kb_config.path / "kb.yaml"
        if not kb_yaml.exists():
            return

        schema = KBSchema.from_yaml(kb_yaml)

        rows = self.db._raw_conn.execute(
            "SELECT id, kb_name, entry_type, title, date, importance, status, metadata "
            "FROM entry WHERE kb_name = ?",
            (kb_name,),
        ).fetchall()

        for row in rows:
            entry = dict(row)
            entry_type = entry.get("entry_type", "")
            fields = {k: v for k, v in entry.items() if v is not None and k not in ("id", "kb_name")}

            result = schema.validate_entry(
                entry_type, fields, context={"kb_type": kb_config.kb_type}
            )

            for err in result.get("errors", []):
                issues.append(
                    {
                        "entry_id": entry["id"],
                        "kb_name": kb_name,
                        "rule": "schema_violation",
                        "severity": "error",
                        "field": err.get("field", ""),
                        "message": (
                            f"Schema error on '{entry['id']}': "
                            f"field '{err.get('field', '')}' — {err.get('rule', '')} "
                            f"(expected {err.get('expected', '')}, got {err.get('got', '')})"
                        ),
                    }
                )

            for warn in result.get("warnings", []):
                issues.append(
                    {
                        "entry_id": entry["id"],
                        "kb_name": kb_name,
                        "rule": "schema_violation",
                        "severity": "warning",
                        "field": warn.get("field", ""),
                        "message": (
                            f"Schema warning on '{entry['id']}': "
                            f"field '{warn.get('field', '')}' — {warn.get('rule', '')} "
                            f"(expected {warn.get('expected', '')}, got {warn.get('got', '')})"
                        ),
                    }
                )
