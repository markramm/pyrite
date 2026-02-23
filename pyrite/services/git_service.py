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
            pass
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
            pass
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
            pass
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
            pass
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
