"""Direct-to-storage uploads (`taskadence._uploads`): the generated `uploads.create` -> PUT to the SAS URL -> the
generated `uploads.complete`; the fallback to multipart (only on the router's plain 404 or a 405); PUT retries,
refusals, SAS redaction and streaming. One fake (an `httpx.MockTransport`) plays both the API and Azure Blob Storage,
since the PUT goes to another host."""

from __future__ import annotations

import io
import json
import logging
from pathlib import Path
from typing import Any

import httpx
import pytest

from taskadence import AsyncTaskadence, BlobUploadError, Taskadence, errors, models
from taskadence._uploads import CHUNK_SIZE, redact

from .conftest import BASE, TOKEN, example, problem

BLOB = "https://tkdfiles.blob.core.windows.net/files/pending/O0020/up_1"
SIG = "sig=S3CR3T%2Bsignature"
SAS_URL = f"{BLOB}?sv=2025-01-05&sr=b&sp=cw&se=2026-10-05T12%3A15%3A00Z&spr=https&{SIG}"
SECRET = "S3CR3T"


# What an API without `POST /v1/uploads` answers: its router's plain 404 (Starlette's "Not Found", as a problem).
ROUTER_404 = (404, problem(404, detail="Not Found"))


def ticket(**over: Any) -> dict[str, Any]:
    return {
        "upload_id": "up_1",
        "upload_url": SAS_URL,
        "method": "PUT",
        "headers": {"x-ms-blob-type": "BlockBlob", "Content-Type": "text/plain"},
        "expires_at": "2026-10-05T12:15:00Z",
        **over,
    }


Answer = tuple[int, Any] | Exception


class Fake:
    """The API and the storage account. Each route answers from its queue (the last answer repeats)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, httpx.Headers, bytes]] = []
        self.answers: dict[str, list[Answer]] = {
            "create": [(201, ticket())],
            "put": [(201, "")],
            "complete": [(201, example("task-attachments.create"))],
            "legacy": [(201, example("task-attachments.create"))],
        }

    def route(self, request: httpx.Request) -> str:
        path = request.url.path
        if request.url.host != "api.taskadence.test":
            return "put"
        if path == "/v1/uploads":
            return "create"
        if path.endswith("/complete"):
            return "complete"
        return "legacy"

    def named(self, name: str) -> list[tuple[str, str, httpx.Headers, bytes]]:
        return [c for c in self.calls if c[0] == name]

    def __call__(self, request: httpx.Request) -> httpx.Response:
        name = self.route(request)
        self.calls.append((name, str(request.url), request.headers, request.content))
        queue = self.answers[name]
        answer = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(answer, Exception):
            raise answer
        status, body = answer
        if isinstance(body, (dict, list)):
            return httpx.Response(status, json=body)
        return httpx.Response(status, text=body)


@pytest.fixture
def fake() -> Fake:
    return Fake()


@pytest.fixture
def slept() -> list[float]:
    return []


@pytest.fixture
def tm(fake: Fake, slept: list[float]) -> Any:
    client = Taskadence(token=TOKEN, base_url=BASE, http_client=httpx.Client(transport=httpx.MockTransport(fake)))
    client._core._sleep = slept.append
    yield client
    client.close()


def body(raw: bytes) -> Any:
    return json.loads(raw)


# ---------------------------------------------------------------------------
# the happy path
# ---------------------------------------------------------------------------


def test_create_put_complete_returns_the_old_model(tm: Taskadence, fake: Fake) -> None:
    seen: list[tuple[int, int]] = []
    result = tm.task_attachments.create(
        task_id="T1",
        project_id="P1",
        file=("notes.txt", b"hello world"),
        title="Notes",
        progress=lambda *a: seen.append(a),
    )
    assert isinstance(result, models.TaskAttachmentInDB)
    assert [c[0] for c in fake.calls] == ["create", "put", "complete"]

    _, _, headers, raw = fake.named("create")[0]
    assert body(raw) == {
        "kind": "attachment",
        "task_id": "T1",
        "filename": "notes.txt",
        "size": 11,
        "content_type": "text/plain",
        "project_id": "P1",
    }
    assert headers["authorization"] == f"Bearer {TOKEN}"

    _, url, headers, raw = fake.named("put")[0]
    assert url == SAS_URL and raw == b"hello world"
    assert headers["x-ms-blob-type"] == "BlockBlob" and headers["content-length"] == "11"
    assert headers["content-type"] == "text/plain"
    assert "authorization" not in headers  # the API token never goes to storage
    assert "transfer-encoding" not in headers  # Put Blob needs a Content-Length

    _, url, _, raw = fake.named("complete")[0]
    assert url == f"{BASE}/v1/uploads/up_1/complete" and body(raw) == {"title": "Notes"}
    assert seen[-1] == (11, 11)


def test_project_files_take_the_same_flow(tm: Taskadence, fake: Fake, tmp_path: Path) -> None:
    fake.answers["complete"] = [(200, example("project-resources.upload"))]  # 200 or 201: both are the model
    path = tmp_path / "plan.pdf"
    path.write_bytes(b"%PDF-1.7 " + b"x" * 100)
    result = tm.project_resources.upload(project_id="P1", file=path)
    assert isinstance(result, models.ProjectResourceInDB)
    sent = body(fake.named("create")[0][3])
    assert sent == {
        "kind": "project_file",
        "project_id": "P1",
        "filename": "plan.pdf",
        "size": 109,
        "content_type": "application/pdf",
    }
    assert fake.named("put")[0][3] == path.read_bytes()
    assert fake.named("complete")[0][3] == b""  # no title: no body (`UploadCompleteIn` is optional)


def test_a_file_object_is_sent_from_where_it_stands(tm: Taskadence, fake: Fake) -> None:
    handle = io.BytesIO(b"HEADERpayload")
    handle.name = "data.csv"
    handle.seek(6)
    tm.task_attachments.create(task_id="T1", file=handle)
    assert body(fake.named("create")[0][3])["size"] == 7
    assert body(fake.named("create")[0][3])["filename"] == "data.csv"
    assert fake.named("put")[0][3] == b"payload"


# ---------------------------------------------------------------------------
# the fallback
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("status", [404, 405])
def test_an_api_without_direct_uploads_gets_multipart(tm: Taskadence, fake: Fake, status: int) -> None:
    fake.answers["create"] = [(status, problem(status, detail="Not Found"))]
    seen: list[tuple[int, int]] = []
    result = tm.task_attachments.create(task_id="T1", file=("a.txt", b"abc"), progress=lambda *a: seen.append(a))
    assert isinstance(result, models.TaskAttachmentInDB)
    assert [c[0] for c in fake.calls] == ["create", "legacy"]
    _, url, headers, raw = fake.named("legacy")[0]
    assert url == f"{BASE}/v1/task-attachments" and headers["content-type"].startswith("multipart/form-data")
    assert b'filename="a.txt"' in raw and b"abc" in raw
    assert seen == [(3, 3)]


def test_the_fallback_resends_a_file_object_from_its_start(tm: Taskadence, fake: Fake) -> None:
    fake.answers["create"] = [ROUTER_404]
    handle = io.BytesIO(b"whole file")
    tm.task_attachments.create(task_id="T1", file=("f.txt", handle))
    assert b"whole file" in fake.named("legacy")[0][3]


def test_is_inline_and_project_name_go_direct(tm: Taskadence, fake: Fake) -> None:
    tm.task_attachments.create(task_id="T1", file=("img.png", b"\x89PNG"), is_inline=True)
    assert body(fake.named("create")[0][3])["is_inline"] is True
    fake.answers["complete"] = [(201, example("project-resources.upload"))]
    tm.project_resources.upload(project_id="P1", project_name="Launch", file=("r.txt", b"r"))
    assert body(fake.named("create")[1][3])["project_name"] == "Launch"
    assert fake.named("legacy") == []


@pytest.mark.parametrize(
    "answer",
    [
        problem(404, detail="Not found"),  # an unreadable task (S.21: not disclosed)
        problem(404, detail="Project not found"),
        problem(404, "urn:taskadence:problem:not-found", "Not Found"),  # a typed problem, whatever its detail
    ],
)
def test_the_apis_own_404_is_raised_not_retried_as_multipart(tm: Taskadence, fake: Fake, answer: Any) -> None:
    fake.answers["create"] = [(404, answer)]
    with pytest.raises(errors.NotFoundError):
        tm.task_attachments.create(task_id="T404", file=("a.txt", b"abc"))
    assert [c[0] for c in fake.calls] == ["create"]


def test_a_404_that_is_not_the_apis_falls_back(tm: Taskadence, fake: Fake) -> None:
    fake.answers["create"] = [(404, "<html>not here</html>")]  # a gateway in front of an API without the route
    tm.task_attachments.create(task_id="T1", file=("a.txt", b"abc"))
    assert [c[0] for c in fake.calls] == ["create", "legacy"]


def test_complete_must_answer_the_model_of_the_kind(tm: Taskadence, fake: Fake) -> None:
    fake.answers["complete"] = [(201, example("project-resources.upload"))]  # a project file for an attachment
    with pytest.raises(errors.ResponseValidationError, match="expected TaskAttachmentInDB"):
        tm.task_attachments.create(task_id="T1", file=("a.txt", b"abc"))


def test_a_malformed_ticket_never_shows_the_signed_url(tm: Taskadence, fake: Fake) -> None:
    fake.answers["create"] = [(201, {"upload_url": SAS_URL})]  # no upload_id / headers / expires_at
    with pytest.raises(errors.ResponseValidationError) as caught:
        tm.task_attachments.create(task_id="T1", file=("a.txt", b"abc"))
    shown = f"{caught.value} {caught.value.body!r} {caught.value.__cause__!r} {caught.value.__context__!r}"
    assert SECRET not in shown and fake.named("put") == []


def test_a_stream_of_unknown_size_takes_the_old_route(tm: Taskadence, fake: Fake) -> None:
    class Pipe(io.RawIOBase):
        def __init__(self) -> None:
            self.data = b"streamed"

        def readable(self) -> bool:
            return True

        def readinto(self, buffer: Any) -> int:
            n = min(len(buffer), len(self.data))
            buffer[:n], self.data = self.data[:n], self.data[n:]
            return n

    tm.task_attachments.create(task_id="T1", file=("pipe.txt", Pipe()))
    assert [c[0] for c in fake.calls] == ["legacy"]


# ---------------------------------------------------------------------------
# the PUT: retries and failures
# ---------------------------------------------------------------------------


def test_a_5xx_put_is_retried_with_the_whole_file(tm: Taskadence, fake: Fake, slept: list[float]) -> None:
    fake.answers["put"] = [(503, "<Error><Code>ServerBusy</Code></Error>"), (500, ""), (201, "")]
    tm.task_attachments.create(task_id="T1", file=("a.txt", b"abcdef"))
    puts = fake.named("put")
    assert len(puts) == 3 and all(p[3] == b"abcdef" for p in puts)
    assert len(slept) == 2
    assert len(fake.named("complete")) == 1


def test_a_connection_failure_on_put_is_retried(tm: Taskadence, fake: Fake, slept: list[float]) -> None:
    fake.answers["put"] = [httpx.ConnectError("reset"), (201, "")]
    tm.task_attachments.create(task_id="T1", file=("a.txt", b"abc"))
    assert len(fake.named("put")) == 2 and len(slept) == 1


def test_an_expired_url_is_not_retried_and_never_shown(tm: Taskadence, fake: Fake, slept: list[float]) -> None:
    fake.answers["put"] = [(403, f"<Error><Code>AuthenticationFailed</Code><Message>{SAS_URL}</Message></Error>")]
    with pytest.raises(BlobUploadError) as caught:
        tm.task_attachments.create(task_id="T1", file=("a.txt", b"abc"))
    exc = caught.value
    assert exc.status == 403 and exc.code == "AuthenticationFailed" and exc.url == f"{BLOB}?<redacted>"
    assert SECRET not in str(exc) and SECRET not in repr(exc) and exc.__cause__ is None
    assert slept == [] and fake.named("complete") == []


def test_retries_run_out_with_a_redacted_error(tm: Taskadence, fake: Fake, slept: list[float]) -> None:
    fake.answers["put"] = [httpx.ConnectError(f"cannot reach {SAS_URL}")]
    with pytest.raises(BlobUploadError) as caught:
        tm.task_attachments.create(task_id="T1", file=("a.txt", b"abc"))
    assert SECRET not in str(caught.value) and caught.value.__cause__ is None
    assert caught.value.__suppress_context__
    assert len(fake.named("put")) == 4 and len(slept) == 3  # max_retries = 3


# ---------------------------------------------------------------------------
# refusals from the API
# ---------------------------------------------------------------------------


def test_too_large_is_refused_at_create_before_any_byte_is_sent(tm: Taskadence, fake: Fake) -> None:
    fake.answers["create"] = [
        (413, problem(413, "urn:taskadence:problem:upload-too-large", "The file is over 100 MB."))
    ]
    with pytest.raises(errors.TaskadenceError) as caught:
        tm.task_attachments.create(task_id="T1", file=("a.txt", b"abc"))
    assert caught.value.status == 413 and caught.value.slug == "upload-too-large"
    assert [c[0] for c in fake.calls] == ["create"]


def test_a_refusal_at_complete_is_the_sdk_error(tm: Taskadence, fake: Fake) -> None:
    fake.answers["complete"] = [
        (422, problem(422, "urn:taskadence:problem:upload-rejected", "The malware scan refused the file."))
    ]
    with pytest.raises(errors.UnprocessableEntityError) as caught:
        tm.task_attachments.create(task_id="T1", file=("a.txt", b"abc"))
    assert caught.value.slug == "upload-rejected" and caught.value.request_id == "req-123"
    assert "malware" in caught.value.detail


def test_storage_full_at_create_is_the_sdk_error(tm: Taskadence, fake: Fake) -> None:
    fake.answers["create"] = [(402, problem(402, "urn:taskadence:problem:storage-limit-reached", "Uploads paused."))]
    with pytest.raises(errors.TaskadenceError) as caught:
        tm.project_resources.upload(project_id="P1", file=b"x")
    assert caught.value.status == 402 and fake.named("put") == []


# ---------------------------------------------------------------------------
# the SAS URL stays out of logs
# ---------------------------------------------------------------------------


def test_redact_keeps_the_blob_and_drops_the_signature() -> None:
    assert redact(SAS_URL) == f"{BLOB}?<redacted>"
    assert redact(BLOB) == BLOB


def test_no_log_line_carries_the_signature(tm: Taskadence, fake: Fake, caplog: pytest.LogCaptureFixture) -> None:
    fake.answers["put"] = [(500, ""), (201, "")]
    with caplog.at_level(logging.DEBUG):
        tm.task_attachments.create(task_id="T1", file=("a.txt", b"abc"))
    lines = [r.getMessage() for r in caplog.records]
    assert any("blob.core.windows.net" in line for line in lines)  # the PUT was logged (by httpx and by us) …
    assert all(SECRET not in line for line in lines)  # … without its signature
    assert any(r.name == "httpx" and "<redacted>" in r.getMessage() for r in caplog.records)


# ---------------------------------------------------------------------------
# streaming: the file is never read whole
# ---------------------------------------------------------------------------


class ChunkOnly(io.BytesIO):
    """A file that refuses `read()` without a size (what a whole-file read would do)."""

    def __init__(self, data: bytes) -> None:
        super().__init__(data)
        self.largest = 0

    def read(self, size: int | None = -1) -> bytes:
        if size is None or size < 0:
            raise AssertionError("read() without a size: the file was read whole")
        self.largest = max(self.largest, size)
        return super().read(size)


def test_a_large_file_is_streamed_in_chunks(tm: Taskadence, fake: Fake) -> None:
    data = bytes(range(256)) * (5 * CHUNK_SIZE // 256 + 7)  # a bit over 5 MiB
    handle = ChunkOnly(data)
    seen: list[tuple[int, int]] = []
    tm.task_attachments.create(task_id="T1", file=("big.bin", handle), progress=lambda *a: seen.append(a))
    assert handle.largest == CHUNK_SIZE
    assert fake.named("put")[0][3] == data
    assert fake.named("put")[0][2]["content-length"] == str(len(data))
    assert len(seen) == 6 and seen[-1] == (len(data), len(data))


def test_a_path_is_opened_and_closed_here(tm: Taskadence, fake: Fake, tmp_path: Path, monkeypatch: Any) -> None:
    path = tmp_path / "x.txt"
    path.write_bytes(b"from disk")
    opened: list[Any] = []
    real_open = open

    def spy(*args: Any, **kwargs: Any) -> Any:
        handle = real_open(*args, **kwargs)
        opened.append(handle)
        return handle

    monkeypatch.setattr("builtins.open", spy)
    tm.task_attachments.create(task_id="T1", file=str(path))
    assert fake.named("put")[0][3] == b"from disk"
    assert opened and all(h.closed for h in opened)


# ---------------------------------------------------------------------------
# async
# ---------------------------------------------------------------------------


def make_async(fake: Fake, slept: list[float]) -> AsyncTaskadence:
    client = AsyncTaskadence(
        token=TOKEN, base_url=BASE, http_client=httpx.AsyncClient(transport=httpx.MockTransport(fake))
    )

    async def asleep(seconds: float) -> None:
        slept.append(seconds)

    client._core._asleep = asleep
    return client


@pytest.mark.anyio
async def test_async_create_put_complete(fake: Fake, slept: list[float]) -> None:
    fake.answers["put"] = [(502, ""), (201, "")]
    handle = ChunkOnly(b"y" * (CHUNK_SIZE + 5))
    seen: list[tuple[int, int]] = []
    async with make_async(fake, slept) as atm:
        result = await atm.task_attachments.create(
            task_id="T1", file=("y.bin", handle), title="Y", progress=lambda *a: seen.append(a)
        )
    assert isinstance(result, models.TaskAttachmentInDB)
    assert [c[0] for c in fake.calls] == ["create", "put", "put", "complete"]
    assert fake.named("put")[1][3] == b"y" * (CHUNK_SIZE + 5) and len(slept) == 1
    assert seen[-1] == (CHUNK_SIZE + 5, CHUNK_SIZE + 5)


@pytest.mark.anyio
async def test_async_falls_back_to_multipart(fake: Fake, slept: list[float]) -> None:
    fake.answers["create"] = [ROUTER_404]
    fake.answers["legacy"] = [(201, example("project-resources.upload"))]
    async with make_async(fake, slept) as atm:
        result = await atm.project_resources.upload(project_id="P1", file=("r.txt", b"abc"))
    assert isinstance(result, models.ProjectResourceInDB)
    assert [c[0] for c in fake.calls] == ["create", "legacy"]


@pytest.mark.anyio
async def test_async_refusal_at_complete(fake: Fake, slept: list[float]) -> None:
    fake.answers["complete"] = [(415, problem(415, "urn:taskadence:problem:upload-type-mismatch", "Not a PNG."))]
    async with make_async(fake, slept) as atm:
        with pytest.raises(errors.TaskadenceError) as caught:
            await atm.task_attachments.create(task_id="T1", file=("a.png", b"MZ"))
    assert caught.value.status == 415
