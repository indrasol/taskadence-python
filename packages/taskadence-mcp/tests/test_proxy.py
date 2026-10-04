"""taskadence-mcp (task 5.3): the stdio ↔ Streamable HTTP proxy.

An MCP client (the SDK's `ClientSession` over in-memory streams — what stdio carries) → `bridge` → a fake remote
server (the SDK's low-level `Server` behind `StreamableHTTPSessionManager`, stateless JSON, reached through
`httpx.ASGITransport`). The fake enforces `readonly` / `groups` and the bearer itself, as the real server does: the
proxy only forwards. Plus: 401 / 400 / unreachable become JSON-RPC errors, the process writes nothing but JSON-RPC
to stdout and never the token, and the package holds no tool code.
"""

from __future__ import annotations

import ast
import json
import os
import socket
import subprocess
import sys
import warnings
from pathlib import Path
from typing import Any

import anyio
import httpx
import pytest
from mcp import ClientSession, types
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.shared.exceptions import McpError
from mcp.shared.message import SessionMessage
from starlette.requests import Request
from starlette.responses import JSONResponse

from taskadence_mcp import proxy
from taskadence_mcp.config import LEGACY_ENV_PREFIX, Config, ConfigError, load_config, redact

TOKEN = "tkd_live_" + "S3cret" * 7 + "x"
API = "http://api.test"

TOOLS = {
    "whoami": ("me", True),
    "list_my_tasks": ("tasks", True),
    "create_task": ("tasks", False),
    "list_projects": ("projects", True),
}


class FakeRemote:
    """The remote server's contract, in miniature: bearer required, `?readonly=1` and `?groups=` enforced."""

    def __init__(self) -> None:
        self.seen: list[dict[str, Any]] = []
        self.server: Server = Server("taskadence")
        self.manager = StreamableHTTPSessionManager(app=self.server, stateless=True, json_response=True)

        def enabled(request: Request) -> set[str]:
            readonly = request.query_params.get("readonly") == "1"
            groups = set((request.query_params.get("groups") or "tasks,projects").split(",")) | {"me"}
            return {n for n, (g, ro) in TOOLS.items() if g in groups and (ro or not readonly)}

        @self.server.list_tools()
        async def list_tools() -> list[types.Tool]:
            names = enabled(self.server.request_context.request)  # type: ignore[arg-type]
            return [types.Tool(name=n, inputSchema={"type": "object"}) for n in TOOLS if n in names]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
            if name not in enabled(self.server.request_context.request):  # type: ignore[arg-type]
                raise ValueError(f"Read-only connection: `{name}` writes")
            return [types.TextContent(type="text", text=f"{name} ok")]

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        request = Request(scope, receive)
        self.seen.append(
            {
                "auth": request.headers.get("authorization"),
                "query": str(request.query_params),
                "ua": request.headers.get("user-agent"),
                "method": request.method,
            }
        )
        if request.headers.get("authorization") != f"Bearer {TOKEN}":
            await JSONResponse(
                {
                    "type": "about:blank",
                    "title": "Unauthorized",
                    "status": 401,
                    "detail": "The access token is not valid",
                    "request_id": "r-1",
                },
                status_code=401,
                media_type="application/problem+json",
            )(scope, receive, send)
            return
        groups = request.query_params.get("groups")
        if groups and not set(groups.split(",")) <= {"tasks", "projects", "me", "admin"}:
            await JSONResponse(
                {
                    "type": "urn:taskadence:problem:invalid-parameter",
                    "title": "Bad Request",
                    "status": 400,
                    "detail": f"groups must be a comma-separated list of: tasks, projects; got {groups}",
                },
                status_code=400,
                media_type="application/problem+json",
            )(scope, receive, send)
            return
        await self.manager.handle_request(scope, receive, send)


async def through_proxy(
    remote: FakeRemote,
    config: Config,
    use,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    logs: list[str] | None = None,
) -> Any:
    """`use(session)` with a ClientSession whose streams run through `proxy.bridge` to `remote`."""
    to_proxy_send, to_proxy_recv = anyio.create_memory_object_stream[SessionMessage | Exception](16)
    to_client_send, to_client_recv = anyio.create_memory_object_stream[SessionMessage](16)
    log = (logs if logs is not None else []).append
    result: Any = None
    async with remote.manager.run(), anyio.create_task_group() as tg:
        tg.start_soon(
            lambda: proxy.bridge(
                to_proxy_recv, to_client_send, config, transport=transport or httpx.ASGITransport(app=remote), log=log
            )
        )
        async with ClientSession(to_client_recv, to_proxy_send) as session:
            result = await use(session)
        await to_proxy_send.aclose()
    return result


def cfg(**kw: Any) -> Config:
    return Config(token=kw.pop("token", TOKEN), api_url=API, **kw)


# ---------------------------------------------------------------------------
# Forwarding
# ---------------------------------------------------------------------------


def test_initialize_list_and_call_are_the_remote_servers_with_the_bearer():
    remote = FakeRemote()

    async def use(session: ClientSession) -> Any:
        init = await session.initialize()
        tools = await session.list_tools()
        called = await session.call_tool("create_task", {"title": "x"})
        return init, tools, called

    init, tools, called = anyio.run(through_proxy, remote, cfg(), use)
    assert init.serverInfo.name == "taskadence"
    assert [t.name for t in tools.tools] == ["whoami", "list_my_tasks", "create_task", "list_projects"]
    assert called.isError is False and called.content[0].text == "create_task ok"
    posts = [s for s in remote.seen if s["method"] == "POST"]
    assert posts and all(s["auth"] == f"Bearer {TOKEN}" and s["query"] == "" for s in posts)
    assert all(s["ua"].startswith("taskadence-mcp/") for s in posts)


def test_readonly_and_groups_are_forwarded_as_the_query_and_the_server_refuses_the_write():
    remote = FakeRemote()

    async def use(session: ClientSession) -> Any:
        await session.initialize()
        return await session.list_tools(), await session.call_tool("create_task", {"title": "x"})

    tools, called = anyio.run(through_proxy, remote, cfg(readonly=True, groups=("tasks",)), use)
    assert [t.name for t in tools.tools] == ["whoami", "list_my_tasks"]
    assert called.isError is True and "Read-only connection" in called.content[0].text
    assert {s["query"] for s in remote.seen if s["method"] == "POST"} == {"readonly=1&groups=tasks"}


def test_a_refused_token_is_a_jsonrpc_error_naming_the_variable_never_the_value():
    remote = FakeRemote()
    logs: list[str] = []
    wrong = "tkd_live_" + "W" * 43

    async def use(session: ClientSession) -> Any:
        with pytest.raises(McpError) as caught:
            await session.initialize()
        return caught.value.error

    error = anyio.run(lambda: through_proxy(remote, cfg(token=wrong), use, logs=logs))
    assert error.code == proxy.UNAUTHORIZED
    assert "TASKADENCE_TOKEN" in error.message and "401" in error.message and "not valid" in error.message
    assert error.data["status"] == 401 and error.data["request_id"] == "r-1"
    assert logs == ["the server refused TASKADENCE_TOKEN (401): The access token is not valid"]
    assert wrong not in json.dumps(error.model_dump()) + " ".join(logs)


def test_a_400_carries_the_servers_detail():
    async def use(session: ClientSession) -> Any:
        with pytest.raises(McpError) as caught:
            await session.initialize()
        return caught.value.error

    error = anyio.run(through_proxy, FakeRemote(), cfg(groups=("nope",)), use)
    assert error.code == proxy.HTTP_ERROR and "400" in error.message and "got nope" in error.message
    assert error.data["type"] == "urn:taskadence:problem:invalid-parameter"


def test_an_unreachable_server_is_a_jsonrpc_error_not_a_hang():
    class Down(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("refused", request=request)

    logs: list[str] = []

    async def use(session: ClientSession) -> Any:
        with anyio.fail_after(10), pytest.raises(McpError) as caught:
            await session.initialize()
        return caught.value.error

    error = anyio.run(lambda: through_proxy(FakeRemote(), cfg(), use, transport=Down(), logs=logs))
    assert error.code == proxy.UNREACHABLE and "http://api.test" in error.message
    assert logs and "cannot reach http://api.test" in logs[0]


def test_a_notification_that_is_refused_gets_no_answer():
    response = proxy.ProblemTransport._answer({"jsonrpc": "2.0", "method": "notifications/initialized"}, -1, "x", {})
    assert response.status_code == 202


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def test_flags_win_over_the_environment_and_the_url_is_the_servers_contract():
    env = {
        "TASKADENCE_TOKEN": TOKEN,
        "TASKADENCE_API_URL": "https://dev.example/v1/",
        "TASKADENCE_MCP_READONLY": "true",
        "TASKADENCE_MCP_GROUPS": "Tasks, projects",
    }
    c = load_config(environ=env)
    assert (c.api_url, c.readonly, c.groups) == ("https://dev.example", True, ("tasks", "projects"))
    assert c.mcp_url == "https://dev.example/mcp?readonly=1&groups=tasks,projects"
    c = load_config(api_url="http://localhost:8000/mcp", readonly=False, groups="views", environ=env)
    assert c.mcp_url == "http://localhost:8000/mcp?groups=views"
    assert load_config(environ={"TASKADENCE_TOKEN": TOKEN}).mcp_url == "https://api.taskadence.com/mcp"
    assert load_config(environ={"TASKADENCE_TOKEN": TOKEN, "TASKADENCE_MCP_GROUPS": ""}).groups is None
    assert TOKEN not in repr(c)


@pytest.mark.parametrize(
    "env,match",
    [
        ({}, "TASKADENCE_TOKEN is not set"),
        ({"TASKADENCE_TOKEN": TOKEN, "TASKADENCE_MCP_READONLY": "maybe"}, "TASKADENCE_MCP_READONLY must be 1 or 0"),
        ({"TASKADENCE_TOKEN": TOKEN, "TASKADENCE_API_URL": "ftp://x"}, "must start with http"),
    ],
)
def test_a_bad_configuration_is_refused_with_a_message_that_names_no_token(env, match):
    with pytest.raises(ConfigError, match=match) as caught:
        load_config(environ=env)
    assert TOKEN not in str(caught.value)


# The 5.8 rename: the pre-rename TASKSMATE_* variables and tm_live_ tokens still work.
LEGACY_TOKEN = "tm_live_" + "L3gacy" * 7 + "x"


def test_a_legacy_variable_is_read_with_a_deprecation_warning_and_the_new_name_wins():
    legacy = {
        "TASKSMATE_TOKEN": LEGACY_TOKEN,
        "TASKSMATE_API_URL": "https://dev.example",
        "TASKSMATE_MCP_READONLY": "1",
        "TASKSMATE_MCP_GROUPS": "tasks",
    }
    with pytest.warns(DeprecationWarning) as caught:
        c = load_config(environ=legacy)
    assert (c.token, c.mcp_url) == (LEGACY_TOKEN, "https://dev.example/mcp?readonly=1&groups=tasks")
    assert sorted(str(w.message).split(" ")[0] for w in caught) == sorted(legacy)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert (
            load_config(
                environ={
                    **legacy,
                    "TASKADENCE_TOKEN": TOKEN,
                    "TASKADENCE_API_URL": "http://x",
                    "TASKADENCE_MCP_READONLY": "0",
                    "TASKADENCE_MCP_GROUPS": "views",
                }
            ).token
            == TOKEN
        )


def test_both_token_prefixes_are_redacted():
    assert redact(f"a {TOKEN} b {LEGACY_TOKEN} c tkd_test_abc") == "a tkd_… b tkd_… c tkd_…"


def test_the_process_reads_a_legacy_token_and_says_so_on_stderr_without_it():
    done = _run(["--api-url", f"http://127.0.0.1:{_free_port()}"], "", {"TASKSMATE_TOKEN": LEGACY_TOKEN})
    assert "warning: TASKSMATE_TOKEN is deprecated" in done.stderr and "TASKADENCE_TOKEN" in done.stderr
    assert "is not set" not in done.stderr and LEGACY_TOKEN not in done.stdout + done.stderr


# ---------------------------------------------------------------------------
# The process: stdout is JSON-RPC only, the token is never written
# ---------------------------------------------------------------------------


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _run(args: list[str], stdin: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    base = {k: v for k, v in os.environ.items() if not k.startswith(("TASKADENCE_", LEGACY_ENV_PREFIX))}
    return subprocess.run(
        [sys.executable, "-m", "taskadence_mcp", *args],
        input=stdin,
        capture_output=True,
        text=True,
        env={**base, **env},
        timeout=60,
        check=False,
    )


def test_the_process_writes_only_jsonrpc_to_stdout_and_never_the_token():
    init = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}},
    }
    done = _run(
        ["--api-url", f"http://127.0.0.1:{_free_port()}", "--readonly"],
        json.dumps(init) + "\n",
        {"TASKADENCE_TOKEN": TOKEN},
    )
    lines = [line for line in done.stdout.splitlines() if line.strip()]
    assert lines, done.stderr
    messages = [json.loads(line) for line in lines]  # every stdout line is JSON…
    assert all(m.get("jsonrpc") == "2.0" for m in messages)  # …and JSON-RPC
    assert messages[0]["id"] == 1 and messages[0]["error"]["code"] == proxy.UNREACHABLE
    assert "cannot reach http://127.0.0.1" in done.stderr and "proxying stdio to" in done.stderr
    assert TOKEN not in done.stdout + done.stderr


def test_the_process_without_a_token_exits_2_saying_so_on_stderr():
    done = _run([], "", {})
    assert done.returncode == 2 and done.stdout == "" and "TASKADENCE_TOKEN is not set" in done.stderr


# ---------------------------------------------------------------------------
# A proxy only
# ---------------------------------------------------------------------------

SRC = Path(__file__).resolve().parents[1] / "src" / "taskadence_mcp"


def test_the_package_holds_no_tool_definitions_and_imports_no_server_or_sdk_code():
    """The tools are the remote server's: no server framework, no tool registry, no Taskadence SDK or backend code."""
    banned_modules = ("mcp.server.lowlevel", "mcp.server.fastmcp", "mcp.server.mcpserver", "taskadence", "app")
    for path in SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            for name in names:
                assert not any(name == b or name.startswith(b + ".") for b in banned_modules), (
                    f"{path.name} imports {name}"
                )
            if isinstance(node, ast.Attribute):
                assert node.attr not in ("list_tools", "call_tool", "Tool"), (
                    f"{path.name} defines or builds tools ({node.attr})"
                )
    assert (SRC / "proxy.py").read_text().count("streamable_http_client") >= 1
