"""The SDK cannot drift from the spec: every public operationId has a facade method (sync and async), the facade's
operation table agrees with the generated client on method and URL, and the committed generated code is what the
generator produces from the committed spec (the CI regen check does the byte-for-byte version of that)."""

from __future__ import annotations

import importlib
import inspect
import re

import pytest

import tasksmate
from tasksmate import AsyncTasksMate, TasksMate
from tasksmate._operations import OPERATIONS
from tasksmate.resources import RESOURCE_METHODS

from .conftest import SPEC, TOKEN

SPEC_OPS = {
    op["operationId"]: (method.upper(), path) for path, item in SPEC["paths"].items() for method, op in item.items()
}


def test_every_public_operation_id_has_a_facade_method_sync_and_async() -> None:
    tm, atm = TasksMate(token=TOKEN), AsyncTasksMate(token=TOKEN)
    missing = []
    for op_id in SPEC_OPS:
        resource, verb = op_id.split(".", 1)
        attr = resource.replace("-", "_")
        for client in (tm, atm):
            method = getattr(getattr(client, attr, None), verb, None)
            if not callable(method):
                missing.append(f"{type(client).__name__}.{attr}.{verb}")
        assert inspect.iscoroutinefunction(getattr(getattr(atm, attr), verb)), op_id
    assert missing == []
    assert set(RESOURCE_METHODS) == set(SPEC_OPS) == set(OPERATIONS)


def test_the_operation_table_matches_the_spec() -> None:
    for op_id, (method, path) in SPEC_OPS.items():
        op = OPERATIONS[op_id]
        assert (op.method, op.path) == (method, path), op_id
        assert op.path_params == tuple(re.findall(r"\{(\w+)\}", path)), op_id


@pytest.mark.parametrize("op_id", sorted(SPEC_OPS))
def test_the_facade_and_the_generated_client_build_the_same_url(op_id: str) -> None:
    """Method + URL from the generated `_get_kwargs` equal the facade's, with the same path arguments."""
    op = OPERATIONS[op_id]
    module = importlib.import_module(op.parse.__module__)  # type: ignore[union-attr]
    signature = inspect.signature(module._get_kwargs)
    args = {name: f"{name.upper()}/1" for name in op.path_params}
    kwargs = {}
    for name, param in signature.parameters.items():
        if param.default is inspect.Parameter.empty and name not in args:
            kwargs[name] = object() if name != "body" else _Body()
    generated = module._get_kwargs(*args.values(), **kwargs)
    ours = tasksmate.TasksMate(token=TOKEN)._core._build(
        op, path=tuple(args.values()), body={} if op.body == "json" else None
    )
    assert generated["method"].upper() == ours.method
    assert generated["url"] == ours.url


class _Body:
    def to_dict(self) -> dict[str, object]:
        return {}

    def to_multipart(self) -> list[object]:
        return []


def test_every_list_is_a_page_and_every_create_is_idempotent() -> None:
    lists = {k for k, op in OPERATIONS.items() if op.is_list}
    creates = {k for k, op in OPERATIONS.items() if op.is_create}
    assert {"tasks.list", "views.rows", "projects.list", "webhooks.deliveries", "audit.list"} <= lists
    assert creates == {"tasks.create", "projects.create", "goals.create", "task-comments.create", "task-comments.reply"}
    for op_id in lists:
        assert OPERATIONS[op_id].item is not None, op_id


def test_generated_files_say_do_not_edit() -> None:
    from pathlib import Path

    generated = Path(tasksmate.__file__).parent / "_generated"
    offenders = [
        p.name for p in generated.rglob("*.py") if "DO NOT EDIT BY HAND" not in p.read_text().split("\n", 2)[0]
    ]
    assert offenders == []
    for name in ("_operations.py", "resources.py"):
        assert "DO NOT EDIT BY HAND" in (Path(tasksmate.__file__).parent / name).read_text().split("\n", 1)[0]


def test_the_sdk_knows_its_api_version_and_default_server() -> None:
    assert tasksmate.API_VERSION == SPEC["info"]["version"] == "2026-09-25"
    assert SPEC["servers"][0]["url"] == tasksmate.DEFAULT_BASE_URL
