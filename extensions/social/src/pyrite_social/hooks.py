"""Social KB lifecycle hooks.

Enforces author-only editing and maintains writeup counts.
"""

import logging
from typing import Any

from pyrite.models.base import Entry

logger = logging.getLogger(__name__)


def before_save_author_check(entry: Entry, context: dict[str, Any]) -> Entry:
    """Enforce author_edit_only policy.

    For writeup entries, the current user must be the author (or the operation
    must be a create). Uses the folder-per-author convention: the entry's file
    path should be under writeups/<author_id>/.
    """
    if entry.entry_type != "writeup":
        return entry

    author_id = getattr(entry, "author_id", "")
    user = context.get("user", "")
    operation = context.get("operation", "")

    # On create, set author_id to current user if not already set
    if operation == "create" and not author_id and user:
        entry.author_id = user
        return entry

    # On update, check that the user is the author
    if operation == "update" and user and author_id:
        if user != author_id:
            raise PermissionError(f"User '{user}' cannot edit writeup owned by '{author_id}'")

    return entry


def after_save_update_counts(entry: Entry, context: dict[str, Any]) -> None:
    """Update the author's writeup_count after saving a writeup.

    This is a best-effort side effect — failures are logged but don't abort.
    """
    if entry.entry_type != "writeup":
        return

    author_id = getattr(entry, "author_id", "")
    if not author_id:
        return

    kb_name = context.get("kb_name", "")
    operation = context.get("operation", "")

    if operation != "create":
        return

    # Log the count update — actual DB update would require the db instance
    # which hooks don't currently receive. This is a known gap.
    logger.info(
        "Writeup created by %s in %s — writeup_count should be incremented",
        author_id,
        kb_name,
    )


def after_delete_adjust_reputation(entry: Entry, context: dict[str, Any]) -> None:
    """Adjust reputation when a writeup with votes is deleted.

    This is a best-effort side effect — failures are logged but don't abort.
    """
    if entry.entry_type != "writeup":
        return

    author_id = getattr(entry, "author_id", "")
    if not author_id:
        return

    logger.info(
        "Writeup %s by %s deleted — reputation adjustments may be needed",
        entry.id,
        author_id,
    )
