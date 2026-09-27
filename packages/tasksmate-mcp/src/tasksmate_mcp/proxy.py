"""The bridge: MCP over stdio on one side, the remote server over Streamable HTTP on the other.

Every JSON-RPC message the client writes goes to the server unchanged (`initialize` included — the server is
stateless), and every message the server answers goes back unchanged; `tools/list` is the server's list. The SDK's
own transports do the protocol work (`mcp.server.stdio.stdio_server`, `mcp.client.streamable_http`).

One thing is added: an HTTP refusal becomes a JSON-RPC error. The SDK's HTTP client turns a non-2xx answer into an
exception that no request is waiting for — the client would hang. `ProblemTransport` (an httpx transport wrapper)
answers such a POST itself with a JSON-RPC error for THAT request id: a 401 names `TASKSMATE_TOKEN` (never its value),
a 400 carries the server's problem detail (an unknown group), anything else the status and detail; an unreachable
server says so. Each also writes one line to stderr. stdout carries JSON-RPC only.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from typing import Any, TextIO

import anyio
import httpx
from anyio.abc import ObjectReceiveStream, ObjectSendStream
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.message import SessionMessage
from mcp.types import JSONRPCError, JSONRPCRequest, JSONRPCResponse

from ._version import __version__
from .config import TOKEN_ENV, Config, redact

UNAUTHORIZED = -32001  # JSON-RPC implementation-defined server errors: -32000 … -32099
HTTP_ERROR = -32002
UNREACHABLE = -32003
DRAIN_SECONDS = 30.0  # after stdin closes: how long answers still in flight are waited for

Log = Callable[[str], None]


def stderr_log(line: str) -> None:
    print(f"tasksmate-mcp: {redact(line)}", file=sys.stderr, flush=True)


def _problem(response_body: bytes) -> dict[str, Any]:
    try:
        body = json.loads(response_body or b"{}")
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


def _jsonrpc_error(request_id: Any, code: int, message: str, data: dict[str, Any]) -> httpx.Response:
    payload = {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": redact(message), "data": data}}
    return httpx.Response(200, headers={"content-type": "application/json"}, content=json.dumps(payload).encode())


class ProblemTransport(httpx.AsyncBaseTransport):
    """Wraps the real transport: a refused or failed POST of a request is answered with a JSON-RPC error."""

    def __init__(self, inner: httpx.AsyncBaseTransport, log: Log = stderr_log) -> None:
        self._inner = inner
        self._log = log

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        rpc = self._rpc(request)
        try:
            response = await self._inner.handle_async_request(request)
        except httpx.TransportError as exc:
            if rpc is None:
                raise
            where = f"{request.url.scheme}://{request.url.host}" + (f":{request.url.port}" if request.url.port else "")
            self._log(f"cannot reach {where} ({type(exc).__name__}) — check TASKSMATE_API_URL and the network")
            return self._answer(rpc, UNREACHABLE, f"TasksMate MCP server unreachable at {where}", {"url": where})
        if rpc is None or response.status_code < 400:
            return response
        body = await response.aread()
        await response.aclose()
        problem = _problem(body)
        detail = str(problem.get("detail") or problem.get("title") or response.reason_phrase)
        data: dict[str, Any] = {
            "status": response.status_code,
            **{k: problem[k] for k in ("type", "title", "detail", "errors", "request_id") if k in problem},
        }
        if response.status_code == 401:
            self._log(f"the server refused {TOKEN_ENV} (401): {detail}")
            message = (
                f"TasksMate refused the access token in {TOKEN_ENV} (401): {detail}. Create one in Developers → Tokens."
            )
            return self._answer(rpc, UNAUTHORIZED, message, data)
        self._log(f"the server answered {response.status_code}: {detail}")
        return self._answer(rpc, HTTP_ERROR, f"TasksMate MCP server: {response.status_code} {detail}", data)

    @staticmethod
    def _rpc(request: httpx.Request) -> dict[str, Any] | None:
        """The JSON-RPC message a POST carries, or None (a GET / DELETE, or a body that is not JSON)."""
        if request.method != "POST":
            return None
        try:
            body = json.loads(request.content or b"null")
        except ValueError:
            return None
        return body if isinstance(body, dict) else None

    @staticmethod
    def _answer(rpc: dict[str, Any], code: int, message: str, data: dict[str, Any]) -> httpx.Response:
        if "id" not in rpc or "method" not in rpc:  # a notification (or a response): nothing waits for an answer
            return httpx.Response(202)
        return _jsonrpc_error(rpc["id"], code, message, data)

    async def aclose(self) -> None:
        await self._inner.aclose()


def http_client(
    config: Config, *, transport: httpx.AsyncBaseTransport | None = None, log: Log = stderr_log
) -> httpx.AsyncClient:
    """The client the SDK's Streamable HTTP transport uses: the bearer, our User-Agent, MCP's timeouts."""
    inner = transport or httpx.AsyncHTTPTransport()
    return httpx.AsyncClient(
        transport=ProblemTransport(inner, log),
        headers={"Authorization": f"Bearer {config.token}", "User-Agent": f"tasksmate-mcp/{__version__} (python)"},
        timeout=httpx.Timeout(30.0, read=300.0),
        follow_redirects=False,
    )


async def bridge(
    client_read: ObjectReceiveStream[SessionMessage | Exception],
    client_write: ObjectSendStream[SessionMessage],
    config: Config,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    log: Log = stderr_log,
) -> None:
    """Forward messages both ways until the client closes its side (stdin EOF); then answer what is still in flight
    (at most `DRAIN_SECONDS`) and close the client's side, so the process ends."""
    pending: set[Any] = set()  # ids of requests sent upstream and not answered yet
    async with (
        client_write,
        http_client(config, transport=transport, log=log) as http,
        streamable_http_client(config.mcp_url, http_client=http, terminate_on_close=False) as (
            server_read,
            server_write,
            _,
        ),
        anyio.create_task_group() as tg,
    ):

        async def upstream() -> None:
            async for message in client_read:
                if isinstance(message, Exception):
                    log(f"ignored a message that is not JSON-RPC: {type(message).__name__}")
                    continue
                if isinstance(message.message.root, JSONRPCRequest):
                    pending.add(message.message.root.id)
                await server_write.send(message)
            with anyio.move_on_after(DRAIN_SECONDS):
                while pending:
                    await anyio.sleep(0.02)
            tg.cancel_scope.cancel()

        async def downstream() -> None:
            async for message in server_read:
                if isinstance(message, Exception):
                    log(f"transport error: {type(message).__name__}: {message}")
                    continue
                if isinstance(message.message.root, JSONRPCResponse | JSONRPCError):
                    pending.discard(message.message.root.id)
                await client_write.send(message)

        tg.start_soon(upstream)
        tg.start_soon(downstream)


async def run_proxy(config: Config, *, stdin: TextIO | None = None, stdout: TextIO | None = None) -> None:
    """stdio ↔ the remote server, for the life of the process."""
    from mcp.server.stdio import stdio_server

    stdin_stream = anyio.wrap_file(stdin) if stdin is not None else None
    stdout_stream = anyio.wrap_file(stdout) if stdout is not None else None
    async with stdio_server(stdin_stream, stdout_stream) as (read, write):
        await bridge(read, write, config)
