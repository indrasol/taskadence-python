"""The request layer under both clients: build a request from an `Operation`, send it with retries, turn the answer
into a typed model, a `Page`, `NotModified`, or an exception.

WHY THE FACADE SENDS ITS OWN REQUESTS. The generated client (`taskadence._generated`) is the source of the MODELS and of
each operation's response PARSER (`_parse_response`, which the facade calls, so typing is exactly the generator's).
Its request functions are not used to send, because (1) they always send every spec default — `limit=100`,
`sort_by=title`, the deprecated `offset=0` and a leaked `is_registration=false` — where the facade sends only what the
caller passed; (2) they give no hook per call for retries, `Idempotency-Key`, `If-Match` / `If-None-Match` or the
`ETag`; (3) they name the list grammar's `filter[status]` as a keyword `filterstatus`. The operation table
(`_operations.py`) is generated from the same spec, and `tests/test_drift.py` checks each operation's method and URL
against the generated `_get_kwargs`.

RETRIES. Safe requests are retried on 429 (honouring `Retry-After`), 502 / 503 / 504 and connection failures, with
exponential backoff and jitter, up to `max_retries`: GET / HEAD / DELETE / PUT always, PATCH only with `If-Match`, POST
only with an `Idempotency-Key` (every create operation gets a fresh uuid4 key unless the caller passes one, or None).
A `Retry-After` longer than `max_retry_after` is not waited out: the `RateLimitedError` is raised at once.
"""

from __future__ import annotations

import datetime as _dt
import enum
import json
import logging
import mimetypes
import os
import platform
import random
import time
import uuid
import warnings
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import PurePath
from typing import IO, Any, Final
from urllib.parse import quote

import httpx

from . import errors
from ._brand import BRAND_NAME, ENV_PREFIX, SLUG, getenv
from ._version import __version__
from .pagination import AsyncPage, Page

logger = logging.getLogger(SLUG)

TOKEN_ENV = ENV_PREFIX + "TOKEN"  # the variable NAME (`_brand.getenv` also reads the pre-rename name)
URL_ENV = ENV_PREFIX + "API_URL"
VERSION_HEADER = f"{BRAND_NAME}-Version"

RETRY_STATUSES: Final = frozenset({429, 502, 503, 504})
IDEMPOTENT_METHODS: Final = frozenset({"GET", "HEAD", "DELETE", "PUT", "OPTIONS"})
BACKOFF_BASE = 0.5
BACKOFF_MAX = 8.0

FileContent = bytes | IO[bytes]
FileInput = bytes | IO[bytes] | str | os.PathLike[str] | tuple[str, FileContent] | tuple[str, FileContent, str]


class NotModifiedType:
    """The answer to a read with `if_none_match=<etag>` when the resource has not changed (HTTP 304). Falsy."""

    _instance: NotModifiedType | None = None

    def __new__(cls) -> NotModifiedType:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "NotModified"


NotModified: Final = NotModifiedType()


class _Auto:
    def __repr__(self) -> str:
        return "AUTO"


AUTO: Final = _Auto()
"""`idempotency_key=AUTO` (the default on creates): a fresh uuid4 per call, reused by that call's retries."""


class ConfigurationError(errors.APIError, ValueError):
    """The client cannot be built as asked (no token, a malformed base URL)."""


@dataclass(frozen=True)
class Operation:
    """One public API operation, as the facade needs it. Instances are generated into `_operations.py`."""

    op_id: str
    method: str
    path: str
    path_params: tuple[str, ...] = ()
    query: tuple[str, ...] = ()
    filters: tuple[str, ...] = ()
    body: str | None = None  # "json" | "multipart" | None
    files: tuple[str, ...] = ()  # multipart fields that carry a file
    is_list: bool = False  # `{data, next_cursor}` (possibly one member of a union)
    is_create: bool = False  # honours `Idempotency-Key`
    if_match: bool = False
    if_none_match: bool = False
    returns: str = "model"  # "model" | "text" | "none"
    parse: Callable[..., Any] | None = field(default=None, repr=False, compare=False)
    item: Callable[[Any], Any] | None = field(default=None, repr=False, compare=False)
    scopes: tuple[str, ...] = ()
    summary: str = ""


@dataclass
class _Request:
    method: str
    url: str
    params: list[tuple[str, str]]
    headers: dict[str, str]
    content: bytes | None = None
    files: list[tuple[str, tuple[str, bytes, str]]] | None = None
    data: dict[str, str] | None = None

    @property
    def retryable(self) -> bool:
        if self.method in IDEMPOTENT_METHODS:
            return True
        if self.method == "PATCH":
            return "If-Match" in self.headers
        if self.method == "POST":
            return "Idempotency-Key" in self.headers
        return False


# ---------------------------------------------------------------------------
# Encoding
# ---------------------------------------------------------------------------


def _json_default(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, (_dt.datetime, _dt.date)):
        return value.isoformat()
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, (set, frozenset, tuple)):
        return list(value)
    raise TypeError(f"{type(value).__name__} is not JSON serializable")


def _scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (_dt.datetime, _dt.date)):
        return value.isoformat()
    if isinstance(value, enum.Enum):
        return str(value.value)
    return str(value)


def _query_value(value: Any) -> str:
    """A list is comma-joined (the list grammar's multi-value rule); anything else is its string form."""
    if isinstance(value, (list, tuple, set, frozenset)):
        return ",".join(_scalar(v) for v in value)
    return _scalar(value)


def _file_part(name: str, value: FileInput) -> tuple[str, tuple[str, bytes, str]]:
    filename: str | None = None
    mime: str | None = None
    content: Any = value
    if isinstance(value, tuple):
        filename, content = value[0], value[1]
        mime = value[2] if len(value) > 2 else None
    if isinstance(content, (str, os.PathLike)):
        path = os.fspath(content)
        filename = filename or PurePath(path).name
        with open(path, "rb") as handle:
            data = handle.read()
    elif isinstance(content, bytes):
        data = content
    else:
        data = content.read()
        filename = filename or PurePath(str(getattr(content, "name", "upload"))).name
    filename = filename or "upload"
    mime = mime or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return name, (filename, data, mime)


# ---------------------------------------------------------------------------
# The shared core
# ---------------------------------------------------------------------------


class _BaseClient:
    def __init__(
        self,
        token: str | None,
        base_url: str | None,
        *,
        timeout: float,
        max_retries: int,
        api_version: str | None,
        default_base_url: str,
        spec_version: str,
        max_retry_after: float,
        headers: Mapping[str, str] | None,
    ) -> None:
        token = token or getenv(TOKEN_ENV)
        if not token:
            raise ConfigurationError(
                f"No token: pass {BRAND_NAME}(token=...) or set {TOKEN_ENV} (a `tkd_live_…` access token)."
            )
        base = (base_url or getenv(URL_ENV) or default_base_url).strip().rstrip("/")
        base = base.removesuffix("/v1")
        if not base.startswith(("http://", "https://")):
            raise ConfigurationError(f"base_url must start with http:// or https:// (got {base!r})")
        self.base_url = base
        self.timeout = timeout
        self.max_retries = max(0, int(max_retries))
        self.max_retry_after = max_retry_after
        self.api_version = api_version or spec_version
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, application/problem+json",
            "User-Agent": f"{SLUG}-python/{__version__} python/{platform.python_version()}",
            VERSION_HEADER: self.api_version,
            **dict(headers or {}),
        }
        self._warned: set[str] = set()
        self._sleep: Callable[[float], Any] = time.sleep

    def __repr__(self) -> str:  # never the token
        return f"<{type(self).__name__} base_url={self.base_url!r}>"

    # -- building -------------------------------------------------------------------------------------------------

    def _build(
        self,
        op: Operation,
        *,
        path: Sequence[Any] = (),
        query: Mapping[str, Any] | None = None,
        filter: Mapping[str, Any] | None = None,
        body: Any = None,
        form: Mapping[str, Any] | None = None,
        if_match: str | None = None,
        if_none_match: str | None = None,
        idempotency_key: str | _Auto | None = AUTO,
    ) -> _Request:
        if len(path) != len(op.path_params):
            raise TypeError(f"{op.op_id} takes {len(op.path_params)} path argument(s): {', '.join(op.path_params)}")
        url = op.path.format(
            **{name: quote(_scalar(value), safe="") for name, value in zip(op.path_params, path, strict=True)}
        )
        params: list[tuple[str, str]] = []
        for key, value in (query or {}).items():
            if value is not None:
                params.append((key, _query_value(value)))
        if filter:
            unknown = sorted(set(filter) - set(op.filters))
            if unknown:
                allowed = ", ".join(op.filters) or "none"
                raise ValueError(f"{op.op_id}: unknown filter key(s) {', '.join(unknown)}; allowed: {allowed}")
            for key, value in filter.items():
                if value is not None:
                    params.append((f"filter[{key}]", _query_value(value)))
        headers: dict[str, str] = {}
        if op.is_create and idempotency_key is not None:
            headers["Idempotency-Key"] = str(uuid.uuid4()) if isinstance(idempotency_key, _Auto) else idempotency_key
        if if_match is not None:
            headers["If-Match"] = if_match
        if if_none_match is not None:
            headers["If-None-Match"] = if_none_match
        request = _Request(op.method, url, params, headers)
        if op.body == "json" and body is not None:
            payload = body.to_dict() if hasattr(body, "to_dict") else body
            request.content = json.dumps(payload, default=_json_default).encode()
            headers["Content-Type"] = "application/json"
        elif op.body == "multipart":
            request.files, request.data = [], {}
            for key, value in (form or {}).items():
                if value is None:
                    continue
                if key in op.files:
                    request.files.append(_file_part(key, value))
                else:
                    request.data[key] = _scalar(value)
        return request

    # -- retries --------------------------------------------------------------------------------------------------

    def _retry_delay(self, attempt: int, response: httpx.Response | None) -> float | None:
        """Seconds to wait before attempt `attempt + 1`, or None: do not retry."""
        if attempt >= self.max_retries:
            return None
        if response is not None:
            after = errors.retry_after_seconds(response.headers)
            if after is not None:
                return after if after <= self.max_retry_after else None
        ceiling = min(BACKOFF_MAX, BACKOFF_BASE * (2.0**attempt))
        return ceiling / 2 + random.uniform(0, ceiling / 2)  # noqa: S311 - jitter, not cryptography

    def _log(
        self,
        request: _Request,
        response: httpx.Response | None,
        started: float,
        attempt: int,
        failure: Exception | None = None,
    ) -> None:
        if not logger.isEnabledFor(logging.DEBUG):
            return
        took = (time.monotonic() - started) * 1000
        if response is not None:
            logger.debug(
                "%s %s -> %s in %.0f ms (attempt %d, request_id %s)",
                request.method,
                request.url,
                response.status_code,
                took,
                attempt + 1,
                response.headers.get("x-request-id"),
            )
        else:
            logger.debug(
                "%s %s -> %s after %.0f ms (attempt %d)",
                request.method,
                request.url,
                type(failure).__name__,
                took,
                attempt + 1,
            )

    # -- answering ------------------------------------------------------------------------------------------------

    def _warn_deprecated(self, op: Operation, response: httpx.Response) -> None:
        if op.op_id in self._warned:
            return
        deprecation = response.headers.get("deprecation")
        sunset = response.headers.get("sunset")
        if not (deprecation or sunset):
            return
        self._warned.add(op.op_id)
        successor = response.headers.get("link", "")
        text = f"{BRAND_NAME}: {op.op_id} ({op.method} {op.path}) is deprecated"
        if sunset:
            text += f" and will be removed after {sunset}"
        if successor:
            text += f"; successor: {successor}"
        warnings.warn(text, DeprecationWarning, stacklevel=5)

    def _answer(
        self,
        op: Operation,
        response: httpx.Response,
        parse_client: Any,
        again: Callable[[str], Any] | None,
        page_cls: type[Page[Any]] | type[AsyncPage[Any]],
    ) -> Any:
        self._warn_deprecated(op, response)
        if response.status_code == 304:
            return NotModified
        if response.status_code >= 400:
            raise errors.from_response(response)
        if op.returns == "none" or response.status_code == 204:
            return None
        if op.returns == "text":
            return response.text
        etag = response.headers.get("etag")
        if op.is_list and op.item is not None:
            try:
                raw = response.json()
            except ValueError as exc:
                raise errors.ResponseValidationError(
                    f"{op.op_id}: the response is not JSON", operation=op.op_id, body=response.text
                ) from exc
            if isinstance(raw, list):  # a bare array (pre-4.1 shape): one page, no cursor — as `unwrapList` reads it
                items = [self._parse_item(op, item) for item in raw]
                return page_cls(items, None, envelope=raw, etag=etag)
        assert op.parse is not None, op.op_id
        try:
            parsed = op.parse(client=parse_client, response=response)
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise errors.ResponseValidationError(
                f"{op.op_id}: the response does not match the models this SDK was generated from ({exc!r}); "
                "upgrade taskadence, or read `.body`",
                operation=op.op_id,
                body=_json_or_text(response),
            ) from exc
        if parsed is None:
            raise errors.ResponseValidationError(
                f"{op.op_id}: HTTP {response.status_code} is not a status the API documents for this operation",
                operation=op.op_id,
                body=_json_or_text(response),
            )
        if op.is_list and hasattr(parsed, "data") and hasattr(parsed, "next_cursor"):
            cursor = parsed.next_cursor if isinstance(parsed.next_cursor, str) else None
            return page_cls(list(parsed.data), cursor, envelope=parsed, etag=etag, fetch_next=again)
        if etag and hasattr(parsed, "etag"):
            parsed.etag = etag
        return parsed

    @staticmethod
    def _parse_item(op: Operation, raw: Any) -> Any:
        assert op.item is not None
        try:
            return op.item(raw)
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise errors.ResponseValidationError(
                f"{op.op_id}: an item does not match the generated model ({exc!r})", operation=op.op_id, body=raw
            ) from exc


def _json_or_text(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text


class SyncCore(_BaseClient):
    """The synchronous transport (`Taskadence`)."""

    def __init__(self, *args: Any, http_client: httpx.Client | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._owns_http = http_client is None
        self._http = http_client or httpx.Client(timeout=self.timeout, follow_redirects=False)
        from ._generated.client import Client as _ParseClient

        self._parse_client = _ParseClient(base_url=self.base_url, raise_on_unexpected_status=False)

    def _send(self, request: _Request) -> httpx.Response:
        attempt = 0
        while True:
            started = time.monotonic()
            try:
                response = self._http.request(
                    request.method,
                    self.base_url + request.url,
                    params=tuple(request.params),
                    headers={**self._headers, **request.headers},
                    content=request.content,
                    files=request.files,
                    data=request.data,
                )
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.RemoteProtocolError) as exc:
                self._log(request, None, started, attempt, exc)
                delay = self._retry_delay(attempt, None) if request.retryable else None
                if delay is None:
                    raise (
                        errors.APITimeoutError if isinstance(exc, httpx.TimeoutException) else errors.APIConnectionError
                    )(f"{request.method} {request.url}: {exc}") from exc
            except httpx.TimeoutException as exc:
                self._log(request, None, started, attempt, exc)
                raise errors.APITimeoutError(f"{request.method} {request.url}: {exc}") from exc
            else:
                self._log(request, response, started, attempt)
                delay = (
                    self._retry_delay(attempt, response)
                    if request.retryable and response.status_code in RETRY_STATUSES
                    else None
                )
                if delay is None:
                    return response
                response.close()
            self._sleep(delay)
            attempt += 1

    def _call(self, op: Operation, **kwargs: Any) -> Any:
        request = self._build(op, **kwargs)
        response = self._send(request)

        def again(cursor: str) -> Any:
            return self._call(op, **{**kwargs, "query": {**(kwargs.get("query") or {}), "cursor": cursor}})

        return self._answer(op, response, self._parse_client, again, Page)

    def _upload(self, op: Operation, *, progress: Callable[[int, int], object] | None = None, **kwargs: Any) -> Any:
        """A file upload: direct to storage, else the operation's multipart route (`_uploads`)."""
        from ._uploads import upload

        return upload(self, op, query=kwargs.get("query"), form=kwargs.get("form"), progress=progress)

    def close(self) -> None:
        if self._owns_http:
            self._http.close()


class AsyncCore(_BaseClient):
    """The asynchronous transport (`AsyncTaskadence`)."""

    def __init__(self, *args: Any, http_client: httpx.AsyncClient | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        import asyncio

        self._owns_http = http_client is None
        self._http = http_client or httpx.AsyncClient(timeout=self.timeout, follow_redirects=False)
        self._asleep: Callable[[float], Any] = asyncio.sleep
        from ._generated.client import Client as _ParseClient

        self._parse_client = _ParseClient(base_url=self.base_url, raise_on_unexpected_status=False)

    async def _send(self, request: _Request) -> httpx.Response:
        attempt = 0
        while True:
            started = time.monotonic()
            try:
                response = await self._http.request(
                    request.method,
                    self.base_url + request.url,
                    params=tuple(request.params),
                    headers={**self._headers, **request.headers},
                    content=request.content,
                    files=request.files,
                    data=request.data,
                )
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.RemoteProtocolError) as exc:
                self._log(request, None, started, attempt, exc)
                delay = self._retry_delay(attempt, None) if request.retryable else None
                if delay is None:
                    raise (
                        errors.APITimeoutError if isinstance(exc, httpx.TimeoutException) else errors.APIConnectionError
                    )(f"{request.method} {request.url}: {exc}") from exc
            except httpx.TimeoutException as exc:
                self._log(request, None, started, attempt, exc)
                raise errors.APITimeoutError(f"{request.method} {request.url}: {exc}") from exc
            else:
                self._log(request, response, started, attempt)
                delay = (
                    self._retry_delay(attempt, response)
                    if request.retryable and response.status_code in RETRY_STATUSES
                    else None
                )
                if delay is None:
                    return response
                await response.aclose()
            await self._asleep(delay)
            attempt += 1

    async def _call(self, op: Operation, **kwargs: Any) -> Any:
        request = self._build(op, **kwargs)
        response = await self._send(request)

        async def again(cursor: str) -> Any:
            return await self._call(op, **{**kwargs, "query": {**(kwargs.get("query") or {}), "cursor": cursor}})

        return self._answer(op, response, self._parse_client, again, AsyncPage)

    async def _upload(
        self, op: Operation, *, progress: Callable[[int, int], object] | None = None, **kwargs: Any
    ) -> Any:
        """A file upload: direct to storage, else the operation's multipart route (`_uploads`)."""
        from ._uploads import aupload

        return await aupload(self, op, query=kwargs.get("query"), form=kwargs.get("form"), progress=progress)

    async def aclose(self) -> None:
        if self._owns_http:
            await self._http.aclose()
