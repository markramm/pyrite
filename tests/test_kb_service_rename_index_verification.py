"""Regression tests for read-back index verification on KBService.rename_entry.

verify-after-write-on-the-index-path (second checklist item): a rename
that succeeds on disk but whose index sync silently fails or misses the
new entry currently only logs a warning — old_id keeps resolving in
search/lookups and new_id stays invisible, discovered only at the next
manual `index sync`. This must surface in the result, not just a log line.
"""

from unittest.mock import patch

import pytest

from pyrite.exceptions import StorageError
from pyrite.services.kb_service import KBService
from pyrite.storage.repository import KBRepository


def _kb_service(indexed_test_env):
    return KBService(indexed_test_env["config"], indexed_test_env["db"])


class TestRenameIndexVerification:
    def test_successful_rename_reports_index_verified(self, indexed_test_env, sample_events):
        """The common case: rename + sync succeed, and the result records
        that the new id was confirmed resolvable in the index — not just
        that sync_incremental didn't raise."""
        kb_service = _kb_service(indexed_test_env)
        old_id = sample_events[0].id
        kb_name = indexed_test_env["events_kb"].name

        result = kb_service.rename_entry(old_id, "renamed-entry-id", kb_name)

        assert result["renamed"] is True
        assert result["index_verified"] is True

    def test_successful_rename_new_id_resolves_in_index(self, indexed_test_env, sample_events):
        db = indexed_test_env["db"]
        kb_service = _kb_service(indexed_test_env)
        old_id = sample_events[0].id
        kb_name = indexed_test_env["events_kb"].name

        kb_service.rename_entry(old_id, "renamed-entry-id", kb_name)

        assert db.get_entry("renamed-entry-id", kb_name) is not None
        assert db.get_entry(old_id, kb_name) is None

    def test_index_sync_failure_raises_storage_error_not_silent_warning(
        self, indexed_test_env, sample_events
    ):
        """Before this fix: sync_incremental raising was caught and
        downgraded to logger.warning, so the caller (CLI/MCP/REST) got a
        200/success response even though the index never learned about
        the rename. That's exactly the derived-state-sync bug class this
        epic exists to close -- the file operation succeeding while the
        index silently drifts must not look like success to the caller."""
        kb_service = _kb_service(indexed_test_env)
        old_id = sample_events[0].id
        kb_name = indexed_test_env["events_kb"].name

        with patch.object(
            kb_service._index_mgr,
            "sync_incremental",
            side_effect=RuntimeError("simulated index failure"),
        ):
            with pytest.raises(StorageError, match="index"):
                kb_service.rename_entry(old_id, "renamed-entry-id", kb_name)

    def test_index_sync_failure_leaves_file_rename_intact(self, indexed_test_env, sample_events):
        """The file rename already succeeded before sync_incremental ran --
        raising StorageError must not attempt to undo it (that would be a
        new failure mode). The file system state is the source of truth;
        only the index is degraded, and a follow-up `index sync` recovers."""
        kb_service = _kb_service(indexed_test_env)
        old_id = sample_events[0].id
        kb_name = indexed_test_env["events_kb"].name
        events_kb = indexed_test_env["events_kb"]

        with patch.object(
            kb_service._index_mgr,
            "sync_incremental",
            side_effect=RuntimeError("simulated index failure"),
        ):
            with pytest.raises(StorageError):
                kb_service.rename_entry(old_id, "renamed-entry-id", kb_name)

        # The file itself was already renamed on disk before the index
        # sync ran -- that part of the operation is not rolled back.
        remaining_ids = {e.id for e, _path in KBRepository(events_kb).list_entries()}
        assert "renamed-entry-id" in remaining_ids
        assert old_id not in remaining_ids

    def test_index_sync_succeeds_but_new_id_missing_raises_storage_error(
        self, indexed_test_env, sample_events
    ):
        """A subtler failure than sync_incremental raising: sync completes
        without error, but the new id still doesn't resolve (e.g. a
        malformed-frontmatter skip, or the file landed somewhere the
        indexer didn't scan). The read-back check must catch this too --
        "sync didn't throw" is not the same guarantee as "sync worked"."""
        kb_service = _kb_service(indexed_test_env)
        old_id = sample_events[0].id
        kb_name = indexed_test_env["events_kb"].name

        with patch.object(
            kb_service._index_mgr, "sync_incremental", return_value={"added": 0, "updated": 0}
        ):
            with pytest.raises(StorageError, match="index"):
                kb_service.rename_entry(old_id, "renamed-entry-id", kb_name)

    def test_dry_run_skips_index_verification(self, indexed_test_env, sample_events):
        """A dry run never touches the filesystem or the index -- there is
        nothing to verify, and it must not raise. (dry_run still reports
        renamed=True as "this is the plan that would execute" -- only the
        actual file/index side effects are skipped.)"""
        kb_service = _kb_service(indexed_test_env)
        old_id = sample_events[0].id
        kb_name = indexed_test_env["events_kb"].name

        result = kb_service.rename_entry(old_id, "renamed-entry-id", kb_name, dry_run=True)
        assert result["dry_run"] is True
        assert "index_verified" not in result
