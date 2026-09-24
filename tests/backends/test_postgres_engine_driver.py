"""
Which DBAPI driver a Postgres URL resolves to.

SQLAlchemy 2.1 changed the default driver for a bare ``postgresql://`` URL
from psycopg2 to psycopg (v3). The ``postgres`` extra installs
``psycopg2-binary``, so on 2.1 every bare URL failed at ``create_engine`` with
``ModuleNotFoundError: No module named 'psycopg'``. Every Postgres engine is
built through ``create_postgres_engine``, which pins a bare URL to psycopg2
and leaves a driver the user chose alone.

``create_engine`` loads the dialect and imports its DBAPI but does not
connect, so none of this needs a running Postgres.
"""

import pytest

pytest.importorskip("psycopg2")

from pyrite.storage.backends.postgres_backend import (  # noqa: E402
    create_postgres_engine,
    postgres_url,
)


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://user:secret@localhost:5432/pyrite",
        "postgres://user:secret@localhost:5432/pyrite",
    ],
)
def test_bare_url_engine_uses_psycopg2(url):
    engine = create_postgres_engine(url)
    try:
        assert engine.dialect.driver == "psycopg2"
        # The password survives normalization (a rendered URL masks it).
        assert engine.url.password == "secret"
        assert engine.url.database == "pyrite"
    finally:
        engine.dispose()


def test_engine_kwargs_pass_through():
    engine = create_postgres_engine(
        "postgresql://localhost/pyrite", connect_args={"options": "-csearch_path=s1,public"}
    )
    try:
        assert engine.dialect.driver == "psycopg2"
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    ("url", "driver"),
    [
        ("postgresql+psycopg://u:p@localhost/pyrite", "postgresql+psycopg"),
        ("postgresql+psycopg2://u:p@localhost/pyrite", "postgresql+psycopg2"),
        ("postgresql+asyncpg://u:p@localhost/pyrite", "postgresql+asyncpg"),
    ],
)
def test_explicit_driver_is_left_alone(url, driver):
    resolved = postgres_url(url)
    assert resolved.drivername == driver
    assert resolved.password == "p"


def test_bare_urls_normalize_to_psycopg2():
    assert postgres_url("postgresql://h/db").drivername == "postgresql+psycopg2"
    assert postgres_url("postgres://h/db").drivername == "postgresql+psycopg2"


def test_postgres_alias_with_explicit_driver_keeps_the_driver():
    # SQLAlchemy has no dialect named "postgres"; the driver the user chose stays.
    assert postgres_url("postgres+psycopg://h/db").drivername == "postgresql+psycopg"


def test_non_postgres_url_is_rejected():
    with pytest.raises(ValueError, match="not a PostgreSQL URL"):
        postgres_url("sqlite:///tmp/x.db")
