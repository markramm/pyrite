"""Repo management endpoints — subscribe, fork, sync, unsubscribe, list."""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request

from ...config import PyriteConfig
from ...services.git_service import GitService
from ...services.repo_service import RepoService
from ...storage.database import PyriteDB
from ..api import (
    TIER_LEVELS,
    get_config,
    get_db,
    get_readable_kbs,
    get_repo_service,
    requires_tier,
    resolve_effective_kb_role,
)
from ..schemas import ForkRequest, PRRequest, RepoInfo, RepoListResponse, SubscribeRequest

logger = logging.getLogger(__name__)


# The public error codes a repo endpoint may put in `detail.code`. A service
# result's `error_code` is echoed only if it is one of these — an unrecognised
# value is an internal identifier, and naming internals to a caller is the same
# class of disclosure as naming paths. Documented in docs/json-contracts.md.
_PUBLIC_ERROR_CODES = frozenset(
    {
        "REPO_NOT_FOUND",
        "AUTH_REQUIRED",
        "BRANCH_NOT_FOUND",
        "PATH_EXISTS",
        "CLONE_TIMEOUT",
        "CLONE_FAILED",
        "INVALID_REQUEST",
        "SUBSCRIBE_FAILED",
        "FORK_FAILED",
        "SYNC_FAILED",
        "UNSUBSCRIBE_FAILED",
        "PR_FAILED",
        "GITHUB_NOT_CONNECTED",
        "KB_NAME_CONFLICT",
        "INVALID_KB_NAME",
        "REPO_NAME_CONFLICT",
    }
)


def _sanitized_message(raw: object, token: str | None, context: str) -> str:
    """Redact a service error string, logging the unredacted original."""
    text = str(raw)
    message = GitService.sanitize_error(text, token)
    if message != text:
        logger.warning("%s (unredacted): %s", context, text)
    return message or "Unknown error"


def _service_token(svc: object) -> str | None:
    """The GitHub token this service would have injected into a remote URL, so
    it can be redacted out of whatever git wrote about that URL."""
    token = getattr(svc, "_github_token", None)
    return token if isinstance(token, str) and token else None


def _error_detail(result: dict, default_code: str, svc: object = None) -> dict:
    """Build a 400 detail body from a service result without disclosing the
    server's filesystem layout.

    A service `error` string may still be raw git stderr (an operator-facing
    message with absolute paths in it), so every one of them goes through
    `GitService.sanitize_error` on the way out — CodeQL py/stack-trace-exposure
    #51 (subscribe), #52 (fork), #53 (pr). The raw text is logged, not sent.
    """
    message = _sanitized_message(
        result.get("error", "Unknown error"), _service_token(svc), default_code
    )
    code = result.get("error_code")
    return {
        "code": code if code in _PUBLIC_ERROR_CODES else default_code,
        "message": message,
    }


def _sanitize_sync_result(result: dict, svc: object) -> dict:
    """`RepoService.sync` reports per-repo outcomes nested under `repos`, and
    a failed repo's `error` is whatever `GitService.pull` returned — now git's
    own words, which can carry an absolute path. That nesting means a 200 body
    never reaches `_error_detail`, so redact it here."""
    repos = result.get("repos")
    if not isinstance(repos, dict):
        return result
    token = _service_token(svc)
    cleaned = dict(result)
    cleaned["repos"] = {
        name: (
            {**entry, "error": _sanitized_message(entry["error"], token, "SYNC_FAILED")}
            if isinstance(entry, dict) and entry.get("error") is not None
            else entry
        )
        for name, entry in repos.items()
    }
    return cleaned


router = APIRouter(
    tags=["Repos"],
    dependencies=[Depends(requires_tier("write"))],
)


def _requires_github_token(svc: RepoService = Depends(get_repo_service)) -> None:
    """400 unless the caller has a connected GitHub account.

    A dependency rather than an inline check so that, on `/pr`, it runs before
    `_repo_kb_guard`: a caller with no token gets this answer whether or not
    the repository exists or is readable, exactly as before the guard.
    """
    if not getattr(svc, "_github_token", None):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "GITHUB_NOT_CONNECTED",
                "message": "Connect your GitHub account first",
            },
        )


def _repo_kb_names(db: PyriteDB, repo: dict) -> list[str]:
    """The KBs a repository holds, as recorded when it was subscribed."""
    return [row["name"] for row in db.get_kbs_for_repo(repo["id"])]


def _repo_is_readable(kb_names: list[str], readable: set[str] | None) -> bool:
    """A repository is readable when every KB it holds is (`None`: unscoped)."""
    return readable is None or all(kb in readable for kb in kb_names)


def _repo_kb_guard(tier: str, missing_status: int, missing_code: str, missing_error: str):
    """Dependency: the caller needs `tier` on **every** KB the repository holds.

    A repository is a container of KBs, so the per-KB rule applies to it
    through its contents -- the same helpers the KB routes use
    (`get_readable_kbs`, `resolve_effective_kb_role`), no second rule:

    - a KB the caller may not read makes the repository answer **exactly as a
      repository that does not exist** answers on this route (`missing_*` is
      that answer, as the service would produce it), because its existence
      and the names of its KBs are private too;
    - a readable KB on which the caller lacks `tier` is a 403.

    A repository that does not exist passes through to the handler, which
    answers as it always has. One that holds no KBs has nothing to scope and
    is governed by the router's global `write` tier alone.
    """

    async def _check(
        name: str,
        request: Request,
        readable: set[str] | None = Depends(get_readable_kbs),
        config: PyriteConfig = Depends(get_config),
        db: PyriteDB = Depends(get_db),
        svc: RepoService = Depends(get_repo_service),
    ) -> None:
        repo = db.get_repo(name=name)
        if not repo:
            return
        kb_names = _repo_kb_names(db, repo)

        if not _repo_is_readable(kb_names, readable):
            raise HTTPException(
                status_code=missing_status,
                detail=_error_detail({"error": missing_error.format(name=name)}, missing_code, svc),
            )

        if tier == "read":
            return
        for kb in kb_names:
            role = await resolve_effective_kb_role(request, config, db, kb)
            if role is None or TIER_LEVELS.get(role, -1) < TIER_LEVELS[tier]:
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient permissions on KB '{kb}': requires '{tier}' tier",
                )

    return _check


# The answer each route gives for a repository that does not exist -- what
# `RepoService` returns for an unknown name -- which is also what a caller
# gets for one whose KBs it may not read.
_GUARD_GET = _repo_kb_guard("read", 404, "REPO_NOT_FOUND", "Repo '{name}' not found")
_GUARD_SYNC = _repo_kb_guard("write", 400, "SYNC_FAILED", "No repos found")
_GUARD_PR = _repo_kb_guard("write", 400, "PR_FAILED", "Repo '{name}' not found")
# Admin, not write: unsubscribing removes the repository's KBs from the
# instance, which is what `DELETE /api/kbs/{name}` does at admin tier.
_GUARD_DELETE = _repo_kb_guard("admin", 400, "UNSUBSCRIBE_FAILED", "Repo '{name}' not found")


def _relativize_path(svc: object, value: str) -> str:
    """Narrow an absolute server path to a form that discloses nothing about
    the server's filesystem layout or usernames, for the HTTP boundary only.

    Issue #195, the success-path twin of #161: `RepoInfo.local_path` and the
    `path` key in `subscribe`/`fork` success bodies are public REST response
    shape (an external consumer we cannot see may read them), so the field
    stays populated rather than being dropped — but relative to the
    workspace root (``owner/repo_name``), same as
    ``workspace_path = self.config.settings.workspace_path / owner / repo_name``
    in `RepoService`.

    Internal callers (repo_service.py, config.py) read `local_path` off the
    DB row or the service's own dict directly — never through this function —
    and keep receiving absolute paths, which they resolve against and pass to
    git. Only what crosses the HTTP boundary is narrowed here.

    A path that is not under the configured workspace root (e.g. legacy data
    from a moved workspace) cannot be made relative without still disclosing
    layout, so it is replaced by an opaque marker instead of raising or
    leaking the absolute value.
    """
    try:
        workspace_path = svc.config.settings.workspace_path
        return str(Path(value).relative_to(workspace_path))
    except (ValueError, AttributeError, TypeError, OSError):
        logger.warning("Path %s could not be relativized to the workspace root", value)
        return "<path>"


def _repo_dict_to_info(repo: dict, svc: object) -> RepoInfo:
    """Convert a repo dict to RepoInfo schema."""
    local_path = repo.get("local_path", "")
    return RepoInfo(
        id=repo.get("id", 0),
        name=repo.get("name", ""),
        local_path=_relativize_path(svc, local_path) if local_path else local_path,
        remote_url=repo.get("remote_url"),
        owner=repo.get("owner"),
        visibility=repo.get("visibility", "public"),
        default_branch=repo.get("default_branch", "main"),
        is_fork=bool(repo.get("is_fork", False)),
        last_synced=repo.get("last_synced"),
        last_synced_commit=repo.get("last_synced_commit"),
        kb_count=repo.get("kb_count", 0),
        kb_names=repo.get("kb_names", []),
        total_entries=repo.get("total_entries", 0),
    )


@router.get("/repos", response_model=RepoListResponse)
def list_repos(
    request: Request,
    svc: RepoService = Depends(get_repo_service),
    readable: set[str] | None = Depends(get_readable_kbs),
    db: PyriteDB = Depends(get_db),
):
    """List the subscribed/forked repos whose KBs the caller may read.

    A repository holding a KB the caller may not read is left out, exactly
    as if it did not exist -- the rule `GET /repos/{name}` applies.
    """
    repos = svc.list_repos()
    if readable is not None:
        repos = [r for r in repos if _repo_is_readable(_repo_kb_names(db, r), readable)]
    return RepoListResponse(repos=[_repo_dict_to_info(r, svc) for r in repos])


@router.get("/repos/{name:path}", dependencies=[Depends(_GUARD_GET)])
def get_repo(
    name: str,
    request: Request,
    svc: RepoService = Depends(get_repo_service),
):
    """Get detailed status for a repo."""
    result = svc.get_repo_status(name)
    if result.get("success", True) is not False and "error" not in result:
        if "local_path" in result:
            result = {**result, "local_path": _relativize_path(svc, result["local_path"])}
        return result
    if result.get("error"):
        raise HTTPException(
            status_code=404,
            detail=_error_detail(result, "REPO_NOT_FOUND", svc),
        )
    return result


@router.post("/repos/subscribe")
def subscribe_to_repo(
    body: SubscribeRequest,
    request: Request,
    svc: RepoService = Depends(get_repo_service),
):
    """Subscribe to a remote repo — clone, discover KBs, index."""
    result = svc.subscribe(body.remote_url, name=body.name, branch=body.branch)
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=_error_detail(result, "SUBSCRIBE_FAILED", svc),
        )
    if "path" in result:
        result = {**result, "path": _relativize_path(svc, result["path"])}
    return result


@router.post("/repos/fork")
def fork_repo(
    body: ForkRequest,
    request: Request,
    svc: RepoService = Depends(get_repo_service),
):
    """Fork a repo on GitHub and subscribe to the fork."""
    if not getattr(svc, "_github_token", None):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "GITHUB_NOT_CONNECTED",
                "message": "Connect your GitHub account first (Settings > Knowledge Bases > Connect GitHub)",
            },
        )
    result = svc.fork_and_subscribe(body.remote_url)
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=_error_detail(result, "FORK_FAILED", svc),
        )
    if "path" in result:
        result = {**result, "path": _relativize_path(svc, result["path"])}
    return result


@router.post("/repos/{name:path}/sync", dependencies=[Depends(_GUARD_SYNC)])
def sync_repo(
    name: str,
    request: Request,
    svc: RepoService = Depends(get_repo_service),
):
    """Sync a repo — pull, detect changes, re-index."""
    result = svc.sync(repo_name=name)
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=_error_detail(result, "SYNC_FAILED", svc),
        )
    # Per-repo failures ride along in a 200 body; redact them too.
    return _sanitize_sync_result(result, svc)


@router.delete("/repos/{name:path}", dependencies=[Depends(_GUARD_DELETE)])
def unsubscribe_repo(
    name: str,
    request: Request,
    delete_files: bool = False,
    svc: RepoService = Depends(get_repo_service),
):
    """Unsubscribe from a repo — remove from workspace, optionally delete files."""
    result = svc.unsubscribe(name, delete_files=delete_files)
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=_error_detail(result, "UNSUBSCRIBE_FAILED", svc),
        )
    return result


@router.get("/github/repos")
def list_github_repos(
    request: Request,
    svc: RepoService = Depends(get_repo_service),
):
    """List GitHub repos accessible by the user's stored token (for export picker)."""
    token = getattr(svc, "_github_token", None)
    if not token:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "GITHUB_NOT_CONNECTED",
                "message": "Connect your GitHub account first",
            },
        )

    try:
        import httpx

        with httpx.Client() as client:
            resp = client.get(
                "https://api.github.com/user/repos",
                params={"per_page": 100, "sort": "updated", "affiliation": "owner"},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                },
                timeout=15,
            )
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail={
                        "code": "GITHUB_API_ERROR",
                        "message": f"GitHub API returned {resp.status_code}",
                    },
                )
            repos_data = resp.json()
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=502,
            detail={"code": "GITHUB_API_ERROR", "message": str(e)},
        )

    repos = [
        {
            "full_name": r["full_name"],
            "description": r.get("description"),
            "html_url": r["html_url"],
            "clone_url": r["clone_url"],
            "private": r.get("private", False),
            "fork": r.get("fork", False),
        }
        for r in repos_data
    ]
    return {"repos": repos}


@router.post(
    "/repos/{name:path}/pr",
    # Order matters: the token check answers first, as it did before the guard.
    dependencies=[Depends(_requires_github_token), Depends(_GUARD_PR)],
)
def create_pull_request(
    name: str,
    body: PRRequest,
    request: Request,
    svc: RepoService = Depends(get_repo_service),
):
    """Create a pull request from a fork to its upstream."""
    result = svc.create_pr(name, body.title, body.body, branch=body.branch)
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=_error_detail(result, "PR_FAILED", svc),
        )
    return result
