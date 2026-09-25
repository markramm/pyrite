"""QUERY_SYNTAX must name the token the caller wrote, not SQLite's fragment (#67).

`detention AND third-party-doctrine` reaches MATCH unquoted because the query
carries an operator, and SQLite answers `no such column: party` — a fragment of
a token the caller never typed, which sends the reader looking for a schema
problem. The message now names the real token. Whenever the error does not name
a token we can find, the previous text is kept untouched.
"""

import sqlite3

import pytest

from pyrite.exceptions import QuerySyntaxError
from pyrite.services.search_service import SearchService


class _RaisingDB:
    """A db whose search always fails with the given error."""

    def __init__(self, error: sqlite3.OperationalError):
        self.error = error

    def search(self, **kwargs):
        raise self.error


def _message(query: str, error_text: str) -> str:
    service = SearchService(_RaisingDB(sqlite3.OperationalError(error_text)))
    with pytest.raises(QuerySyntaxError) as excinfo:
        service._db_search(query=query)
    return str(excinfo.value)


def test_names_the_token_the_caller_wrote():
    message = _message("detention AND third-party-doctrine", "no such column: party")

    assert "third-party-doctrine" in message
    assert "no such column" not in message
    # The suggestion quotes the token it just named.
    assert '"third-party-doctrine"' in message


def test_prefers_the_token_the_fragment_came_from():
    message = _message("detention AND cross-link AND third-party-doctrine", "no such column: party")

    assert "third-party-doctrine" in message
    assert "cross-link" not in message


def test_does_not_blame_a_token_the_error_does_not_name():
    message = _message("detention AND third-party-doctrine", "no such column: zebra")

    assert "no such column: zebra" in message
    assert "third-party-doctrine" not in message


def test_other_operational_errors_keep_the_previous_text():
    message = _message("detention AND third-party-doctrine", "unterminated string")

    assert "unterminated string" in message
    assert "third-party-doctrine" not in message


def test_error_code_is_unchanged():
    service = SearchService(_RaisingDB(sqlite3.OperationalError("no such column: party")))

    with pytest.raises(QuerySyntaxError) as excinfo:
        service._db_search(query="detention AND third-party-doctrine")

    assert excinfo.value.error_code == "QUERY_SYNTAX"


# ---------------------------------------------------------------------------
# A non-syntax OperationalError is a server failure, not the caller's fault
# (#414 fix round 2): "database is locked", a disk I/O error, a missing
# table, or a database file that can't be opened must stay a 5xx and be
# logged -- not get relabeled QUERY_SYNTAX/400 just because they are also
# OperationalError under the hood.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "error_text",
    [
        "database is locked",
        "disk I/O error",
        "no such table: entry_fts",
        "unable to open database file",
    ],
)
def test_non_syntax_operational_errors_are_not_query_syntax_error(error_text):
    from pyrite.exceptions import StorageError

    service = SearchService(_RaisingDB(sqlite3.OperationalError(error_text)))
    with pytest.raises(StorageError) as excinfo:
        service._db_search(query="hello")
    assert error_text in str(excinfo.value)
    # And specifically not reclassified as the caller's query being bad.
    assert not isinstance(excinfo.value, QuerySyntaxError)
