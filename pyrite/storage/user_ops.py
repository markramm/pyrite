"""
User, repo, workspace, and version history operations.

Mixin class for collaboration-related data access.
"""

from datetime import UTC, datetime
from typing import Any


class UserOpsMixin:
    """User management, repo registration, workspace, and entry versions."""

    # =========================================================================
    # Users
    # =========================================================================

    def upsert_user(
        self,
        github_login: str,
        github_id: int,
        display_name: str = "",
        avatar_url: str = "",
        email: str = "",
    ) -> dict[str, Any]:
        """Insert or update a user. Returns user dict."""
        now = datetime.now(UTC).isoformat()
        self._raw_conn.execute(
            """
            INSERT INTO user (github_login, github_id, display_name,
                              avatar_url, email, last_seen)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(github_id) DO UPDATE SET
                github_login = excluded.github_login,
                display_name = excluded.display_name,
                avatar_url = excluded.avatar_url,
                email = excluded.email,
                last_seen = excluded.last_seen
            """,
            (github_login, github_id, display_name, avatar_url, email, now),
        )
        self._raw_conn.commit()
        row = self._raw_conn.execute(
            "SELECT * FROM user WHERE github_id = ?", (github_id,)
        ).fetchone()
        return dict(row) if row else {}

    def get_user(
        self,
        github_login: str | None = None,
        github_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Get user by login or ID."""
        if github_id is not None:
            row = self._raw_conn.execute(
                "SELECT * FROM user WHERE github_id = ?", (github_id,)
            ).fetchone()
        elif github_login is not None:
            row = self._raw_conn.execute(
                "SELECT * FROM user WHERE github_login = ?", (github_login,)
            ).fetchone()
        else:
            return None
        return dict(row) if row else None

    def get_local_user(self) -> dict[str, Any]:
        """Get the sentinel 'local' user."""
        row = self._raw_conn.execute("SELECT * FROM user WHERE github_id = 0").fetchone()
        if row:
            return dict(row)
        return self.upsert_user("local", 0, "Local User")

    # =========================================================================
    # Repos
    # =========================================================================

    def register_repo(
        self,
        name: str,
        local_path: str,
        remote_url: str | None = None,
        owner: str | None = None,
        visibility: str = "public",
        default_branch: str = "main",
        upstream_repo_id: int | None = None,
        is_fork: bool = False,
    ) -> dict[str, Any]:
        """Register a repo in the database. Returns repo dict."""
        self._raw_conn.execute(
            """
            INSERT INTO repo (name, local_path, remote_url, owner, visibility,
                              default_branch, upstream_repo_id, is_fork)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                local_path = excluded.local_path,
                remote_url = COALESCE(excluded.remote_url, repo.remote_url),
                owner = COALESCE(excluded.owner, repo.owner),
                visibility = excluded.visibility,
                default_branch = excluded.default_branch,
                upstream_repo_id = COALESCE(
                    excluded.upstream_repo_id, repo.upstream_repo_id
                ),
                is_fork = excluded.is_fork
            """,
            (
                name,
                local_path,
                remote_url,
                owner,
                visibility,
                default_branch,
                upstream_repo_id,
                1 if is_fork else 0,
            ),
        )
        self._raw_conn.commit()
        row = self._raw_conn.execute("SELECT * FROM repo WHERE name = ?", (name,)).fetchone()
        return dict(row) if row else {}

    def get_repo(
        self,
        name: str | None = None,
        repo_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Get repo by name or ID."""
        if repo_id is not None:
            row = self._raw_conn.execute("SELECT * FROM repo WHERE id = ?", (repo_id,)).fetchone()
        elif name is not None:
            row = self._raw_conn.execute("SELECT * FROM repo WHERE name = ?", (name,)).fetchone()
        else:
            return None
        return dict(row) if row else None

    def list_repos(self) -> list[dict[str, Any]]:
        """List all repos."""
        rows = self._raw_conn.execute("SELECT * FROM repo ORDER BY name").fetchall()
        return [dict(r) for r in rows]

    def delete_repo(self, name: str) -> bool:
        """Delete a repo by name. Returns True if deleted."""
        result = self._raw_conn.execute("DELETE FROM repo WHERE name = ?", (name,))
        self._raw_conn.commit()
        return result.rowcount > 0

    def update_repo_synced(self, name: str, commit_hash: str) -> None:
        """Update repo's last synced commit and timestamp."""
        now = datetime.now(UTC).isoformat()
        self._raw_conn.execute(
            "UPDATE repo SET last_synced_commit = ?, last_synced = ? " "WHERE name = ?",
            (commit_hash, now, name),
        )
        self._raw_conn.commit()

    # =========================================================================
    # Workspace
    # =========================================================================

    def add_workspace_repo(self, user_id: int, repo_id: int, role: str = "subscriber") -> None:
        """Add a repo to a user's workspace."""
        self._raw_conn.execute(
            """
            INSERT OR IGNORE INTO workspace_repo (user_id, repo_id, role)
            VALUES (?, ?, ?)
            """,
            (user_id, repo_id, role),
        )
        self._raw_conn.commit()

    def remove_workspace_repo(self, user_id: int, repo_id: int) -> bool:
        """Remove a repo from a user's workspace."""
        result = self._raw_conn.execute(
            "DELETE FROM workspace_repo WHERE user_id = ? AND repo_id = ?",
            (user_id, repo_id),
        )
        self._raw_conn.commit()
        return result.rowcount > 0

    def get_workspace_repos(self, user_id: int) -> list[dict[str, Any]]:
        """Get repos in a user's workspace."""
        rows = self._raw_conn.execute(
            """
            SELECT r.*, wr.role, wr.auto_sync, wr.added_at
            FROM repo r
            JOIN workspace_repo wr ON r.id = wr.repo_id
            WHERE wr.user_id = ?
            ORDER BY r.name
            """,
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    # =========================================================================
    # Entry versions
    # =========================================================================

    def upsert_entry_version(
        self,
        entry_id: str,
        kb_name: str,
        commit_hash: str,
        author_name: str,
        author_email: str,
        commit_date: str,
        message: str = "",
        diff_summary: str = "",
        change_type: str = "modified",
        author_github_login: str | None = None,
    ) -> None:
        """Insert an entry version (from git log). Skips if commit already recorded."""
        self._raw_conn.execute(
            """
            INSERT OR IGNORE INTO entry_version
                (entry_id, kb_name, commit_hash, author_name, author_email,
                 author_github_login, commit_date, message, diff_summary,
                 change_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry_id,
                kb_name,
                commit_hash,
                author_name,
                author_email,
                author_github_login,
                commit_date,
                message,
                diff_summary,
                change_type,
            ),
        )
        self._raw_conn.commit()

    def get_entry_versions(
        self, entry_id: str, kb_name: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get version history for an entry."""
        rows = self._raw_conn.execute(
            """
            SELECT * FROM entry_version
            WHERE entry_id = ? AND kb_name = ?
            ORDER BY commit_date DESC
            LIMIT ?
            """,
            (entry_id, kb_name, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_contributors(self, kb_name: str | None = None) -> list[dict[str, Any]]:
        """Get contributors (from entry_version) with commit counts."""
        if kb_name:
            rows = self._raw_conn.execute(
                """
                SELECT author_name, author_email, author_github_login,
                       COUNT(DISTINCT commit_hash) as commits,
                       MAX(commit_date) as last_commit
                FROM entry_version
                WHERE kb_name = ?
                GROUP BY author_email
                ORDER BY commits DESC
                """,
                (kb_name,),
            ).fetchall()
        else:
            rows = self._raw_conn.execute("""
                SELECT author_name, author_email, author_github_login,
                       COUNT(DISTINCT commit_hash) as commits,
                       MAX(commit_date) as last_commit
                FROM entry_version
                GROUP BY author_email
                ORDER BY commits DESC
            """).fetchall()
        return [dict(r) for r in rows]
