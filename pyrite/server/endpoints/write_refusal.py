"""REST adapters for the KBService write pipeline's refusals (#378).

The service decides every create/update refusal; these only translate: a
refusal into an ``HTTPException`` with its own ``error_code``, and the raw
request body into the ADR-0034 check the pydantic models cannot see.
"""

from fastapi import HTTPException, Request

from ...exceptions import ValidationError
from ...services.body_bounds import ensure_not_truncated


def refusal_http(exc: ValidationError) -> HTTPException:
    """Map a write-pipeline refusal to REST, keeping its own code.

    The service decides; this only picks the status. `ENTRY_EXISTS` is a
    conflict (409); every other refusal is a bad request (400). Never
    retryable: the same request fails the same way.
    """
    code = getattr(exc, "error_code", None) or "VALIDATION_FAILED"
    detail: dict = {"code": code, "message": str(exc), "retryable": False}
    suggestion = getattr(exc, "suggestion", None)
    if suggestion:
        detail["hint"] = suggestion
    declared = getattr(exc, "declared_types", None)
    if declared is not None:
        detail["declared_types"] = declared
        detail.setdefault(
            "hint",
            f"Use an entry_type in [{', '.join(declared)}], or send allow_undeclared: true.",
        )
    return HTTPException(status_code=409 if code == "ENTRY_EXISTS" else 400, detail=detail)


async def refuses_truncated_body(request: Request) -> None:
    """ADR-0034 rule 2 on the REST JSON write endpoints' *raw* body.

    A FastAPI dependency, because the pydantic request models drop every key
    they do not declare -- a `body_truncated` nested under any other key would
    never reach the service, while the body it marks would. This reads the raw
    JSON and applies the service's own check (``ensure_not_truncated``) at any
    depth, before the handler runs.

    A request whose payload is not JSON (a multipart upload, an empty body) is
    left alone: there is nothing to inspect, and `/entries/import` hands each
    parsed record to the pipeline, which checks it.

    **The JSON test mirrors FastAPI's own**, deliberately. FastAPI parses a
    body whenever the media type's maintype is `application` and its subtype
    is `json` or ends `+json`, lower-cased by `email.message` first
    (`fastapi/routing.py::get_request_handler`). A narrower test here does not
    make the guard conservative -- it makes it *bypassable*, because the
    handler still runs and still writes.
    """
    media_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if not (media_type == "application/json" or media_type.endswith("+json")):
        return
    try:
        payload = await request.json()
    except Exception:
        return

    # PATCH writes one named field, so it is a body write only when that field
    # IS the body -- and then `value`, not a `body` key, holds the body.
    if isinstance(payload, dict) and payload.get("field") is not None:
        if payload.get("field") != "body":
            return
        payload = {**payload, "body": payload.get("value")}

    try:
        ensure_not_truncated(payload)
    except ValidationError as e:
        raise refusal_http(e) from e
