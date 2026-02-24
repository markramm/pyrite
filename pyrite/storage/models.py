"""
SQLAlchemy ORM Models for pyrite

Declarative models for standard tables. Virtual tables (FTS5, sqlite-vec)
are handled separately in virtual_tables.py since they have no ORM equivalent.
"""

from sqlalchemy import (
    Column,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class KB(Base):
    __tablename__ = "kb"

    name = Column(String, primary_key=True)
    kb_type = Column(String, nullable=False)
    path = Column(String, nullable=False)
    description = Column(Text)
    last_indexed = Column(String)
    entry_count = Column(Integer, default=0)

    # Phase 7: repo association
    repo_id = Column(Integer, ForeignKey("repo.id", ondelete="SET NULL"), nullable=True)
    repo_subpath = Column(String, default="")

    entries = relationship("Entry", back_populates="kb_rel", cascade="all, delete-orphan")
    repo_rel = relationship("Repo", back_populates="knowledge_bases")


class Entry(Base):
    __tablename__ = "entry"

    id = Column(String, primary_key=True)
    kb_name = Column(
        String, ForeignKey("kb.name", ondelete="CASCADE"), primary_key=True, nullable=False
    )
    entry_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    body = Column(Text)
    summary = Column(Text)
    file_path = Column(String)

    # Common indexed fields
    date = Column(String)
    importance = Column(Integer)
    status = Column(String)
    location = Column(String)

    # Extension fields (JSON) — attribute named extra_data to avoid SQLAlchemy reserved 'metadata'
    extra_data = Column("metadata", Text, default="{}")

    # Timestamps
    created_at = Column(String)
    updated_at = Column(String)
    indexed_at = Column(String, server_default="CURRENT_TIMESTAMP")

    # Attribution
    created_by = Column(String, nullable=True)
    modified_by = Column(String, nullable=True)

    # Relationships
    kb_rel = relationship("KB", back_populates="entries")
    tags = relationship("EntryTag", back_populates="entry", cascade="all, delete-orphan")
    sources = relationship("Source", back_populates="entry", cascade="all, delete-orphan")
    outgoing_links = relationship(
        "Link", back_populates="source_entry", cascade="all, delete-orphan"
    )
    versions = relationship("EntryVersion", back_populates="entry", cascade="all, delete-orphan")


class Tag(Base):
    __tablename__ = "tag"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False, index=True)

    entry_tags = relationship("EntryTag", back_populates="tag")


class EntryTag(Base):
    __tablename__ = "entry_tag"

    entry_id = Column(String, nullable=False, primary_key=True)
    kb_name = Column(String, nullable=False, primary_key=True)
    tag_id = Column(
        Integer, ForeignKey("tag.id", ondelete="CASCADE"), nullable=False, primary_key=True
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["entry_id", "kb_name"],
            ["entry.id", "entry.kb_name"],
            ondelete="CASCADE",
        ),
        Index("idx_entry_tag_entry", "entry_id", "kb_name"),
        Index("idx_entry_tag_tag", "tag_id"),
    )

    entry = relationship("Entry", back_populates="tags")
    tag = relationship("Tag", back_populates="entry_tags")


class Link(Base):
    __tablename__ = "link"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(String, nullable=False)
    source_kb = Column(String, nullable=False)
    target_id = Column(String, nullable=False)
    target_kb = Column(String, nullable=False)
    relation = Column(String, nullable=False)
    inverse_relation = Column(String, nullable=False)
    note = Column(Text)
    created_at = Column(String, server_default="CURRENT_TIMESTAMP")

    __table_args__ = (
        ForeignKeyConstraint(
            ["source_id", "source_kb"],
            ["entry.id", "entry.kb_name"],
            ondelete="CASCADE",
        ),
        Index("idx_link_source", "source_id", "source_kb"),
        Index("idx_link_target", "target_id", "target_kb"),
        Index("idx_link_relation", "relation"),
    )

    source_entry = relationship("Entry", back_populates="outgoing_links")


class EntryRef(Base):
    __tablename__ = "entry_ref"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(String, nullable=False)
    source_kb = Column(String, nullable=False)
    target_id = Column(String, nullable=False)
    target_kb = Column(String, nullable=False)
    field_name = Column(String, nullable=False)
    target_type = Column(String)  # from schema constraint

    __table_args__ = (
        ForeignKeyConstraint(
            ["source_id", "source_kb"],
            ["entry.id", "entry.kb_name"],
            ondelete="CASCADE",
        ),
        Index("idx_entry_ref_source", "source_id", "source_kb"),
        Index("idx_entry_ref_target", "target_id", "target_kb"),
        Index("idx_entry_ref_field", "field_name"),
    )


class Source(Base):
    __tablename__ = "source"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_id = Column(String, nullable=False)
    kb_name = Column(String, nullable=False)
    title = Column(String, nullable=False)
    url = Column(String)
    outlet = Column(String)
    date = Column(String)
    verified = Column(Integer, default=0)

    __table_args__ = (
        ForeignKeyConstraint(
            ["entry_id", "kb_name"],
            ["entry.id", "entry.kb_name"],
            ondelete="CASCADE",
        ),
        Index("idx_source_entry", "entry_id", "kb_name"),
        Index("idx_source_url", "url"),
    )

    entry = relationship("Entry", back_populates="sources")


# =========================================================================
# Phase 7: Collaboration Models
# =========================================================================


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    github_login = Column(String, unique=True, nullable=False, index=True)
    github_id = Column(Integer, unique=True, nullable=False)
    display_name = Column(String)
    avatar_url = Column(String)
    email = Column(String)
    created_at = Column(String, server_default="CURRENT_TIMESTAMP")
    last_seen = Column(String)

    workspace_repos = relationship(
        "WorkspaceRepo", back_populates="user", cascade="all, delete-orphan"
    )


class Repo(Base):
    __tablename__ = "repo"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False, index=True)
    local_path = Column(String, nullable=False)
    remote_url = Column(String)
    owner = Column(String)
    visibility = Column(String, default="public")
    default_branch = Column(String, default="main")
    upstream_repo_id = Column(Integer, ForeignKey("repo.id", ondelete="SET NULL"), nullable=True)
    is_fork = Column(Integer, default=0)
    last_synced_commit = Column(String)
    last_synced = Column(String)
    created_at = Column(String, server_default="CURRENT_TIMESTAMP")

    upstream = relationship("Repo", remote_side=[id], backref="forks")
    knowledge_bases = relationship("KB", back_populates="repo_rel")
    workspace_entries = relationship(
        "WorkspaceRepo", back_populates="repo", cascade="all, delete-orphan"
    )


class WorkspaceRepo(Base):
    __tablename__ = "workspace_repo"

    user_id = Column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), primary_key=True, nullable=False
    )
    repo_id = Column(
        Integer, ForeignKey("repo.id", ondelete="CASCADE"), primary_key=True, nullable=False
    )
    added_at = Column(String, server_default="CURRENT_TIMESTAMP")
    role = Column(String, default="subscriber")
    auto_sync = Column(Integer, default=1)
    sync_interval = Column(Integer, default=3600)

    user = relationship("User", back_populates="workspace_repos")
    repo = relationship("Repo", back_populates="workspace_entries")


class EntryVersion(Base):
    __tablename__ = "entry_version"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_id = Column(String, nullable=False)
    kb_name = Column(String, nullable=False)
    commit_hash = Column(String(40), nullable=False, index=True)
    author_name = Column(String)
    author_email = Column(String)
    author_github_login = Column(String, index=True)
    commit_date = Column(String, nullable=False, index=True)
    message = Column(Text)
    diff_summary = Column(Text)
    change_type = Column(String)

    __table_args__ = (
        ForeignKeyConstraint(
            ["entry_id", "kb_name"],
            ["entry.id", "entry.kb_name"],
            ondelete="CASCADE",
        ),
        Index("idx_entry_version_entry", "entry_id", "kb_name"),
    )

    entry = relationship("Entry", back_populates="versions")


# =========================================================================
# Starred/Pinned Entries (engagement-tier, SQLite only per ADR-0003)
# =========================================================================


class StarredEntry(Base):
    __tablename__ = "starred_entry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_id = Column(String, nullable=False)
    kb_name = Column(String, nullable=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint("entry_id", "kb_name", name="uq_starred_entry"),
        Index("idx_starred_entry_kb", "kb_name"),
        Index("idx_starred_entry_sort", "sort_order"),
    )


# =========================================================================
# Settings
# =========================================================================


class Setting(Base):
    __tablename__ = "setting"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(Text)
    updated_at = Column(String, server_default="CURRENT_TIMESTAMP")
