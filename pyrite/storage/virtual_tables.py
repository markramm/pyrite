"""
Virtual Table Adapter for SQLite-specific FTS5 and sqlite-vec tables.

These virtual tables have no ORM equivalent, so we manage them via raw SQL.
In a future Postgres migration, this module gets a counterpart using
tsvector + pgvector.
"""

FTS_SCHEMA_SQL = """
-- Full-text search index
CREATE VIRTUAL TABLE IF NOT EXISTS entry_fts USING fts5(
    id,
    kb_name,
    entry_type,
    title,
    body,
    summary,
    location,
    content='entry',
    content_rowid='rowid',
    tokenize='porter unicode61'
);

-- FTS triggers for automatic sync
CREATE TRIGGER IF NOT EXISTS entry_ai AFTER INSERT ON entry BEGIN
    INSERT INTO entry_fts(rowid, id, kb_name, entry_type, title, body, summary, location)
    VALUES (new.rowid, new.id, new.kb_name, new.entry_type, new.title,
            COALESCE(new.body, ''), COALESCE(new.summary, ''), COALESCE(new.location, ''));
END;

CREATE TRIGGER IF NOT EXISTS entry_ad AFTER DELETE ON entry BEGIN
    INSERT INTO entry_fts(entry_fts, rowid, id, kb_name, entry_type, title, body, summary, location)
    VALUES('delete', old.rowid, old.id, old.kb_name, old.entry_type, old.title,
           COALESCE(old.body, ''), COALESCE(old.summary, ''), COALESCE(old.location, ''));
END;

CREATE TRIGGER IF NOT EXISTS entry_au AFTER UPDATE ON entry BEGIN
    INSERT INTO entry_fts(entry_fts, rowid, id, kb_name, entry_type, title, body, summary, location)
    VALUES('delete', old.rowid, old.id, old.kb_name, old.entry_type, old.title,
           COALESCE(old.body, ''), COALESCE(old.summary, ''), COALESCE(old.location, ''));
    INSERT INTO entry_fts(rowid, id, kb_name, entry_type, title, body, summary, location)
    VALUES (new.rowid, new.id, new.kb_name, new.entry_type, new.title,
            COALESCE(new.body, ''), COALESCE(new.summary, ''), COALESCE(new.location, ''));
END;
"""

VEC_SCHEMA_SQL = "CREATE VIRTUAL TABLE IF NOT EXISTS vec_entry USING vec0(embedding float[384])"


def create_fts_tables(connection) -> None:
    """Create FTS5 virtual table and sync triggers on a raw sqlite3 connection."""
    connection.executescript(FTS_SCHEMA_SQL)
    connection.commit()


def create_vec_table(connection) -> None:
    """Create sqlite-vec virtual table on a raw sqlite3 connection."""
    existing = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='vec_entry'"
    ).fetchone()
    if not existing:
        connection.execute(VEC_SCHEMA_SQL)
        connection.commit()
