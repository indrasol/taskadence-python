"""Shared fixtures. No test touches the network: every HTTP call goes to `respx`, and response bodies come from the
spec snapshot's own examples (`spec/openapi.public.json`) — the snapshot is the only input."""

from __future__ import annotations

import copy
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import respx

from tasksmate import AsyncTasksMate, TasksMate

BASE = "https://api.tasksmate.test"
TOKEN = "tm_live_" + "x" * 43  # a well-formed, fake access token
FULL_SPEC: dict[str, Any] = json.loads(
    (Path(__file__).resolve().parent.parent / "spec" / "openapi.public.json").read_text()
)
# What the SDK is generated from (scripts/generate.py `sdk_spec`): the snapshot without the OAuth protocol operations.
SPEC: dict[str, Any] = {
    **FULL_SPEC,
    "paths": {
        path: kept
        for path, item in FULL_SPEC["paths"].items()
        if (kept := {m: op for m, op in item.items() if op.get("x-kind") != "oauth"})
    },
}


def operation(op_id: str) -> tuple[str, str, dict[str, Any]]:
    for path, item in SPEC["paths"].items():
        for method, op in item.items():
            if op["operationId"] == op_id:
                return method.upper(), path, op
    raise KeyError(op_id)


def example(op_id: str) -> Any:
    """The spec's 2xx JSON example for `op_id` (a deep copy)."""
    _, _, op = operation(op_id)
    status = next(s for s in op["responses"] if s.startswith("2"))
    return copy.deepcopy(op["responses"][status]["content"]["application/json"]["example"])


def task(task_id: str = "T000001", **fields: Any) -> dict[str, Any]:
    body = example("tasks.read")
    body.update({"task_id": task_id, **fields})
    return body


def card(task_id: str, **fields: Any) -> dict[str, Any]:
    body = example("tasks.list")["data"][0]
    body.update({"task_id": task_id, **fields})
    return body


def problem(status: int, type_: str = "about:blank", detail: Any = "nope", **extra: Any) -> dict[str, Any]:
    return {
        "type": type_,
        "title": "x",
        "status": status,
        "detail": detail,
        "instance": "/v1/x",
        "request_id": "req-123",
        **extra,
    }


@pytest.fixture
def api() -> Iterator[respx.MockRouter]:
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        yield router


@pytest.fixture
def slept() -> list[float]:
    return []


@pytest.fixture
def tm(api: respx.MockRouter, slept: list[float]) -> Iterator[TasksMate]:
    client = TasksMate(token=TOKEN, base_url=BASE)
    client._core._sleep = slept.append  # no real waiting; the delays are asserted
    yield client
    client.close()


@pytest.fixture
async def atm(api: respx.MockRouter, slept: list[float]) -> Any:
    client = AsyncTasksMate(token=TOKEN, base_url=BASE)

    async def asleep(seconds: float) -> None:
        slept.append(seconds)

    client._core._asleep = asleep
    yield client
    await client.close()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
