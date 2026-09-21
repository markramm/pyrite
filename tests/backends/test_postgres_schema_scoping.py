"""`ensure_schema()` must set a database up correctly in more than one schema.

Postgres resolves unqualified DDL through the connection's `search_path`, so
two Pyrite instances can share one database by each owning a schema -- an
ordinary multi-tenant or staging-beside-prod layout, and the mechanism
`tests/backends/conftest.py` uses to give every xdist worker its own tables.

`pg_trigger` does not work that way. It is cluster-wide and `tgname` is not
unique across tables, so a guard that asks only "does a trigger named X
exist?" answers *yes* for a trigger on some other schema's table. The second
schema then silently gets no FTS trigger: `entry.fts_vector` stays NULL,
`search()` returns zero rows, and nothing raises. The failure is invisible
without a real Postgres and two schemas, which is why it survived.
"""

import os

import pytest

pytest.importorskip("psycopg2")

from sqlalchemy import create_engine, text  # noqa: E402

from pyrite.storage.backends.postgres_backend import ensure_schema  # noqa: E402
from pyrite.storage.models import Base  # noqa: E402


def _pg_url():
    return os.environ.get("PYRITE_TEST_PG_URL")


def _two_schema_names():
    """A private pair of schema names for this test in this worker.

    Suffixed with the xdist worker id for the same reason `conftest.py` gives
    each worker its own schema: two tests in different worker processes that
    both used a fixed pair would create the same tables in the same namespace
    and collide on `pg_type_typname_nsp_index`. This module has two tests, so
    at `-n 8` that is not hypothetical -- it was observed before the suffix.
    """
    worker = os.environ.get("PYTEST_XDIST_WORKER", "serial")
    return (f"pyrite_scope_a_{worker}", f"pyrite_scope_b_{worker}")


@pytest.fixture
def two_schemas():
    """Two schemas on one database, each set up through the real ensure_schema()."""
    url = _pg_url()
    if not url:
        pytest.skip("PYRITE_TEST_PG_URL not set")

    schema_names = _two_schema_names()

    admin = create_engine(url)
    with admin.connect() as conn:
        # The extension is per-database and must live somewhere both schemas
        # can see, or `vector` does not resolve for the second one.
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector SCHEMA public"))
        for name in schema_names:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{name}" CASCADE'))
            conn.execute(text(f'CREATE SCHEMA "{name}"'))
        conn.commit()

    engines = {
        name: create_engine(url, connect_args={"options": f"-csearch_path={name},public"})
        for name in schema_names
    }
    # Both schemas fully built BEFORE any assertion: the bug only appears when
    # the second one is created while the first one's trigger already exists.
    for engine in engines.values():
        Base.metadata.create_all(engine)
        ensure_schema(engine)
        with engine.connect() as conn:
            # entry.kb_name is a foreign key; every schema needs its own KB row.
            conn.execute(
                text(
                    "INSERT INTO kb (name, kb_type, path, description) "
                    "VALUES ('test', 'generic', '/tmp/test', 'Test KB')"
                )
            )
            conn.commit()

    yield engines

    for engine in engines.values():
        engine.dispose()
    with admin.connect() as conn:
        for name in schema_names:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{name}" CASCADE'))
        conn.commit()
    admin.dispose()


def test_every_schema_gets_its_own_fts_trigger(two_schemas):
    """The guard must be scoped to the table, not to the bare trigger name."""
    for name, engine in two_schemas.items():
        with engine.connect() as conn:
            found = conn.execute(
                text(
                    "SELECT 1 FROM pg_trigger t "
                    "JOIN pg_class c ON c.oid = t.tgrelid "
                    "JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE t.tgname = 'trg_entry_fts' AND n.nspname = :schema"
                ),
                {"schema": name},
            ).fetchone()
        assert found is not None, (
            f"schema {name!r} has no trg_entry_fts trigger. ensure_schema() "
            "guards it with a lookup on pg_trigger, which is cluster-wide: "
            "once any table anywhere carries a trigger of that name the guard "
            "reports it as present and this schema silently gets none, so "
            "fts_vector is never populated and search returns nothing."
        )


def test_full_text_search_works_in_every_schema(two_schemas):
    """The user-visible consequence: a search that silently returns nothing."""
    for name, engine in two_schemas.items():
        with engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO entry (id, kb_name, entry_type, title, body) "
                    "VALUES (:id, 'test', 'note', :title, :body)"
                ),
                {
                    "id": f"entry-in-{name}",
                    "title": "Distinctive Zarquon Heading",
                    "body": "the body mentions zarquon as well",
                },
            )
            conn.commit()

            populated = conn.execute(
                text("SELECT fts_vector IS NOT NULL FROM entry WHERE id = :id"),
                {"id": f"entry-in-{name}"},
            ).scalar()
            assert populated, (
                f"entry inserted into schema {name!r} has a NULL fts_vector -- "
                "the BEFORE INSERT trigger did not fire in this schema, so "
                "keyword search cannot match it"
            )

            hits = conn.execute(
                text(
                    "SELECT count(*) FROM entry "
                    "WHERE fts_vector @@ plainto_tsquery('english', 'zarquon')"
                )
            ).scalar()
            assert hits == 1, (
                f"full-text search in schema {name!r} returned {hits} rows for a "
                "term that is in the entry it just inserted"
            )
