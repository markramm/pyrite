"""
User, repo, workspace, and version history operations.

Mixin class for collaboration-related data access.
Uses ORM session for all writes.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func

from .models import EntryVersion, Repo, User, WorkspaceRepo


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
        existing = self.session.query(User).filter_by(github_id=github_id).first()
        if existing:
            existing.github_login = github_login
            existing.display_name = display_name
            existing.avatar_url = avatar_url
            existing.email = email
            existing.last_seen = now
        else:
            user = User(
                github_login=github_login,
                github_id=github_id,
                display_name=display_name,
                avatar_url=avatar_url,
                email=email,
                last_seen=now,
            )
            self.session.add(user)
        self.session.commit()

        user_obj = self.session.query(User).filter_by(github_id=github_id).first()
        return self._user_to_dict(user_obj) if user_obj else {}

    def _user_to_dict(self, user: User) -> dict[str, Any]:
        """Convert User ORM object to dict."""
        return {
            "id": user.id,
            "github_login": user.github_login,
            "github_id": user.github_id,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "email": user.email,
            "created_at": user.created_at,
            "last_seen": user.last_seen,
        }

    def get_user(
        self,
        github_login: str | None = None,
        github_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Get user by login or ID."""
        if github_id is not None:
            user = self.session.query(User).filter_by(github_id=github_id).first()
        elif github_login is not None:
            user = self.session.query(User).filter_by(github_login=github_login).first()
        else:
            return None
        return self._user_to_dict(user) if user else None

    def get_local_user(self) -> dict[str, Any]:
        """Get the sentinel 'local' user."""
        user = self.session.query(User).filter_by(github_id=0).first()
        if user:
            return self._user_to_dict(user)
        return self.upsert_user("local", 0, "Local User")

    # =========================================================================
    # Repos
    # =========================================================================

    def _repo_to_dict(self, repo: Repo) -> dict[str, Any]:
        """Convert Repo ORM object to dict."""
        return {
            "id": repo.id,
            "name": repo.name,
            "local_path": repo.local_path,
            "remote_url": repo.remote_url,
            "owner": repo.owner,
            "visibility": repo.visibility,
            "default_branch": repo.default_branch,
            "upstream_repo_id": repo.upstream_repo_id,
            "is_fork": repo.is_fork,
            "last_synced_commit": repo.last_synced_commit,
            "last_synced": repo.last_synced,
            "created_at": repo.created_at,
        }

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
        existing = self.session.query(Repo).filter_by(name=name).first()
        if existing:
            existing.local_path = local_path
            if remote_url is not None:
                existing.remote_url = remote_url
            if owner is not None:
                existing.owner = owner
            existing.visibility = visibility
            existing.default_branch = default_branch
            if upstream_repo_id is not None:
                existing.upstream_repo_id = upstream_repo_id
            existing.is_fork = 1 if is_fork else 0
        else:
            repo = Repo(
                name=name,
                local_path=local_path,
                remote_url=remote_url,
                owner=owner,
                visibility=visibility,
                default_branch=default_branch,
                upstream_repo_id=upstream_repo_id,
                is_fork=1 if is_fork else 0,
            )
            self.session.add(repo)
        self.session.commit()

        repo_obj = self.session.query(Repo).filter_by(name=name).first()
        return self._repo_to_dict(repo_obj) if repo_obj else {}

    def get_repo(
        self,
        name: str | None = None,
        repo_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Get repo by name or ID."""
        if repo_id is not None:
            repo = self.session.query(Repo).filter_by(id=repo_id).first()
        elif name is not None:
            repo = self.session.query(Repo).filter_by(name=name).first()
        else:
            return None
        return self._repo_to_dict(repo) if repo else None

    def list_repos(self) -> list[dict[str, Any]]:
        """List all repos."""
        repos = self.session.query(Repo).order_by(Repo.name).all()
        return [self._repo_to_dict(r) for r in repos]

    def delete_repo(self, name: str) -> bool:
        """Delete a repo by name. Returns True if deleted."""
        count = self.session.query(Repo).filter_by(name=name).delete()
        self.session.commit()
        return count > 0

    def update_repo_synced(self, name: str, commit_hash: str) -> None:
        """Update repo's last synced commit and timestamp."""
        now = datetime.now(UTC).isoformat()
        repo = self.session.query(Repo).filter_by(name=name).first()
        if repo:
            repo.last_synced_commit = commit_hash
            repo.last_synced = now
            self.session.commit()

    # =========================================================================
    # Workspace
    # =========================================================================

    def add_workspace_repo(self, user_id: int, repo_id: int, role: str = "subscriber") -> None:
        """Add a repo to a user's workspace."""
        existing = self.session.query(WorkspaceRepo).filter_by(
            user_id=user_id, repo_id=repo_id
        ).first()
        if not existing:
            wr = WorkspaceRepo(user_id=user_id, repo_id=repo_id, role=role)
            self.session.add(wr)
            self.session.commit()

    def remove_workspace_repo(self, user_id: int, repo_id: int) -> bool:
        """Remove a repo from a user's workspace."""
        count = self.session.query(WorkspaceRepo).filter_by(
            user_id=user_id, repo_id=repo_id
        ).delete()
        self.session.commit()
        return count > 0

    def get_workspace_repos(self, user_id: int) -> list[dict[str, Any]]:
        """Get repos in a user's workspace."""
        results = (
            self.session.query(Repo, WorkspaceRepo.role, WorkspaceRepo.auto_sync, WorkspaceRepo.added_at)
            .join(WorkspaceRepo, Repo.id == WorkspaceRepo.repo_id)
            .filter(WorkspaceRepo.user_id == user_id)
            .order_by(Repo.name)
            .all()
        )
        workspace_repos = []
        for repo, role, auto_sync, added_at in results:
            d = self._repo_to_dict(repo)
            d["role"] = role
            d["auto_sync"] = auto_sync
            d["added_at"] = added_at
            workspace_repos.append(d)
        return workspace_repos

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
        existing = self.session.query(EntryVersion).filter_by(
            entry_id=entry_id, kb_name=kb_name, commit_hash=commit_hash
        ).first()
        if not existing:
            version = EntryVersion(
                entry_id=entry_id,
                kb_name=kb_name,
                commit_hash=commit_hash,
                author_name=author_name,
                author_email=author_email,
                author_github_login=author_github_login,
                commit_date=commit_date,
                message=message,
                diff_summary=diff_summary,
                change_type=change_type,
            )
            self.session.add(version)
            self.session.commit()

    def get_entry_versions(
        self, entry_id: str, kb_name: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get version history for an entry."""
        versions = (
            self.session.query(EntryVersion)
            .filter_by(entry_id=entry_id, kb_name=kb_name)
            .order_by(EntryVersion.commit_date.desc())
            .limit(limit)
            .all()
        )
        return [self._version_to_dict(v) for v in versions]

    def _version_to_dict(self, v: EntryVersion) -> dict[str, Any]:
        """Convert EntryVersion ORM object to dict."""
        return {
            "id": v.id,
            "entry_id": v.entry_id,
            "kb_name": v.kb_name,
            "commit_hash": v.commit_hash,
            "author_name": v.author_name,
            "author_email": v.author_email,
            "author_github_login": v.author_github_login,
            "commit_date": v.commit_date,
            "message": v.message,
            "diff_summary": v.diff_summary,
            "change_type": v.change_type,
        }

    def get_contributors(self, kb_name: str | None = None) -> list[dict[str, Any]]:
        """Get contributors (from entry_version) with commit counts."""
        query = self.session.query(
            EntryVersion.author_name,
            EntryVersion.author_email,
            EntryVersion.author_github_login,
            func.count(func.distinct(EntryVersion.commit_hash)).label("commits"),
            func.max(EntryVersion.commit_date).label("last_commit"),
        )

        if kb_name:
            query = query.filter(EntryVersion.kb_name == kb_name)

        query = query.group_by(EntryVersion.author_email).order_by(
            func.count(func.distinct(EntryVersion.commit_hash)).desc()
        )

        rows = query.all()
        return [
            {
                "author_name": r[0],
                "author_email": r[1],
                "author_github_login": r[2],
                "commits": r[3],
                "last_commit": r[4],
            }
            for r in rows
        ]
