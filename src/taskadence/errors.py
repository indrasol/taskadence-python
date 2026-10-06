"""Exceptions. Every error the API returns is `application/problem+json` (RFC 9457); each problem `type` is a class.

    APIError                              anything this SDK raises about a request
    ├── APIConnectionError                the request never got an HTTP answer (DNS, refused, reset)
    │   └── APITimeoutError
    ├── ResponseValidationError           a 2xx whose body does not match the spec this SDK was generated from
    ├── BlobUploadError                   a direct upload's PUT to storage failed (.status .code; the URL is redacted)
    └── TaskadenceError                    an HTTP error answer: .status .type .title .detail .request_id .errors
        ├── BadRequestError (400)         ├── InvalidParameterError   urn:taskadence:problem:invalid-parameter
        │                                 └── IdempotencyKeyInvalidError
        ├── AuthenticationError (401)     ├── TokenInvalidError / TokenExpiredError / TokenRevokedError
        ├── ForbiddenError (403)          ├── InsufficientScopeError  (.required_scope)
        │                                 └── TestTokenReadOnlyError
        ├── NotFoundError (404)
        ├── ConflictError (409)           └── IdempotencyKeyInFlightError
        ├── PreconditionFailedError (412)
        ├── UnprocessableEntityError (422) ├── ValidationError, IdempotencyKeyReusedError, UrlRefusedError
        │                                 └── InvalidValueError   422 invalid-parameter: also an InvalidParameterError
        ├── RateLimitedError (429)        (.retry_after)
        ├── InternalError (5xx)
        └── TokenPolicyError              403 or 422: the organization's token policy

A problem type from a server older than the rename (`_brand.LEGACY_URN_PREFIX`) maps exactly like its
`urn:taskadence:problem:…` twin. `about:blank` problems (and non-problem bodies) map by status.
 The mapping mirrors the TasKadence app's own reader
(`apiService.ts`): the message is `detail`, else `message`, else the reason phrase; a `detail` that is a list (a
422's per-field errors) is joined.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from email.utils import parsedate_to_datetime
from http import HTTPStatus
from typing import Any

import httpx

from ._brand import URN_PREFIX, problem_slug

URN = URN_PREFIX


class APIError(Exception):
    """Base class of every exception this SDK raises about a request."""


class APIConnectionError(APIError):
    """The request never got an HTTP response (DNS, connection refused or reset, TLS)."""


class APITimeoutError(APIConnectionError):
    """The request timed out (connect, read or write)."""


class ResponseValidationError(APIError):
    """A 2xx response whose body does not match the models generated from `spec/openapi.public.json` — typically an
    SDK older than the API (a new enum value, a required field that became optional). `.body` holds the raw JSON."""

    def __init__(self, message: str, *, operation: str, body: Any) -> None:
        super().__init__(message)
        self.operation = operation
        self.body = body


class BlobUploadError(APIError):
    """A direct upload's PUT to Azure Blob Storage failed after its retries (or was refused: an expired upload URL is
    403 `AuthenticationFailed`). Nothing was attached; call the upload again for a fresh URL. The message and every
    attribute carry the URL without its query string (the signature), never the signed URL itself."""

    def __init__(self, message: str, *, status: int | None = None, code: str | None = None, url: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.url = url


class TaskadenceError(APIError):
    """An HTTP error answered by the TasKadence API (a problem+json body, or a plain one mapped the same way)."""

    status: int
    type: str
    title: str
    detail: str
    request_id: str | None
    errors: list[dict[str, Any]]

    def __init__(
        self,
        *,
        status: int,
        type: str = "about:blank",
        title: str | None = None,
        detail: str = "",
        instance: str | None = None,
        request_id: str | None = None,
        errors: list[dict[str, Any]] | None = None,
        body: Any = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self.status = status
        self.type = type
        self.title = title or _phrase(status)
        self.detail = detail
        self.instance = instance
        self.request_id = request_id
        self.errors = list(errors or [])
        self.body = body
        self.headers: Mapping[str, str] = dict(headers or {})
        super().__init__(str(self))

    @property
    def slug(self) -> str | None:
        """`token-expired` for `urn:taskadence:problem:token-expired` (or its pre-rename twin); None for
        `about:blank`."""
        return problem_slug(self.type)

    def __str__(self) -> str:
        text = f"{self.status} {self.title}"
        if self.detail and self.detail != self.title:
            text += f": {self.detail}"
        if self.request_id:
            text += f" (request_id {self.request_id})"
        return text

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(status={self.status}, type={self.type!r}, detail={self.detail!r}, "
            f"request_id={self.request_id!r})"
        )


class BadRequestError(TaskadenceError):
    """400."""


class AuthenticationError(TaskadenceError):
    """401: missing, malformed, unknown, expired or revoked credentials."""


class ForbiddenError(TaskadenceError):
    """403: authenticated, but not allowed."""


PermissionDeniedError = ForbiddenError


class NotFoundError(TaskadenceError):
    """404."""


class ConflictError(TaskadenceError):
    """409."""


class PreconditionFailedError(TaskadenceError):
    """412: `If-Match` named a stale `ETag` — re-read the resource and retry. Nothing was written."""


class UnprocessableEntityError(TaskadenceError):
    """422."""


class RateLimitedError(TaskadenceError):
    """429: over the access token's per-minute limit. `.retry_after` is the server's `Retry-After`, in seconds."""

    @property
    def retry_after(self) -> float | None:
        return retry_after_seconds(self.headers)


class InternalError(TaskadenceError):
    """5xx. Quote `.request_id` to support."""


InternalServerError = InternalError


class InvalidParameterError(BadRequestError):
    """A query parameter outside what the operation accepts; `errors[0]["allowed"]` lists the valid values."""


class IdempotencyKeyInvalidError(BadRequestError):
    """`Idempotency-Key` must be 1–255 printable ASCII characters."""


class ValidationError(UnprocessableEntityError):
    """The body or query did not validate; `.errors` lists each failure (`loc`, `msg`, `type`)."""


class InvalidValueError(InvalidParameterError, ValidationError):
    """422 `invalid-parameter`: a body field outside its fixed set of values (a status, a priority, a type);
    `errors[0]["allowed"]` lists the valid values. Before the API named it (backend `5fa0aa4`) the same request was a
    `ValidationError`, and it still is one: `except ValidationError` / `UnprocessableEntityError` keep catching it,
    and so does `except InvalidParameterError`."""


class IdempotencyKeyReusedError(UnprocessableEntityError):
    """This `Idempotency-Key` was first used for a different request."""


class IdempotencyKeyInFlightError(ConflictError):
    """The first request with this `Idempotency-Key` has not finished; retry shortly."""


class UrlRefusedError(UnprocessableEntityError):
    """A webhook URL the API refuses (not https, credentials, or a private / loopback / metadata address)."""


class TokenInvalidError(AuthenticationError):
    """The access token is unknown or malformed (or its principal no longer exists)."""


class TokenExpiredError(AuthenticationError):
    """The access token is past its `expires_at` — mint a new one."""


class TokenRevokedError(AuthenticationError):
    """The access token was revoked (by its owner, an admin, a rotation, or its service account's deactivation)."""


class InsufficientScopeError(ForbiddenError):
    """The access token lacks the scope this operation needs; `.required_scope` names it (None: not for tokens)."""

    @property
    def required_scope(self) -> str | None:
        for item in self.errors:
            if isinstance(item, dict) and "required" in item:
                value = item["required"]
                return str(value) if value is not None else None
        return None


class TestTokenReadOnlyError(ForbiddenError):
    """A `tkd_test_` token authenticates and reads, but never writes."""

    __test__ = False  # not a pytest test class, despite the name


class TokenPolicyError(TaskadenceError):
    """The organization's token policy refuses this token (personal tokens off, expiry required, or too long)."""


BY_TYPE: dict[str, type[TaskadenceError]] = {
    URN + "validation": ValidationError,
    URN + "invalid-parameter": InvalidParameterError,
    URN + "precondition-failed": PreconditionFailedError,
    URN + "idempotency-key-reused": IdempotencyKeyReusedError,
    URN + "idempotency-key-in-flight": IdempotencyKeyInFlightError,
    URN + "idempotency-key-invalid": IdempotencyKeyInvalidError,
    URN + "rate-limit": RateLimitedError,
    URN + "internal": InternalError,
    URN + "token-invalid": TokenInvalidError,
    URN + "token-expired": TokenExpiredError,
    URN + "token-revoked": TokenRevokedError,
    URN + "insufficient-scope": InsufficientScopeError,
    URN + "test-token-read-only": TestTokenReadOnlyError,
    URN + "token-policy": TokenPolicyError,
    URN + "url-refused": UrlRefusedError,
}

BY_STATUS: dict[int, type[TaskadenceError]] = {
    400: BadRequestError,
    401: AuthenticationError,
    403: ForbiddenError,
    404: NotFoundError,
    409: ConflictError,
    412: PreconditionFailedError,
    422: UnprocessableEntityError,
    429: RateLimitedError,
}


def _phrase(status: int) -> str:
    try:
        return HTTPStatus(status).phrase
    except ValueError:
        return "Error"


def _text(detail: Any) -> str:
    if detail is None:
        return ""
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):  # FastAPI's 422 list, kept in `detail` by 4.1
        return "; ".join(str(d.get("msg", d)) if isinstance(d, dict) else str(d) for d in detail)
    return json.dumps(detail, default=str)


def retry_after_seconds(headers: Mapping[str, str]) -> float | None:
    """`Retry-After` as seconds: delta-seconds or an HTTP date. None when absent or unreadable."""
    value = next((v for k, v in headers.items() if k.lower() == "retry-after"), None)
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        from datetime import datetime, timezone

        when = parsedate_to_datetime(value)
        return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())
    except (TypeError, ValueError):
        return None


def error_class(status: int, type_: str) -> type[TaskadenceError]:
    slug = problem_slug(type_)
    if slug == "invalid-parameter" and status == 422:
        return InvalidValueError
    if slug is not None and URN + slug in BY_TYPE:
        return BY_TYPE[URN + slug]
    if status >= 500:
        return InternalError
    return BY_STATUS.get(status, TaskadenceError)


def from_response(response: httpx.Response) -> TaskadenceError:
    """The exception for a non-2xx response. Tolerant: a non-JSON or non-problem body still maps by status."""
    try:
        body: Any = response.json()
    except ValueError:
        body = response.text
    problem = body if isinstance(body, dict) else {}
    status = int(problem.get("status") or response.status_code)
    type_ = str(problem.get("type") or "about:blank")
    detail = (
        _text(problem.get("detail", problem.get("message")))
        or (body if isinstance(body, str) else "")
        or _phrase(status)
    )
    errors = problem.get("errors")
    if not isinstance(errors, list) and isinstance(problem.get("detail"), list):
        errors = problem["detail"]
    request_id = problem.get("request_id") or response.headers.get("x-request-id")
    cls = error_class(status, type_)
    return cls(
        status=status,
        type=type_,
        title=problem.get("title") or _phrase(status),
        detail=detail,
        instance=problem.get("instance"),
        request_id=request_id,
        errors=[e for e in (errors or []) if isinstance(e, dict)],
        body=body,
        headers=response.headers,
    )
