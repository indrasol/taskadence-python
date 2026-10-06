"""Direct-to-storage uploads: the one path every file upload in this package takes (both clients and `tm`).

THE FLOW (the generated `uploads.create` / `uploads.complete` operations):

    1. create    POST /v1/uploads {kind, <parent id>, filename, size, content_type, [project_id, is_inline,
                 project_name]} -> `UploadCreateOut` {upload_id, upload_url, method: "PUT", headers, expires_at}. Size,
                 type, permission and the organization's storage are checked here, before a byte is sent.
    2. PUT       the file goes straight to Azure Blob Storage at `upload_url` (a SAS URL for one pending blob,
                 create + write only, 15 minutes): streamed in chunks from the path / file object, never read whole.
                 Retried on 5xx and connection failures (the file is rewound), with the client's backoff.
    3. complete  POST /v1/uploads/{upload_id}/complete {title} -> the attachment / resource, the same model the old
                 multipart method returned. The API inspects and scans the blob here; a refusal is a `TaskadenceError`.

FALLBACK. An API without direct uploads answers create with its router's plain 404 (`about:blank`, detail exactly
"Not Found") or a 405; the upload is then sent the old way, as multipart to the operation's own route. So this package
works against an API that has not shipped the routes and switches by itself when it has. Any other 404 is the API's own
answer about the parent (a task / project that does not exist or that the caller cannot read: a typed `type` or the
route's own `detail`) and is raised as `NotFoundError`, never retried as multipart.

THE SAS URL IS A CREDENTIAL. It never reaches a log line or an exception: messages carry it without its query string,
and a filter on the `httpx` logger (which logs every request URL at INFO) strips the query from storage URLs.
"""

from __future__ import annotations

import asyncio
import logging
import mimetypes
import os
import time
from collections.abc import AsyncIterator, Callable, Iterator, Mapping
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePath
from typing import IO, TYPE_CHECKING, Any, Final
from urllib.parse import urlsplit, urlunsplit

import httpx

from . import errors
from ._brand import problem_slug
from ._generated import models as _models
from ._operations import OPERATIONS as _OPS

if TYPE_CHECKING:
    from ._core import AsyncCore, FileInput, Operation, SyncCore, _BaseClient

logger = logging.getLogger("taskadence")

UploadProgress = Callable[[int, int], object]
"""`progress(sent, total)`: called as bytes reach storage (and once at the end of a multipart fallback)."""

CHUNK_SIZE: Final = 1024 * 1024
PUT_TIMEOUT: Final = httpx.Timeout(600.0, connect=30.0)  # 100 MB on a slow link; per read / write, not in total
PUT_RETRY_STATUSES: Final = frozenset({408, 429, 500, 502, 503, 504})
ROUTER_NOT_FOUND: Final = "Not Found"  # the API router's detail for a path it does not mount (Starlette's default)


@dataclass(frozen=True)
class DirectKind:
    """How one multipart operation maps onto the direct flow."""

    kind: str  # `UploadCreateIn.kind`
    parent: str  # the form / query field that names the parent (task / project)
    model: str  # the generated model `complete` answers with (the old route's 201 model)
    extra: tuple[str, ...] = ()  # optional `UploadCreateIn` fields the multipart method also takes


DIRECT: Final[Mapping[str, DirectKind]] = {
    "task-attachments.create": DirectKind(
        "attachment", "task_id", "TaskAttachmentInDB", extra=("project_id", "is_inline")
    ),
    "project-resources.upload": DirectKind(
        "project_file", "project_id", "ProjectResourceInDB", extra=("project_name",)
    ),
}


# ---------------------------------------------------------------------------
# SAS redaction
# ---------------------------------------------------------------------------


def redact(url: object) -> str:
    """The URL without its query string (a SAS URL's signature lives there) or fragment."""
    parts = urlsplit(str(url))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "<redacted>" if parts.query else "", ""))


def _is_signed(value: Any) -> bool:
    text = str(value)
    return "sig=" in text and "://" in text


class _RedactSignedUrls(logging.Filter):
    """httpx logs `HTTP Request: PUT <url> …` at INFO: a signed storage URL loses its query string first."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple) and any(_is_signed(a) for a in record.args):
            record.args = tuple(redact(a) if _is_signed(a) else a for a in record.args)
        elif isinstance(record.msg, str) and _is_signed(record.msg):
            record.msg = " ".join(redact(w) if _is_signed(w) else w for w in record.msg.split(" "))
        return True


_FILTER: Final = _RedactSignedUrls()
for _name in ("httpx", "httpcore"):
    if _FILTER not in logging.getLogger(_name).filters:
        logging.getLogger(_name).addFilter(_FILTER)


# ---------------------------------------------------------------------------
# The file
# ---------------------------------------------------------------------------


@dataclass
class _Source:
    filename: str
    content_type: str
    size: int
    stream: IO[bytes]
    start: int  # where the bytes begin (a caller's file object may not be at 0)
    owned: bool  # opened here (a path), so closed here

    @property
    def rewindable(self) -> bool:
        try:
            return self.stream.seekable()
        except (AttributeError, ValueError):
            return False

    def rewind(self) -> None:
        self.stream.seek(self.start)

    def close(self) -> None:
        if self.owned:
            self.stream.close()


def _size_of(stream: IO[bytes]) -> int | None:
    """Bytes from the current position to the end, without reading them. None when it cannot be known."""
    try:
        position = stream.tell()
        fileno = stream.fileno()
    except (AttributeError, OSError, ValueError):
        fileno = None
    if fileno is not None:
        try:
            return max(0, os.fstat(fileno).st_size - position)
        except OSError:
            pass
    try:
        if not stream.seekable():
            return None
        position = stream.tell()
        end = stream.seek(0, os.SEEK_END)
        stream.seek(position)
        return max(0, end - position)
    except (AttributeError, OSError, ValueError):
        return None


def _open(value: FileInput) -> _Source | None:
    """The file behind a `FileInput` (a path, bytes, a binary file object, or `(name, content[, type])`), or None
    when its size cannot be known up front (a non-seekable stream: the multipart route takes it)."""
    filename: str | None = None
    content_type: str | None = None
    content: Any = value
    if isinstance(value, tuple):
        filename, content = value[0], value[1]
        content_type = value[2] if len(value) > 2 else None
    owned = False
    if isinstance(content, (str, os.PathLike)):
        path = os.fspath(content)
        filename = filename or PurePath(path).name
        stream: IO[bytes] = open(path, "rb")  # noqa: SIM115 - closed by _Source.close
        owned = True
    elif isinstance(content, (bytes, bytearray, memoryview)):
        stream = BytesIO(bytes(content))
    else:
        stream = content
        filename = filename or PurePath(str(getattr(content, "name", "upload"))).name
    size = _size_of(stream)
    if size is None:
        if owned:
            stream.close()
        return None
    try:
        start = stream.tell()
    except (AttributeError, OSError, ValueError):
        start = 0
    filename = filename or "upload"
    content_type = content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return _Source(filename, content_type, size, stream, start, owned)


def _chunks(source: _Source, progress: UploadProgress | None) -> Iterator[bytes]:
    sent = 0
    while sent < source.size:
        chunk = source.stream.read(min(CHUNK_SIZE, source.size - sent))
        if not chunk:
            break
        sent += len(chunk)
        yield chunk
        if progress is not None:
            progress(sent, source.size)


async def _achunks(source: _Source, progress: UploadProgress | None) -> AsyncIterator[bytes]:
    sent = 0
    while sent < source.size:
        chunk = await asyncio.to_thread(source.stream.read, min(CHUNK_SIZE, source.size - sent))
        if not chunk:
            break
        sent += len(chunk)
        yield chunk
        if progress is not None:
            progress(sent, source.size)


# ---------------------------------------------------------------------------
# The requests
# ---------------------------------------------------------------------------


def _wanted(op: Operation, form: Mapping[str, Any], query: Mapping[str, Any]) -> DirectKind | None:
    direct = DIRECT.get(op.op_id)
    if direct is None:
        return None
    if (form.get(direct.parent) or query.get(direct.parent)) is None:
        return None
    return direct


def _create_body(direct: DirectKind, source: _Source, form: Mapping[str, Any], query: Mapping[str, Any]) -> Any:
    fields = {**query, **form}
    body: dict[str, Any] = {
        "kind": direct.kind,
        direct.parent: fields[direct.parent],
        "filename": source.filename,
        "size": source.size,
        "content_type": source.content_type,
    }
    for name in direct.extra:
        if fields.get(name) is not None:
            body[name] = fields[name]
    return _models.UploadCreateIn.from_dict(body)


def _complete_body(title: Any) -> Any:
    from ._core import _scalar

    return _models.UploadCompleteIn(title=_scalar(title)) if title is not None else None


def _route_missing(response: httpx.Response) -> bool:
    """True when create's answer says the API has no direct uploads (fall back to multipart), False when it is the
    API's own answer (a 404 about the parent is raised: a missing task must not be retried as multipart)."""
    if response.status_code == 405:
        return True
    if response.status_code != 404:
        return False
    try:
        body = response.json()
    except ValueError:
        return True  # not the API's problem+json: a proxy / gateway in front of a server without the route
    if not isinstance(body, dict):
        return True
    if problem_slug(str(body.get("type") or "about:blank")) is not None:
        return False  # a typed problem is always the API's own answer
    return body.get("detail") in (None, "", ROUTER_NOT_FOUND)


@dataclass(frozen=True)
class _Ticket:
    upload_id: str
    url: str
    method: str
    headers: dict[str, str]


def _ticket(core: SyncCore | AsyncCore, response: httpx.Response) -> _Ticket:
    """`UploadCreateOut` (or the API's error), through the generated parser. A malformed answer never carries the
    signed URL into the exception."""
    from .pagination import Page

    try:
        out = core._answer(_OPS["uploads.create"], response, core._parse_client, None, Page)
    except errors.ResponseValidationError as exc:
        if "sig=" not in response.text:
            raise
        exc.body = None  # it held the answer, signed URL included; the chained original must not carry it either
        raise errors.ResponseValidationError(
            "uploads.create: the answer is not an upload ticket (body withheld: it carries a signed URL)",
            operation="uploads.create",
            body=None,
        ) from None
    method = out.method if isinstance(out.method, str) else "PUT"
    headers = out.headers.additional_properties if hasattr(out.headers, "additional_properties") else {}
    return _Ticket(
        str(out.upload_id), str(out.upload_url), method.upper(), {str(k): str(v) for k, v in headers.items()}
    )


def _put_headers(ticket: _Ticket, source: _Source) -> dict[str, str]:
    headers = {"x-ms-blob-type": "BlockBlob", "Content-Type": source.content_type, **ticket.headers}
    headers["Content-Length"] = str(source.size)
    return headers


def _storage_code(response: httpx.Response) -> str | None:
    """Azure's `<Code>…</Code>` (or `x-ms-error-code`); only the code, never the message."""
    code: str | None = response.headers.get("x-ms-error-code")
    if code:
        return code
    text = response.text
    start, end = text.find("<Code>"), text.find("</Code>")
    return text[start + 6 : end] if 0 <= start < end else None


def _put_error(ticket: _Ticket, response: httpx.Response | None, failure: Exception | None) -> errors.BlobUploadError:
    where = redact(ticket.url)
    if response is not None:
        code = _storage_code(response)
        return errors.BlobUploadError(
            f"{ticket.method} {where}: storage answered HTTP {response.status_code}" + (f" ({code})" if code else ""),
            status=response.status_code,
            code=code,
            url=where,
        )
    name = type(failure).__name__ if failure is not None else "error"
    return errors.BlobUploadError(f"{ticket.method} {where}: {name} (no answer from storage)", url=where)


def _put_delay(core: _BaseClient, attempt: int, source: _Source) -> float | None:
    if not source.rewindable:
        return None
    return core._retry_delay(attempt, None)


def _checked(direct: DirectKind, result: Any) -> Any:
    """`uploads.complete` answers a union: the model must be the one the old method returned for this kind."""
    if not isinstance(result, getattr(_models, direct.model)):
        raise errors.ResponseValidationError(
            f"uploads.complete: expected {direct.model}, got {type(result).__name__}",
            operation="uploads.complete",
            body=result.to_dict() if hasattr(result, "to_dict") else result,
        )
    return result


def _log_put(ticket: _Ticket, status: Any, started: float, attempt: int) -> None:
    if logger.isEnabledFor(logging.DEBUG):
        took = (time.monotonic() - started) * 1000
        logger.debug(
            "%s %s -> %s in %.0f ms (attempt %d)", ticket.method, redact(ticket.url), status, took, attempt + 1
        )


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------


def upload(
    core: SyncCore,
    op: Operation,
    *,
    query: Mapping[str, Any] | None = None,
    form: Mapping[str, Any] | None = None,
    progress: UploadProgress | None = None,
) -> Any:
    """`op` (a multipart upload operation) through the direct flow, else its own multipart route."""
    query, form = dict(query or {}), dict(form or {})
    direct = _wanted(op, form, query)
    source = _open(form[op.files[0]]) if direct is not None and op.files and form.get(op.files[0]) is not None else None
    if direct is None or source is None:
        return _multipart(core, op, query, form, progress)
    try:
        created = core._send(core._build(_OPS["uploads.create"], body=_create_body(direct, source, form, query)))
        if _route_missing(created):
            created.close()
            if source.rewindable:
                source.rewind()
            return _multipart(core, op, query, form, progress)
        ticket = _ticket(core, created)
        _put(core, ticket, source, progress)
        result = core._call(_OPS["uploads.complete"], path=(ticket.upload_id,), body=_complete_body(form.get("title")))
        return _checked(direct, result)
    finally:
        source.close()


def _put(core: SyncCore, ticket: _Ticket, source: _Source, progress: UploadProgress | None) -> None:
    attempt = 0
    while True:
        started = time.monotonic()
        if attempt:
            source.rewind()
        response: httpx.Response | None = None
        failure: Exception | None = None
        try:
            response = core._http.request(
                ticket.method,
                ticket.url,
                headers=_put_headers(ticket, source),
                content=_chunks(source, progress),
                timeout=PUT_TIMEOUT,
            )
        except httpx.TransportError as exc:
            failure = exc
        _log_put(ticket, response.status_code if response is not None else type(failure).__name__, started, attempt)
        if response is not None and response.status_code < 300:
            response.close()
            return
        retry = failure is not None or (response is not None and response.status_code in PUT_RETRY_STATUSES)
        delay = _put_delay(core, attempt, source) if retry else None
        if delay is None:
            raise _put_error(ticket, response, failure) from None
        if response is not None:
            response.close()
        core._sleep(delay)
        attempt += 1


def _multipart(
    core: SyncCore, op: Operation, query: Mapping[str, Any], form: Mapping[str, Any], progress: UploadProgress | None
) -> Any:
    result = core._call(op, query=query, form=form)
    _report_done(op, form, progress)
    return result


def _report_done(op: Operation, form: Mapping[str, Any], progress: UploadProgress | None) -> None:
    if progress is None or not op.files:
        return
    value = form.get(op.files[0])
    content = value[1] if isinstance(value, tuple) else value
    size: int | None
    if isinstance(content, (bytes, bytearray, memoryview)):
        size = len(content)
    elif isinstance(content, (str, os.PathLike)):
        size = os.path.getsize(content)
    else:
        size = None
    if size is not None:
        progress(size, size)


# ---------------------------------------------------------------------------
# Async
# ---------------------------------------------------------------------------


async def aupload(
    core: AsyncCore,
    op: Operation,
    *,
    query: Mapping[str, Any] | None = None,
    form: Mapping[str, Any] | None = None,
    progress: UploadProgress | None = None,
) -> Any:
    """`upload`, awaited."""
    query, form = dict(query or {}), dict(form or {})
    direct = _wanted(op, form, query)
    source = _open(form[op.files[0]]) if direct is not None and op.files and form.get(op.files[0]) is not None else None
    if direct is None or source is None:
        return await _amultipart(core, op, query, form, progress)
    try:
        created = await core._send(core._build(_OPS["uploads.create"], body=_create_body(direct, source, form, query)))
        if _route_missing(created):
            await created.aclose()
            if source.rewindable:
                source.rewind()
            return await _amultipart(core, op, query, form, progress)
        ticket = _ticket(core, created)
        await _aput(core, ticket, source, progress)
        result = await core._call(
            _OPS["uploads.complete"], path=(ticket.upload_id,), body=_complete_body(form.get("title"))
        )
        return _checked(direct, result)
    finally:
        source.close()


async def _aput(core: AsyncCore, ticket: _Ticket, source: _Source, progress: UploadProgress | None) -> None:
    attempt = 0
    while True:
        started = time.monotonic()
        if attempt:
            source.rewind()
        response: httpx.Response | None = None
        failure: Exception | None = None
        try:
            response = await core._http.request(
                ticket.method,
                ticket.url,
                headers=_put_headers(ticket, source),
                content=_achunks(source, progress),
                timeout=PUT_TIMEOUT,
            )
        except httpx.TransportError as exc:
            failure = exc
        _log_put(ticket, response.status_code if response is not None else type(failure).__name__, started, attempt)
        if response is not None and response.status_code < 300:
            await response.aclose()
            return
        retry = failure is not None or (response is not None and response.status_code in PUT_RETRY_STATUSES)
        delay = _put_delay(core, attempt, source) if retry else None
        if delay is None:
            raise _put_error(ticket, response, failure) from None
        if response is not None:
            await response.aclose()
        await core._asleep(delay)
        attempt += 1


async def _amultipart(
    core: AsyncCore, op: Operation, query: Mapping[str, Any], form: Mapping[str, Any], progress: UploadProgress | None
) -> Any:
    result = await core._call(op, query=query, form=form)
    _report_done(op, form, progress)
    return result


__all__ = ["DIRECT", "UploadProgress", "aupload", "redact", "upload"]
