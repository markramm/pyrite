"""
QA Fix Service — auto-fix for safe structural issues in knowledge bases.

Extracted from QAService. Handles date normalisation, missing field defaults,
broken wikilink fixes by edit distance, and tag normalisation.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from ..config import PyriteConfig
from ..storage.database import PyriteDB
from ..utils.metadata import parse_metadata

logger = logging.getLogger(__name__)


class QAFixService:
    """Auto-fix safe structural issues in knowledge bases."""

    # Rules that can be safely auto-fixed.
    FIXABLE_RULES = frozenset(
        {
            "invalid_date",
            "schema_violation",  # only missing-field sub-cases
            "broken_link",
        }
    )

    def __init__(self, config: PyriteConfig, db: PyriteDB, kb_svc=None):
        self.config = config
        self.db = db
        self._kb_svc = kb_svc

    def fix_kb(
        self,
        kb_name: str,
        *,
        dry_run: bool = True,
        fix_rules: list[str] | None = None,
        validate_kb_fn=None,
    ) -> dict[str, Any]:
        """Auto-fix safe structural issues in a KB.

        Runs validation first, then applies mechanical fixes where
        unambiguous.  Returns a report of what was fixed, what was skipped,
        and what still needs manual attention.

        Args:
            kb_name: KB to fix.
            dry_run: If True, report planned fixes without writing.
            fix_rules: Optional list of rule names to restrict fixes to.
            validate_kb_fn: Callable to run validation (injected by QAService).

        Returns:
            Dict with fixed, skipped, manual lists plus summary counts.
        """
        if self._kb_svc is not None:
            kb_svc = self._kb_svc
        else:
            from .kb_service import KBService

            kb_svc = KBService(self.config, self.db)

        # Run validation to discover issues
        result = validate_kb_fn(kb_name)
        issues = result["issues"]

        fixed: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []
        manual: list[dict[str, Any]] = []

        # Collect all entry IDs in this KB for wikilink matching
        all_entry_ids = self._get_all_entry_ids(kb_name)

        # Group issues by entry_id for batch updates
        issues_by_entry: dict[str, list[dict[str, Any]]] = {}
        for issue in issues:
            eid = issue.get("entry_id", "")
            if eid:
                issues_by_entry.setdefault(eid, []).append(issue)

        # Also run tag normalisation pass
        tag_fixes = self._find_tag_normalisation_fixes(kb_name)

        # Apply fix_rules filter if provided
        active_fix_rules = set(fix_rules) if fix_rules else None

        for entry_id, entry_issues in issues_by_entry.items():
            updates: dict[str, Any] = {}

            for issue in entry_issues:
                rule = issue.get("rule", "")

                # Filter by fix_rules if specified
                if active_fix_rules and rule not in active_fix_rules:
                    if rule not in active_fix_rules and "tag_case" not in active_fix_rules:
                        skipped.append({**issue, "reason": "filtered_by_fix_rule"})
                        continue

                if rule == "invalid_date":
                    fix = self._fix_invalid_date(issue)
                    if fix:
                        updates["date"] = fix["new_value"]
                        fixed.append(fix)
                    else:
                        manual.append({**issue, "reason": "cannot_normalise_date"})

                elif rule == "schema_violation" and "missing" in issue.get("message", "").lower():
                    fix = self._fix_missing_field(issue)
                    if fix:
                        field_name = fix["field"]
                        if field_name.startswith("metadata."):
                            meta_key = field_name.split(".", 1)[1]
                            meta_updates = updates.get("metadata", {})
                            meta_updates[meta_key] = fix["new_value"]
                            updates["metadata"] = meta_updates
                        else:
                            updates[field_name] = fix["new_value"]
                        fixed.append(fix)
                    else:
                        manual.append({**issue, "reason": "no_safe_default"})

                elif rule == "broken_link":
                    fix = self._fix_broken_link(issue, all_entry_ids)
                    if fix:
                        fixed.append(fix)
                        # Broken link fixes need special handling via link
                        # update — applied separately below.
                        if not dry_run:
                            self._apply_link_fix(
                                issue["entry_id"],
                                issue["kb_name"],
                                fix["old_target"],
                                fix["new_value"],
                                kb_svc,
                            )
                    else:
                        manual.append({**issue, "reason": "no_close_match"})
                else:
                    manual.append({**issue, "reason": "not_auto_fixable"})

            # Apply accumulated field updates for this entry
            if updates and not dry_run:
                try:
                    # Handle metadata merge specially
                    if "metadata" in updates:
                        meta_extra = updates.pop("metadata")
                        # Load current metadata first
                        rows = self.db.execute_sql(
                            "SELECT metadata FROM entry WHERE id = :eid AND kb_name = :kb",
                            {"eid": entry_id, "kb": kb_name},
                        )
                        current_meta = parse_metadata(
                            rows[0]["metadata"] if rows else None
                        )
                        current_meta.update(meta_extra)
                        updates["metadata"] = current_meta

                    kb_svc.update_entry(entry_id, kb_name, **updates)
                except Exception as e:
                    logger.warning("Failed to apply fix to %s: %s", entry_id, e)
                    # Move these from fixed to manual
                    for f in list(fixed):
                        if f.get("entry_id") == entry_id:
                            fixed.remove(f)
                            manual.append({**f, "reason": f"update_failed: {e}"})

        # Tag normalisation
        for tag_fix in tag_fixes:
            if active_fix_rules and "tag_case" not in active_fix_rules:
                skipped.append({**tag_fix, "reason": "filtered_by_fix_rule"})
                continue
            fixed.append(tag_fix)
            if not dry_run:
                self._apply_tag_normalisation(
                    tag_fix["entry_id"],
                    kb_name,
                    tag_fix["old_value"],
                    tag_fix["new_value"],
                    kb_svc,
                )

        return {
            "kb_name": kb_name,
            "dry_run": dry_run,
            "fixed_count": len(fixed),
            "skipped_count": len(skipped),
            "manual_count": len(manual),
            "fixed": fixed,
            "skipped": skipped,
            "manual": manual,
        }

    def _get_all_entry_ids(self, kb_name: str) -> list[str]:
        """Get all entry IDs in a KB for edit-distance matching."""
        rows = self.db.execute_sql(
            "SELECT id FROM entry WHERE kb_name = :kb_name",
            {"kb_name": kb_name},
        )
        return [row["id"] for row in rows]

    @staticmethod
    def _normalise_date(raw: str) -> str | None:
        """Try to normalise a date string to YYYY-MM-DD.

        Handles: YYYY, YYYY-MM, MM/DD/YYYY, DD/MM/YYYY (if unambiguous),
        and ISO datetime strings.

        Returns normalised string or None if not parseable.
        """
        raw = raw.strip().strip("'\"")

        # Already valid YYYY-MM-DD
        if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
            return raw

        # Just a year: YYYY -> YYYY-01-01
        if re.match(r"^\d{4}$", raw):
            return f"{raw}-01-01"

        # Year-month: YYYY-MM -> YYYY-MM-01
        m = re.match(r"^(\d{4})-(\d{1,2})$", raw)
        if m:
            year, month = m.group(1), m.group(2).zfill(2)
            return f"{year}-{month}-01"

        # ISO datetime: YYYY-MM-DDTHH:MM:SS... -> YYYY-MM-DD
        m = re.match(r"^(\d{4}-\d{2}-\d{2})T", raw)
        if m:
            return m.group(1)

        # US-style: MM/DD/YYYY
        m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", raw)
        if m:
            month, day, year = m.group(1).zfill(2), m.group(2).zfill(2), m.group(3)
            try:
                datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d")
                return f"{year}-{month}-{day}"
            except ValueError:
                return None

        return None

    def _fix_invalid_date(self, issue: dict[str, Any]) -> dict[str, Any] | None:
        """Attempt to fix an invalid date issue. Returns fix dict or None."""
        msg = issue.get("message", "")
        # Extract the raw date from the message (after "invalid date: '...'")
        m = re.search(r"invalid date:\s*'([^']*)'", msg)
        if not m:
            return None

        raw_date = m.group(1)
        normalised = self._normalise_date(raw_date)
        if normalised is None:
            return None

        return {
            "entry_id": issue["entry_id"],
            "kb_name": issue["kb_name"],
            "rule": "invalid_date",
            "field": "date",
            "old_value": raw_date,
            "new_value": normalised,
            "message": f"Normalised date '{raw_date}' -> '{normalised}'",
        }

    @staticmethod
    def _fix_missing_field(issue: dict[str, Any]) -> dict[str, Any] | None:
        """Provide a type-appropriate default for a missing required field.

        Only handles fields where a safe default exists.
        Returns fix dict or None.
        """
        field = issue.get("field", "")

        # Map of field names to safe defaults
        safe_defaults: dict[str, Any] = {
            "importance": 5,
        }

        default_val = safe_defaults.get(field)
        if default_val is None:
            return None

        return {
            "entry_id": issue["entry_id"],
            "kb_name": issue["kb_name"],
            "rule": "schema_violation",
            "field": field,
            "old_value": None,
            "new_value": default_val,
            "message": f"Added default {field}={default_val}",
        }

    @staticmethod
    def _edit_distance(a: str, b: str) -> int:
        """Compute Levenshtein edit distance between two strings."""
        if len(a) < len(b):
            return QAFixService._edit_distance(b, a)

        if len(b) == 0:
            return len(a)

        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a):
            curr = [i + 1]
            for j, cb in enumerate(b):
                cost = 0 if ca == cb else 1
                curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))
            prev = curr

        return prev[len(b)]

    def _fix_broken_link(
        self,
        issue: dict[str, Any],
        all_entry_ids: list[str],
    ) -> dict[str, Any] | None:
        """Fix broken link by finding closest entry ID by edit distance.

        Only fixes if the best match is within 40% edit distance of the
        target ID length (i.e. a plausible typo, not a completely
        different ID).

        Returns fix dict or None.
        """
        msg = issue.get("message", "")
        # Extract target_id from message: "links to non-existent 'xxx' in 'yyy'"
        m = re.search(r"links to non-existent '([^']*)'", msg)
        if not m:
            return None

        broken_target = m.group(1)

        if not all_entry_ids:
            return None

        # Find closest match
        best_id = None
        best_dist = float("inf")
        for eid in all_entry_ids:
            d = self._edit_distance(broken_target, eid)
            if d < best_dist:
                best_dist = d
                best_id = eid

        # Only fix if within reasonable edit distance (40% of target length)
        max_allowed = max(2, int(len(broken_target) * 0.4))
        if best_dist > max_allowed or best_id is None:
            return None

        return {
            "entry_id": issue["entry_id"],
            "kb_name": issue["kb_name"],
            "rule": "broken_link",
            "field": "links",
            "old_target": broken_target,
            "old_value": broken_target,
            "new_value": best_id,
            "edit_distance": best_dist,
            "message": f"Fixed broken link '{broken_target}' -> '{best_id}' (distance={best_dist})",
        }

    def _apply_link_fix(
        self,
        entry_id: str,
        kb_name: str,
        old_target: str,
        new_target: str,
        kb_svc,
    ) -> None:
        """Update a broken link target in the entry's link list and re-save."""
        from ..storage.repository import KBRepository

        kb_config = self.config.get_kb(kb_name)
        if not kb_config:
            return

        repo = KBRepository(kb_config)
        entry = repo.load(entry_id)
        if not entry:
            return

        # Update the link target in the entry's links list
        changed = False
        for link in entry.links:
            if link.target == old_target:
                link.target = new_target
                changed = True

        if changed:
            kb_svc.update_entry(entry_id, kb_name, links=entry.links)

    def _find_tag_normalisation_fixes(self, kb_name: str) -> list[dict[str, Any]]:
        """Find tags with mixed case that should be lowercased.

        Returns list of fix dicts (one per entry+tag combination).
        """
        rows = self.db.execute_sql(
            "SELECT et.entry_id, t.name AS tag_name FROM entry_tag et "
            "JOIN tag t ON et.tag_id = t.id "
            "WHERE et.kb_name = :kb_name AND t.name != LOWER(t.name)",
            {"kb_name": kb_name},
        )

        fixes = []
        for row in rows:
            tag_name = row["tag_name"]
            fixes.append(
                {
                    "entry_id": row["entry_id"],
                    "kb_name": kb_name,
                    "rule": "tag_case",
                    "field": "tags",
                    "old_value": tag_name,
                    "new_value": tag_name.lower(),
                    "message": f"Normalised tag '{tag_name}' -> '{tag_name.lower()}'",
                }
            )

        return fixes

    def _apply_tag_normalisation(
        self,
        entry_id: str,
        kb_name: str,
        old_tag: str,
        new_tag: str,
        kb_svc,
    ) -> None:
        """Normalise a single tag on an entry by updating its tag list."""
        from ..storage.repository import KBRepository

        kb_config = self.config.get_kb(kb_name)
        if not kb_config:
            return

        repo = KBRepository(kb_config)
        entry = repo.load(entry_id)
        if not entry:
            return

        new_tags = [new_tag if t == old_tag else t for t in entry.tags]
        kb_svc.update_entry(entry_id, kb_name, tags=new_tags)
