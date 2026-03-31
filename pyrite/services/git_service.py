"""
Git Service — Low-level git operations via subprocess.

Pure git plumbing wrapper with no DB or config dependencies.
Token handling is done by injecting credentials into URLs or environment.
"""

import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class GitService:
    """Low-level git operations via subprocess."""

    @staticmethod
    def clone(
        remote_url: str,
        local_path: Path,
        branch: str = "main",
        depth: int | None = 1,
        token: str | None = None,
    ) -> tuple[bool, str]:
        """
        Clone a repository.

        Args:
            remote_url: HTTPS or SSH URL
            local_path: Where to clone to
            branch: Branch to clone
            depth: Shallow clone depth (None for full clone)
            token: GitHub OAuth token for private repos

        Returns:
            (success, message)
        """
        url = GitService._inject_token(remote_url, token)

        cmd = ["git", "clone", "--branch", branch]
        if depth is not None:
            cmd.extend(["--depth", str(depth)])
        cmd.extend([url, str(local_path)])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                return True, f"Cloned to {local_path}"
            error = GitService._sanitize_output(result.stderr, token)
            return False, f"Clone failed: {error}"
        except subprocess.TimeoutExpired:
            return False, "Clone timed out"
        except Exception as e:
            return False, f"Clone failed: {e}"

    @staticmethod
    def pull(local_path: Path, token: str | None = None) -> tuple[bool, str]:
        """Pull latest changes. Returns (success, message)."""
        env = os.environ.copy()
        if token:
            env["GIT_ASKPASS"] = "echo"
            env["GIT_USERNAME"] = "oauth2"
            env["GIT_PASSWORD"] = token

        try:
            result = subprocess.run(
                ["git", "pull"],
                cwd=str(local_path),
                capture_output=True,
                text=True,
                env=env,
                timeout=60,
            )
            if result.returncode == 0:
                return True, result.stdout.strip() or "Already up to date"
            error = GitService._sanitize_output(result.stderr, token)
            return False, f"Pull failed: {error}"
        except subprocess.TimeoutExpired:
            return False, "Pull timed out"
        except Exception as e:
            return False, f"Pull failed: {e}"

    @staticmethod
    def get_remote_url(local_path: Path) -> str | None:
        """Get the 'origin' remote URL."""
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=str(local_path),
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            logger.warning("Failed to get remote URL for %s", local_path, exc_info=True)
        return None

    @staticmethod
    def get_current_branch(local_path: Path) -> str:
        """Get the current branch name."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(local_path),
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            logger.warning("Failed to get current branch for %s", local_path, exc_info=True)
        return "main"

    @staticmethod
    def get_head_commit(local_path: Path) -> str:
        """Get HEAD commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(local_path),
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            logger.warning("Failed to get HEAD commit for %s", local_path, exc_info=True)
        return ""

    @staticmethod
    def get_file_log(
        local_path: Path,
        file_path: str,
        since_commit: str | None = None,
    ) -> list[dict]:
        """
        Get git log for a specific file.

        Returns list of dicts with: hash, author_name, author_email, date, message
        """
        cmd = [
            "git",
            "log",
            "--follow",
            "--format=%H|%an|%ae|%aI|%s",
            "--",
            file_path,
        ]
        if since_commit:
            cmd.insert(2, f"{since_commit}..HEAD")

        try:
            result = subprocess.run(
                cmd,
                cwd=str(local_path),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return []

            entries = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("|", 4)
                if len(parts) < 5:
                    continue
                entries.append(
                    {
                        "hash": parts[0],
                        "author_name": parts[1],
                        "author_email": parts[2],
                        "date": parts[3],
                        "message": parts[4],
                    }
                )
            return entries
        except Exception:
            logger.warning("Failed to parse git log for %s", file_path, exc_info=True)
            return []

    @staticmethod
    def get_changed_files(
        local_path: Path,
        since_commit: str | None = None,
    ) -> list[str]:
        """
        Get list of changed .md files since a commit.

        If since_commit is None, lists all tracked .md files.
        """
        if since_commit:
            cmd = [
                "git",
                "diff",
                "--name-only",
                f"{since_commit}..HEAD",
                "--",
                "*.md",
            ]
        else:
            cmd = ["git", "ls-files", "*.md"]

        try:
            result = subprocess.run(
                cmd,
                cwd=str(local_path),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return [f for f in result.stdout.strip().split("\n") if f]
        except Exception:
            logger.warning("Failed to get changed files for %s", local_path, exc_info=True)
        return []

    @staticmethod
    def is_git_repo(path: Path) -> bool:
        """Check if a path is inside a git repository."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=str(path),
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except Exception:
            logger.debug("Not a git repo: %s", path)
            return False

    @staticmethod
    def add_remote(local_path: Path, name: str, url: str) -> tuple[bool, str]:
        """Add a git remote."""
        try:
            result = subprocess.run(
                ["git", "remote", "add", name, url],
                cwd=str(local_path),
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return True, f"Added remote '{name}'"
            return False, result.stderr.strip()
        except Exception as e:
            return False, str(e)

    @staticmethod
    def fork_repo(owner: str, repo: str, token: str) -> tuple[bool, dict]:
        """
        Fork a repo on GitHub via the API.

        Returns (success, response_dict).
        """
        try:
            import httpx
        except ImportError:
            return False, {"error": "httpx required for GitHub API operations"}

        try:
            with httpx.Client() as client:
                response = client.post(
                    f"https://api.github.com/repos/{owner}/{repo}/forks",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github+json",
                    },
                    timeout=30,
                )
                if response.status_code in (200, 202):
                    return True, response.json()
                return False, {
                    "error": f"GitHub API error: {response.status_code}",
                    "message": response.text,
                }
        except Exception as e:
            return False, {"error": str(e)}

    @staticmethod
    def create_pull_request(
        owner: str,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str,
        token: str,
    ) -> tuple[bool, dict]:
        """
        Create a pull request on GitHub via the API.

        Args:
            owner: Repo owner (upstream)
            repo: Repo name (upstream)
            title: PR title
            body: PR body/description
            head: Head branch (e.g. "user:branch" for cross-fork PRs)
            base: Base branch to merge into
            token: GitHub OAuth token

        Returns:
            (success, response_dict)
        """
        try:
            import httpx
        except ImportError:
            return False, {"error": "httpx required for GitHub API operations"}

        try:
            with httpx.Client() as client:
                response = client.post(
                    f"https://api.github.com/repos/{owner}/{repo}/pulls",
                    json={
                        "title": title,
                        "body": body,
                        "head": head,
                        "base": base,
                    },
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github+json",
                    },
                    timeout=30,
                )
                if response.status_code in (200, 201):
                    data = response.json()
                    return True, {
                        "pr_url": data.get("html_url"),
                        "pr_number": data.get("number"),
                    }
                return False, {
                    "error": f"GitHub API error: {response.status_code}",
                    "message": response.text,
                }
        except Exception as e:
            return False, {"error": str(e)}

    @staticmethod
    def parse_github_url(url: str) -> tuple[str, str] | None:
        """
        Parse a GitHub URL into (owner, repo).

        Handles:
          https://github.com/owner/repo
          https://github.com/owner/repo.git
          git@github.com:owner/repo.git
        """
        url = url.rstrip("/")
        if url.endswith(".git"):
            url = url[:-4]

        if "github.com/" in url:
            parts = url.split("github.com/")[-1].split("/")
            if len(parts) >= 2:
                return parts[0], parts[1]
        elif "github.com:" in url:
            parts = url.split("github.com:")[-1].split("/")
            if len(parts) >= 2:
                return parts[0], parts[1]
        return None

    @staticmethod
    def commit(
        local_path: Path,
        message: str,
        paths: list[str] | None = None,
        sign_off: bool = False,
    ) -> tuple[bool, dict]:
        """
        Stage and commit changes in a git repository.

        Args:
            local_path: Path to the git repository
            message: Commit message
            paths: Specific file paths to stage (stages all if None)
            sign_off: Add Signed-off-by line

        Returns:
            (success, result_dict) where result_dict contains
            commit_hash, files_changed, message on success
            or error on failure.
        """
        if not GitService.is_git_repo(local_path):
            return False, {"error": "Not a git repository"}

        try:
            # Stage files
            if paths:
                for p in paths:
                    result = subprocess.run(
                        ["git", "add", p],
                        cwd=str(local_path),
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode != 0:
                        return False, {"error": f"Failed to stage {p}: {result.stderr.strip()}"}
            else:
                result = subprocess.run(
                    ["git", "add", "-A"],
                    cwd=str(local_path),
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    return False, {"error": f"Failed to stage: {result.stderr.strip()}"}

            # Check if there's anything to commit
            status_result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=str(local_path),
                capture_output=True,
                text=True,
            )
            staged_files = [f for f in status_result.stdout.strip().split("\n") if f]
            if not staged_files:
                return False, {"error": "No changes to commit"}

            # Build commit command
            cmd = ["git", "commit", "-m", message]
            if sign_off:
                cmd.append("--signoff")

            result = subprocess.run(
                cmd,
                cwd=str(local_path),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return False, {"error": f"Commit failed: {result.stderr.strip()}"}

            # Get the commit hash
            commit_hash = GitService.get_head_commit(local_path)

            return True, {
                "commit_hash": commit_hash,
                "files_changed": len(staged_files),
                "files": staged_files,
                "message": message,
            }
        except subprocess.TimeoutExpired:
            return False, {"error": "Commit timed out"}
        except Exception as e:
            return False, {"error": str(e)}

    @staticmethod
    def push(
        local_path: Path,
        remote: str = "origin",
        branch: str | None = None,
        token: str | None = None,
    ) -> tuple[bool, str]:
        """
        Push commits to a remote repository.

        Args:
            local_path: Path to the git repository
            remote: Remote name (default: origin)
            branch: Branch to push (default: current branch)
            token: OAuth token for authentication

        Returns:
            (success, message)
        """
        if not GitService.is_git_repo(local_path):
            return False, "Not a git repository"

        if branch is None:
            branch = GitService.get_current_branch(local_path)

        env = os.environ.copy()
        if token:
            env["GIT_ASKPASS"] = "echo"
            env["GIT_USERNAME"] = "oauth2"
            env["GIT_PASSWORD"] = token

        try:
            result = subprocess.run(
                ["git", "push", "-u", remote, branch],
                cwd=str(local_path),
                capture_output=True,
                text=True,
                env=env,
                timeout=60,
            )
            if result.returncode == 0:
                return True, result.stderr.strip() or result.stdout.strip() or "Pushed successfully"
            error = GitService._sanitize_output(result.stderr, token)
            return False, f"Push failed: {error}"
        except subprocess.TimeoutExpired:
            return False, "Push timed out"
        except Exception as e:
            return False, f"Push failed: {e}"

    @staticmethod
    def get_status(local_path: Path) -> dict:
        """
        Get git working tree status.

        Returns dict with: clean (bool), staged (list), unstaged (list), untracked (list)
        """
        result = {"clean": True, "staged": [], "unstaged": [], "untracked": []}

        if not GitService.is_git_repo(local_path):
            return result

        try:
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(local_path),
                capture_output=True,
                text=True,
            )
            if status.returncode != 0:
                return result

            for line in status.stdout.rstrip("\n").split("\n"):
                if not line:
                    continue
                if len(line) < 4:
                    continue
                result["clean"] = False
                index_status = line[0]
                work_status = line[1]
                filename = line[3:]

                if index_status == "?":
                    result["untracked"].append(filename)
                elif index_status != " ":
                    result["staged"].append(filename)
                if work_status not in (" ", "?"):
                    result["unstaged"].append(filename)

            return result
        except Exception:
            logger.warning("Failed to get git status for repo", exc_info=True)
            return result

    @staticmethod
    def _inject_token(url: str, token: str | None) -> str:
        """Inject OAuth token into HTTPS URL for authentication."""
        if not token:
            return url
        if url.startswith("git@github.com:"):
            url = url.replace("git@github.com:", "https://github.com/")
            if not url.endswith(".git"):
                url += ".git"
        if "github.com" in url and url.startswith("https://"):
            return url.replace("https://", f"https://oauth2:{token}@")
        return url

    @staticmethod
    def _sanitize_output(output: str, token: str | None) -> str:
        """Remove tokens from error messages."""
        if token and token in output:
            return output.replace(token, "***")
        return output

    # =========================================================================
    # Git worktree operations
    # =========================================================================

    @staticmethod
    def worktree_add(
        repo_path: Path, worktree_path: Path, branch: str
    ) -> tuple[bool, str]:
        """Create a git worktree with a new branch.

        Args:
            repo_path: Path to the main git repository.
            worktree_path: Path where the worktree will be created.
            branch: Branch name for the worktree (created if not exists).

        Returns:
            (success, message) tuple.
        """
        worktree_path = Path(worktree_path)
        worktree_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            # Try creating with new branch first
            result = subprocess.run(
                ["git", "worktree", "add", str(worktree_path), "-b", branch],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return True, f"Created worktree at {worktree_path} on branch {branch}"
            # Branch may already exist — try without -b
            result = subprocess.run(
                ["git", "worktree", "add", str(worktree_path), branch],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return True, f"Created worktree at {worktree_path} on existing branch {branch}"
            return False, result.stderr.strip()
        except Exception as e:
            return False, str(e)

    @staticmethod
    def worktree_list(repo_path: Path) -> list[dict[str, str]]:
        """List all git worktrees for a repository.

        Returns list of dicts with 'worktree', 'HEAD', 'branch' keys.
        """
        try:
            result = subprocess.run(
                ["git", "worktree", "list", "--porcelain"],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                return []
            worktrees = []
            current: dict[str, str] = {}
            for line in result.stdout.splitlines():
                if line.startswith("worktree "):
                    if current:
                        worktrees.append(current)
                    current = {"worktree": line[9:]}
                elif line.startswith("HEAD "):
                    current["HEAD"] = line[5:]
                elif line.startswith("branch "):
                    current["branch"] = line[7:]
                elif line == "bare":
                    current["bare"] = "true"
                elif line == "detached":
                    current["detached"] = "true"
            if current:
                worktrees.append(current)
            return worktrees
        except Exception:
            return []

    @staticmethod
    def worktree_remove(
        repo_path: Path, worktree_path: Path, force: bool = False
    ) -> tuple[bool, str]:
        """Remove a git worktree."""
        cmd = ["git", "worktree", "remove", str(worktree_path)]
        if force:
            cmd.append("--force")
        try:
            result = subprocess.run(
                cmd,
                cwd=str(repo_path),
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return True, f"Removed worktree at {worktree_path}"
            return False, result.stderr.strip()
        except Exception as e:
            return False, str(e)

    @staticmethod
    def merge_branch(
        repo_path: Path, branch: str, into: str = "main"
    ) -> tuple[bool, str]:
        """Merge a branch into another (typically main).

        Performs checkout + merge in the repo_path working directory.
        Returns (success, message). On conflict, returns (False, conflict_info).
        """
        try:
            # Checkout target branch
            result = subprocess.run(
                ["git", "checkout", into],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                return False, f"Failed to checkout {into}: {result.stderr.strip()}"

            # Merge
            result = subprocess.run(
                ["git", "merge", branch, "--no-edit"],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return True, f"Merged {branch} into {into}"

            # Merge conflict — abort and report
            conflict_info = result.stdout.strip()
            subprocess.run(
                ["git", "merge", "--abort"],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
            )
            return False, f"Merge conflict: {conflict_info}"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def diff_branches(
        repo_path: Path, base: str, head: str, stat_only: bool = False
    ) -> tuple[bool, str]:
        """Get diff between two branches.

        Args:
            repo_path: Path to the git repository.
            base: Base branch (e.g., "main").
            head: Head branch (e.g., "user/alice").
            stat_only: If True, return --stat summary only.

        Returns:
            (success, diff_output) tuple.
        """
        cmd = ["git", "diff", f"{base}...{head}"]
        if stat_only:
            cmd.append("--stat")
        try:
            result = subprocess.run(
                cmd,
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return True, result.stdout
            return False, result.stderr.strip()
        except subprocess.TimeoutExpired:
            return False, "Diff timed out"
        except Exception as e:
            return False, str(e)
