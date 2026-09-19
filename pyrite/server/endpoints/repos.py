"""Repo management endpoints — subscribe, fork, sync, unsubscribe, list."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from ...services.git_service import GitService
from ...services.repo_service import RepoService
from ..api import get_repo_service, requires_tier
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


def _repo_dict_to_info(repo: dict) -> RepoInfo:
    """Convert a repo dict to RepoInfo schema."""
    return RepoInfo(
        id=repo.get("id", 0),
        name=repo.get("name", ""),
        local_path=repo.get("local_path", ""),
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
):
    """List all subscribed/forked repos."""
    repos = svc.list_repos()
    return RepoListResponse(repos=[_repo_dict_to_info(r) for r in repos])


@router.get("/repos/{name:path}")
def get_repo(
    name: str,
    request: Request,
    svc: RepoService = Depends(get_repo_service),
):
    """Get detailed status for a repo."""
    result = svc.get_repo_status(name)
    if result.get("success", True) is not False and "error" not in result:
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
    return result


@router.post("/repos/{name:path}/sync")
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


@router.delete("/repos/{name:path}")
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


@router.post("/repos/{name:path}/pr")
def create_pull_request(
    name: str,
    body: PRRequest,
    request: Request,
    svc: RepoService = Depends(get_repo_service),
):
    """Create a pull request from a fork to its upstream."""
    token = getattr(svc, "_github_token", None)
    if not token:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "GITHUB_NOT_CONNECTED",
                "message": "Connect your GitHub account first",
            },
        )

    result = svc.create_pr(name, body.title, body.body, branch=body.branch)
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=_error_detail(result, "PR_FAILED", svc),
        )
    return result
