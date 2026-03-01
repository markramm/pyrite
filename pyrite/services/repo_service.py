"""
Repo Service — High-level repository management.

Orchestrates GitService + DB + Config to implement subscribe, fork, sync,
and unsubscribe workflows. This is the main entry point for collaboration
operations.
"""

import logging
from pathlib import Path

from pyrite.utils.yaml import load_yaml_file

from ..config import (
    KBConfig,
    KBType,
    PyriteConfig,
    auto_discover_kbs,
    save_config,
)
from ..github_auth import get_github_token
from ..storage.database import PyriteDB
from ..storage.index import IndexManager
from .git_service import GitService
from .user_service import UserService

logger = logging.getLogger(__name__)


class RepoService:
    """High-level repo operations for collaboration workflows."""

    def __init__(
        self,
        config: PyriteConfig,
        db: PyriteDB,
        git_service: GitService | None = None,
        user_service: UserService | None = None,
    ):
        self.config = config
        self.db = db
        self.git = git_service or GitService()
        self.user_service = user_service or UserService(db)

    def subscribe(
        self,
        remote_url: str,
        name: str | None = None,
        branch: str = "main",
    ) -> dict:
        """
        Subscribe to a remote repo: clone, discover KBs, index with attribution.

        Returns dict with repo info and discovered KBs.
        """
        parsed = GitService.parse_github_url(remote_url)
        if not parsed:
            return {"success": False, "error": "Could not parse GitHub URL"}

        owner, repo_name = parsed
        full_name = name or f"{owner}/{repo_name}"

        # Determine workspace path
        workspace_path = self.config.settings.workspace_path / owner / repo_name
        if workspace_path.exists():
            return {"success": False, "error": f"Path already exists: {workspace_path}"}

        workspace_path.parent.mkdir(parents=True, exist_ok=True)

        # Clone (shallow for subscriptions)
        token = get_github_token()
        success, msg = GitService.clone(
            remote_url, workspace_path, branch=branch, depth=1, token=token
        )
        if not success:
            return {"success": False, "error": msg}

        # Discover KBs
        discovered_kbs = self.discover_kbs(workspace_path)

        # Register repo in DB
        head = GitService.get_head_commit(workspace_path)
        repo_row = self.db.register_repo(
            name=full_name,
            local_path=str(workspace_path),
            remote_url=remote_url,
            owner=owner,
            visibility="public",
            default_branch=branch,
        )
        self.db.update_repo_synced(full_name, head)

        # Register KBs in config and DB
        index_mgr = IndexManager(self.db, self.config)
        kb_names = []
        for kb_config in discovered_kbs:
            # Set repo association
            kb_config.repo = full_name
            kb_config.repo_subpath = str(kb_config.path.relative_to(workspace_path))
            kb_config.read_only = True  # Subscriptions are read-only

            # Add to config if not already present
            if not self.config.get_kb(kb_config.name):
                self.config.add_kb(kb_config)

            # Register in DB with repo_id
            self.db.register_kb(
                name=kb_config.name,
                kb_type=kb_config.kb_type,
                path=str(kb_config.path),
                description=kb_config.description,
            )
            # Link KB to repo in DB
            if repo_row.get("id"):
                self.db.link_kb_to_repo(kb_config.name, repo_row["id"], kb_config.repo_subpath)

            # Index with attribution
            index_mgr.index_with_attribution(kb_config.name, self.git)
            kb_names.append(kb_config.name)

        # Add to user's workspace
        user = self.user_service.get_current_user()
        if repo_row.get("id"):
            self.db.add_workspace_repo(user["id"], repo_row["id"], "subscriber")

        save_config(self.config)

        return {
            "success": True,
            "repo": full_name,
            "path": str(workspace_path),
            "kbs": kb_names,
            "entries_indexed": sum(self.db.count_entries(kb) for kb in kb_names),
        }

    def fork_and_subscribe(self, remote_url: str) -> dict:
        """
        Fork a repo on GitHub, then subscribe to the fork.

        Returns dict with fork info.
        """
        parsed = GitService.parse_github_url(remote_url)
        if not parsed:
            return {"success": False, "error": "Could not parse GitHub URL"}

        owner, repo_name = parsed
        token = get_github_token()
        if not token:
            return {"success": False, "error": "GitHub authentication required for forking"}

        # Fork on GitHub
        success, fork_data = GitService.fork_repo(owner, repo_name, token)
        if not success:
            return {"success": False, "error": fork_data.get("error", "Fork failed")}

        fork_clone_url = fork_data.get("clone_url", "")
        fork_full_name = fork_data.get("full_name", "")

        if not fork_clone_url:
            return {"success": False, "error": "Fork created but no clone URL returned"}

        # Subscribe to our fork (full clone, not shallow — we need history)
        result = self._clone_and_register(fork_clone_url, fork_full_name, depth=None)
        if not result["success"]:
            return result

        # Set upstream relationship
        upstream_repo = self.db.get_repo(name=f"{owner}/{repo_name}")
        fork_repo = self.db.get_repo(name=fork_full_name)
        if upstream_repo and fork_repo:
            self.db.set_repo_upstream(fork_repo["id"], upstream_repo["id"])

        # Add upstream remote
        workspace_path = Path(result["path"])
        GitService.add_remote(workspace_path, "upstream", remote_url)

        # Update workspace role
        user = self.user_service.get_current_user()
        if fork_repo:
            self.db.update_workspace_role(user["id"], fork_repo["id"], "contributor")

        result["is_fork"] = True
        result["upstream"] = f"{owner}/{repo_name}"
        return result

    def sync(self, repo_name: str | None = None) -> dict:
        """
        Sync repo(s): pull, detect changes, re-index changed files with attribution.

        Returns dict with sync results.
        """
        if repo_name:
            repos = [self.db.get_repo(name=repo_name)]
            repos = [r for r in repos if r]
        else:
            repos = self.db.list_repos()

        if not repos:
            return {"success": False, "error": "No repos found"}

        results = {}
        token = get_github_token()

        for repo in repos:
            name = repo["name"]
            local_path = Path(repo["local_path"])

            if not local_path.exists():
                results[name] = {"success": False, "error": "Path does not exist"}
                continue

            old_head = repo.get("last_synced_commit") or GitService.get_head_commit(local_path)

            # Pull
            success, msg = GitService.pull(local_path, token=token)
            if not success:
                results[name] = {"success": False, "error": msg}
                continue

            new_head = GitService.get_head_commit(local_path)

            if old_head == new_head:
                results[name] = {"success": True, "message": "Already up to date", "changes": 0}
                continue

            # Get changed files
            changed = GitService.get_changed_files(local_path, since_commit=old_head)

            # Re-index changed files per KB
            index_mgr = IndexManager(self.db, self.config)
            total_reindexed = 0

            # Find KBs in this repo
            kb_rows = self.db.get_kbs_for_repo(repo["id"])

            for kb_row in kb_rows:
                kb_name = kb_row["name"]
                kb_config = self.config.get_kb(kb_name)
                if not kb_config:
                    continue

                # Filter changed files that belong to this KB's subpath
                subpath = kb_row["repo_subpath"] or ""
                kb_changed = [f for f in changed if f.startswith(subpath)] if subpath else changed

                if kb_changed:
                    count = index_mgr.index_with_attribution(
                        kb_name, self.git, since_commit=old_head
                    )
                    total_reindexed += count

            # Update synced state
            self.db.update_repo_synced(name, new_head)

            results[name] = {
                "success": True,
                "message": msg,
                "changes": len(changed),
                "reindexed": total_reindexed,
            }

        return {"success": True, "repos": results}

    def unsubscribe(self, repo_name: str, delete_files: bool = False) -> dict:
        """Remove a repo from the workspace."""
        repo = self.db.get_repo(name=repo_name)
        if not repo:
            return {"success": False, "error": f"Repo '{repo_name}' not found"}

        # Remove KBs associated with this repo
        kb_rows = self.db.get_kbs_for_repo(repo["id"])
        for kb_row in kb_rows:
            self.config.remove_kb(kb_row["name"])
            self.db.unregister_kb(kb_row["name"])

        # Remove workspace membership
        user = self.user_service.get_current_user()
        self.db.remove_workspace_repo(user["id"], repo["id"])

        # Remove repo from DB
        self.db.delete_repo(repo_name)

        # Optionally delete files
        if delete_files:
            import shutil

            local_path = Path(repo["local_path"])
            if local_path.exists():
                shutil.rmtree(local_path)

        save_config(self.config)

        return {
            "success": True,
            "repo": repo_name,
            "kbs_removed": [r["name"] for r in kb_rows],
            "files_deleted": delete_files,
        }

    def list_repos(self, user_id: int | None = None) -> list[dict]:
        """List repos, optionally filtered by user workspace."""
        if user_id is not None:
            return self.db.get_workspace_repos(user_id)
        return self.db.list_repos()

    def get_repo_status(self, repo_name: str) -> dict:
        """Get detailed status for a repo."""
        repo = self.db.get_repo(name=repo_name)
        if not repo:
            return {"success": False, "error": f"Repo '{repo_name}' not found"}

        local_path = Path(repo["local_path"])
        status = dict(repo)

        if local_path.exists():
            status["current_branch"] = GitService.get_current_branch(local_path)
            status["head_commit"] = GitService.get_head_commit(local_path)
            status["is_git_repo"] = GitService.is_git_repo(local_path)
        else:
            status["path_exists"] = False

        # Count KBs and entries
        kb_rows = self.db.get_kbs_for_repo(repo["id"])
        status["kb_count"] = len(kb_rows)
        status["kb_names"] = [r["name"] for r in kb_rows]

        total_entries = sum(self.db.count_entries(r["name"]) for r in kb_rows)
        status["total_entries"] = total_entries

        # Contributors
        contributors = []
        for kb_row in kb_rows:
            contributors.extend(self.db.get_contributors(kb_row["name"]))
        status["contributors"] = contributors

        return status

    def discover_kbs(self, repo_path: Path) -> list[KBConfig]:
        """Discover KBs in a repository path."""
        # First try auto_discover_kbs (looks for kb.yaml)
        discovered = auto_discover_kbs([repo_path])

        if not discovered:
            # Fallback: check if the repo root itself looks like a KB
            kb_yaml = repo_path / "kb.yaml"
            if kb_yaml.exists():
                try:
                    data = load_yaml_file(kb_yaml)
                    kb = KBConfig(
                        name=data.get("name", repo_path.name),
                        path=repo_path,
                        kb_type=KBType(data.get("kb_type", "research")),
                        description=data.get("description", ""),
                    )
                    kb.load_kb_yaml()
                    discovered.append(kb)
                except Exception as e:
                    logger.warning("Could not parse %s: %s", kb_yaml, e)

        return discovered

    def _clone_and_register(
        self,
        clone_url: str,
        full_name: str,
        depth: int | None = 1,
        branch: str = "main",
    ) -> dict:
        """Internal helper: clone and register a repo + KBs."""
        parsed = GitService.parse_github_url(clone_url)
        if not parsed:
            return {"success": False, "error": "Could not parse clone URL"}

        owner, repo_name = parsed
        workspace_path = self.config.settings.workspace_path / owner / repo_name

        if workspace_path.exists():
            return {"success": False, "error": f"Path already exists: {workspace_path}"}

        workspace_path.parent.mkdir(parents=True, exist_ok=True)
        token = get_github_token()

        success, msg = GitService.clone(
            clone_url, workspace_path, branch=branch, depth=depth, token=token
        )
        if not success:
            return {"success": False, "error": msg}

        # Discover and register
        discovered_kbs = self.discover_kbs(workspace_path)
        head = GitService.get_head_commit(workspace_path)

        repo_row = self.db.register_repo(
            name=full_name,
            local_path=str(workspace_path),
            remote_url=clone_url,
            owner=owner,
            default_branch=branch,
        )
        self.db.update_repo_synced(full_name, head)

        index_mgr = IndexManager(self.db, self.config)
        kb_names = []
        for kb_config in discovered_kbs:
            kb_config.repo = full_name
            kb_config.repo_subpath = str(kb_config.path.relative_to(workspace_path))
            if not self.config.get_kb(kb_config.name):
                self.config.add_kb(kb_config)
            self.db.register_kb(
                name=kb_config.name,
                kb_type=kb_config.kb_type,
                path=str(kb_config.path),
                description=kb_config.description,
            )
            if repo_row.get("id"):
                self.db.link_kb_to_repo(kb_config.name, repo_row["id"], kb_config.repo_subpath)
            index_mgr.index_with_attribution(kb_config.name, self.git)
            kb_names.append(kb_config.name)

        user = self.user_service.get_current_user()
        if repo_row.get("id"):
            self.db.add_workspace_repo(user["id"], repo_row["id"], "contributor")

        save_config(self.config)

        return {
            "success": True,
            "repo": full_name,
            "path": str(workspace_path),
            "kbs": kb_names,
        }
