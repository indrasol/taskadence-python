"""The SDK cannot drift from the spec: every public operationId has a facade method (sync and async), the facade's
operation table agrees with the generated client on method and URL, and the committed generated code is what the
generator produces from the committed spec (the CI regen check does the byte-for-byte version of that)."""

from __future__ import annotations

import importlib
import inspect
import re
import sys
from typing import Any

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


# ---------------------------------------------------------------------------
# 4.1b — the spec is generated from as-is: no update-defaults strip, no leaked parameters, kinds from `x-kind`
# ---------------------------------------------------------------------------


def _generator() -> Any:
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parent.parent / "scripts" / "generate.py"
    spec = importlib.util.spec_from_file_location("tasksmate_generate", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # its dataclasses look their module up
    spec.loader.exec_module(module)
    return module


def test_the_committed_spec_passes_the_generators_guard() -> None:
    _generator().check_spec(SPEC)


@pytest.mark.parametrize(
    ("breakage", "message"),
    [
        (
            lambda s: s["components"]["schemas"]["TaskUpdate"]["properties"]["priority"].update(default="none"),
            "TaskUpdate.priority has default 'none'",
        ),
        (
            lambda s: s["paths"]["/v1/tasks/{task_id}"]["get"]["parameters"].append(
                {"name": "is_registration", "in": "query", "schema": {"type": "boolean"}}
            ),
            "parameter is_registration",
        ),
    ],
)
def test_the_generator_refuses_a_spec_that_regressed(breakage: Any, message: str) -> None:
    """The 4.5 transform stripped update-body defaults before generating; 4.1b fixed the backend and removed it. If the
    backend ever advertises one again (or leaks `verify_token`'s parameters), generation stops instead of shipping a
    client whose `TaskUpdate(status=…)` also resets priority and type."""
    import copy

    broken = copy.deepcopy(SPEC)
    breakage(broken)
    with pytest.raises(SystemExit, match=re.escape(message)):
        _generator().check_spec(broken)


def test_update_bodies_in_the_spec_carry_no_defaults_and_the_generated_model_sends_only_what_is_set() -> None:
    from tasksmate._generated.models import TaskUpdate

    schema = SPEC["components"]["schemas"]["TaskUpdate"]["properties"]
    assert [name for name, prop in schema.items() if prop.get("default") is not None] == []
    assert TaskUpdate(status="in_progress").to_dict() == {"status": "in_progress"}


def test_list_and_create_come_from_x_kind() -> None:
    kinds = {op["operationId"]: op.get("x-kind", "") for item in SPEC["paths"].values() for op in item.values()}
    assert {k for k, v in kinds.items() if v == "list"} == {k for k, op in OPERATIONS.items() if op.is_list}
    assert {k for k, v in kinds.items() if v == "create"} == {k for k, op in OPERATIONS.items() if op.is_create}
