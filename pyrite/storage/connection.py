"""
Database connection setup, extensions, migrations, and plugin tables.

Mixin class providing __init__, close, transaction, and schema management.
"""

import logging
import re
import sqlite3
import warnings
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session

from .backends.sqlite_backend import SQLiteBackend
from .models import Base
from .virtual_tables import create_fts_tables, create_vec_table

logger = logging.getLogger(__name__)

# Register explicit adapters to avoid Python 3.12+ deprecation warnings
sqlite3.register_adapter(datetime, lambda dt: dt.isoformat())
sqlite3.register_adapter(date, lambda d: d.isoformat())
sqlite3.register_converter("timestamp", lambda b: datetime.fromisoformat(b.decode()))


class ConnectionMixin:
    """Database connection, extensions, migrations, and plugin table creation."""

    def _init_connection(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create SQLAlchemy engine
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )

        # Set SQLite pragmas on every connection
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("PRAGMA journal_mode = WAL")
            cursor.execute("PRAGMA synchronous = NORMAL")
            cursor.close()

        # Create ORM tables
        Base.metadata.create_all(self.engine)

        # Create session
        self.session = Session(self.engine)

        # Derive raw connection FROM the session's underlying connection
        # This ensures ORM writes and raw SQL share the same connection
        self._sa_conn = self.engine.connect()
        self._raw_conn = self._sa_conn.connection.dbapi_connection
        self._raw_conn.row_factory = sqlite3.Row

        # Load extensions and create virtual tables
        self._load_extensions()
        create_fts_tables(self._raw_conn)
        if self.vec_available:
            create_vec_table(self._raw_conn)

        self._run_migrations()
        self._create_plugin_tables()

        # Instantiate the search backend
        self._backend = SQLiteBackend(
            session=self.session,
            raw_conn=self._raw_conn,
            vec_available=self.vec_available,
        )

    def _load_extensions(self):
        """Try to load sqlite-vec extension for vector search."""
        self.vec_available = False
        try:
            import sqlite_vec

            self._raw_conn.enable_load_extension(True)
            sqlite_vec.load(self._raw_conn)
            self._raw_conn.enable_load_extension(False)
            self.vec_available = True
        except (ImportError, Exception):
            pass

    def _run_migrations(self):
        """Run any pending database migrations using legacy MigrationManager."""
        from .migrations import MigrationManager

        mgr = MigrationManager(self._raw_conn)
        pending = mgr.get_pending_migrations()
        if pending:
            mgr.migrate()
        # Create vec_entry table if sqlite-vec is available and table doesn't exist
        if self.vec_available:
            create_vec_table(self._raw_conn)

    def _create_plugin_tables(self):
        """Create custom tables defined by plugins."""
        try:
            from ..plugins import get_registry

            for table_def in get_registry().get_all_db_tables():
                self._create_table_from_def(table_def)
        except Exception:
            logger.warning("Plugin table creation failed", exc_info=True)

    _VALID_SQL_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    _VALID_SQL_TYPE = re.compile(r"^[A-Z][A-Z0-9_ ()]*$")
    _VALID_FK_REF = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*\([a-zA-Z_][a-zA-Z0-9_]*\)$")
    _VALID_SQL_DEFAULT = re.compile(
        r"^(?:NULL|TRUE|FALSE|CURRENT_TIMESTAMP|[0-9]+(?:\.[0-9]+)?|'[^']*')$",
        re.IGNORECASE,
    )

    def _validate_identifier(self, value: str, context: str) -> str:
        """Validate a SQL identifier to prevent injection."""
        if not self._VALID_SQL_IDENTIFIER.match(value):
            raise ValueError(f"Invalid SQL identifier for {context}: {value!r}")
        return value

    def _create_table_from_def(self, table_def: dict):
        """Create a single table from a plugin table definition."""
        name = self._validate_identifier(table_def["name"], "table name")
        columns = table_def.get("columns", [])
        indexes = table_def.get("indexes", [])

        col_defs = []
        for col in columns:
            col_name = self._validate_identifier(col["name"], "column name")
            col_type = col["type"]
            if not self._VALID_SQL_TYPE.match(col_type):
                raise ValueError(f"Invalid SQL type: {col_type!r}")
            parts = [col_name, col_type]
            if col.get("primary_key"):
                parts.append("PRIMARY KEY")
                if col_type == "INTEGER":
                    parts.append("AUTOINCREMENT")
            if col.get("nullable") is False:
                parts.append("NOT NULL")
            if "default" in col:
                default_val = str(col["default"])
                if not self._VALID_SQL_DEFAULT.match(default_val):
                    raise ValueError(
                        f"Invalid SQL DEFAULT value: {default_val!r}"
                    )
                parts.append(f"DEFAULT {default_val}")
            col_defs.append(" ".join(parts))

        for fk in table_def.get("foreign_keys", []):
            fk_col = self._validate_identifier(fk["column"], "foreign key column")
            fk_ref = fk["references"]
            if not self._VALID_FK_REF.match(fk_ref):
                raise ValueError(f"Invalid FK reference: {fk_ref!r}")
            col_defs.append(f"FOREIGN KEY ({fk_col}) REFERENCES {fk_ref}")

        sql = f"CREATE TABLE IF NOT EXISTS {name} ({', '.join(col_defs)})"
        self._raw_conn.execute(sql)

        for idx in indexes:
            for idx_col in idx["columns"]:
                self._validate_identifier(idx_col, "index column")
            cols = ", ".join(idx["columns"])
            unique = "UNIQUE " if idx.get("unique") else ""
            idx_name = f"idx_{name}_{'_'.join(idx['columns'])}"
            self._raw_conn.execute(
                f"CREATE {unique}INDEX IF NOT EXISTS {idx_name} ON {name} ({cols})"
            )

        self._raw_conn.commit()

    @property
    def conn(self):
        """Backward-compat: returns raw sqlite3 connection.

        Deprecated: Use ``session`` for writes and ``execute_sql()`` for
        read-only raw SQL queries.
        """
        warnings.warn(
            "db.conn is deprecated. Use db.session for writes and "
            "db.execute_sql() for read-only queries.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._raw_conn

    def execute_sql(self, sql: str, params=None) -> list[dict]:
        """Execute raw SQL through the session connection. For read-only search queries."""
        result = self.session.execute(text(sql), params or {})
        if result.returns_rows:
            cols = result.keys()
            return [dict(zip(cols, row, strict=False)) for row in result.fetchall()]
        return []

    def get_schema_version(self) -> int:
        """Get current schema version."""
        from .migrations import MigrationManager

        mgr = MigrationManager(self._raw_conn)
        return mgr.get_current_version()

    def get_migration_status(self) -> dict:
        """Get migration status including pending migrations."""
        from .migrations import MigrationManager

        mgr = MigrationManager(self._raw_conn)
        return mgr.status()

    def close(self):
        """Close database connection."""
        self.session.close()
        if hasattr(self, "_sa_conn"):
            self._sa_conn.close()
        self.engine.dispose()

    @contextmanager
    def transaction(self):
        """Context manager for ORM transactions with rollback on failure."""
        try:
            yield self.session
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
