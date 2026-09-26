"""REST's adapter to the access policy (ADR-0037 §2, #383).

The rule lives in `pyrite/services/access_policy.py`. This module holds only
the FastAPI side of asking it: turning what `api.verify_api_key` recorded on
the request into a `Principal`. The dependencies in `api.py`
(`requires_tier`, `requires_kb_tier`, `requires_kb_read`, `get_readable_kbs`)
build the principal here and ask the policy; ADR-0037 theme 3a adds the one
`authorize(...)` dependency that replaces them.
"""

from __future__ import annotations

from starlette.requests import HTTPConnection

from ..services.access_policy import Principal


def get_principal(request: HTTPConnection) -> Principal | None:
    """The caller, as `verify_api_key` resolved it; None when it did not.

    `verify_api_key` sets exactly one of: a session user (`auth_user`), the
    anonymous visitor (`anonymous`), or neither -- an operator API key, or
    auth disabled -- with the role in `api_role`. Usable as a FastAPI
    dependency.
    """
    state = request.state
    role = getattr(state, "api_role", None)
    if role is None:
        return None
    auth_user = getattr(state, "auth_user", None)
    if auth_user:
        return Principal.user(auth_user["id"], role)
    if getattr(state, "anonymous", False):
        return Principal.anonymous(role)
    return Principal.from_api_key(role)
