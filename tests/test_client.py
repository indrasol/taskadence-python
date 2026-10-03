"""Configuration, request building, typed responses, conditional requests and idempotency — through `respx`."""

from __future__ import annotations

import datetime as dt
import json
import platform
import uuid

import httpx
import pytest
import respx

import taskadence
from taskadence import AUTO, NotModified, Taskadence, models
from taskadence.errors import PreconditionFailedError

from .conftest import BASE, TOKEN, card, example, task

# ---------------------------------------------------------------------------
# configuration
# ---------------------------------------------------------------------------


def test_token_and_base_url_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TASKADENCE_TOKEN", TOKEN)
    monkeypatch.setenv("TASKADENCE_API_URL", "https://example.test/v1/")
    tm = Taskadence()
    assert tm.base_url == "https://example.test"  # a trailing /v1 (and slash) is accepted
    monkeypatch.delenv("TASKADENCE_API_URL")
    assert Taskadence().base_url == taskadence.DEFAULT_BASE_URL


def test_no_token_is_a_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TASKADENCE_TOKEN", raising=False)
    with pytest.raises(taskadence.ConfigurationError, match="TASKADENCE_TOKEN"):
        Taskadence()
    with pytest.raises(taskadence.ConfigurationError, match="http"):
        Taskadence(token=TOKEN, base_url="api.example.test")


def test_the_token_is_never_in_a_repr() -> None:
    tm = Taskadence(token=TOKEN, base_url=BASE)
    assert TOKEN not in repr(tm) and TOKEN not in repr(tm._core) and TOKEN not in repr(tm.tasks)


def test_every_request_carries_auth_user_agent_and_api_version(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.get("/v1/me").respond(json=example("me.read"))
    tm.me()
    headers = route.calls.last.request.headers
    assert headers["authorization"] == f"Bearer {TOKEN}"
    assert headers["user-agent"] == f"taskadence-python/{taskadence.__version__} python/{platform.python_version()}"
    assert headers["taskadence-version"] == "2026-09-25"


def test_me_is_callable_and_typed(tm: Taskadence, api: respx.MockRouter) -> None:
    api.get("/v1/me").respond(json=example("me.read"))
    me = tm.me()
    assert isinstance(me, models.MeOut)
    assert tm.me.read().to_dict() == me.to_dict()


def test_context_manager_closes(api: respx.MockRouter) -> None:
    with Taskadence(token=TOKEN, base_url=BASE) as tm:
        assert not tm._core._http.is_closed
    assert tm._core._http.is_closed


# ---------------------------------------------------------------------------
# request building
# ---------------------------------------------------------------------------


def test_path_arguments_are_quoted(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.get(url__regex=r"/v1/tasks/.*").respond(json=task())
    tm.tasks.read("T 1/2")
    assert route.calls.last.request.url.raw_path == b"/v1/tasks/T%201%2F2"


def test_only_what_the_caller_passed_is_sent_filters_are_comma_joined(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.get("/v1/tasks").respond(json={"data": [], "next_cursor": None})
    tm.tasks.list(
        org_id="O0020",
        filter={"status": ["in_progress", "blocked"], "overdue": True, "search": "a, b"},
        sort_by="due_date",
        include_inaccessible=False,
    )
    params = route.calls.last.request.url.params
    assert dict(params) == {
        "org_id": "O0020",
        "filter[status]": "in_progress,blocked",
        "filter[overdue]": "true",
        "filter[search]": "a, b",
        "sort_by": "due_date",
        "include_inaccessible": "false",
    }
    assert "is_registration" not in params and "offset" not in params and "limit" not in params


def test_an_unknown_filter_key_names_the_allowed_ones(tm: Taskadence) -> None:
    with pytest.raises(ValueError, match=r"unknown filter key\(s\) colour; allowed: status, priority"):
        tm.tasks.list(org_id="O0020", filter={"colour": "red"})


def test_a_model_body_sends_only_what_was_set(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.patch("/v1/tasks/T1").respond(json=task("T1", status="completed"))
    tm.tasks.update("T1", models.TaskUpdate(status="completed", due_date=None))
    # null clears; nothing else is sent. 4.1b: the spec's TaskUpdate carries no defaults any more (the generator's strip
    # is gone), so this is the generated model as-is — a regression in the backend fails here and in test_drift.py
    assert json.loads(route.calls.last.request.content) == {"status": "completed", "due_date": None}


def test_a_mapping_body_is_sent_as_is_with_dates_encoded(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.post("/v1/tasks").respond(json=task("T2"))
    created = tm.tasks.create({"org_id": "O0020", "title": "Ship", "due_date": dt.date(2026, 10, 1)})
    assert json.loads(route.calls.last.request.content) == {
        "org_id": "O0020",
        "title": "Ship",
        "due_date": "2026-10-01",
    }
    assert isinstance(created, models.TaskInDB) and created.task_id == "T2"


def test_uploads_are_multipart_with_the_file(tm: Taskadence, api: respx.MockRouter, tmp_path: object) -> None:
    route = api.post("/v1/task-attachments").respond(201, json=example("task-attachments.create"))
    tm.task_attachments.create(task_id="T1", file=("notes.txt", b"hello"), title="Notes")
    body = route.calls.last.request.content
    assert b'name="task_id"' in body and b"T1" in body and b'filename="notes.txt"' in body and b"hello" in body
    assert route.calls.last.request.headers["content-type"].startswith("multipart/form-data")


def test_the_upload_sends_project_id_once_as_the_query(tm: Taskadence, api: respx.MockRouter) -> None:
    """4.1b: the spec declares `project_id` once (the query the permission check reads); it used to be a form field too,
    and the facade sent it in both places."""
    route = api.post("/v1/project-resources/upload").respond(201, json=example("project-resources.upload"))
    tm.project_resources.upload(project_id="P1", file=b"x")
    request = route.calls.last.request
    assert request.url.params["project_id"] == "P1" and b'name="project_id"' not in request.content
    assert b'name="file"' in request.content


# ---------------------------------------------------------------------------
# idempotency
# ---------------------------------------------------------------------------


def test_creates_get_an_idempotency_key_unless_told_otherwise(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.post("/v1/tasks").respond(json=task())
    tm.tasks.create({"org_id": "O0020", "title": "a"})
    uuid.UUID(route.calls.last.request.headers["idempotency-key"])
    tm.tasks.create({"org_id": "O0020", "title": "a"}, idempotency_key="my-key")
    assert route.calls.last.request.headers["idempotency-key"] == "my-key"
    tm.tasks.create({"org_id": "O0020", "title": "a"}, idempotency_key=None)
    assert "idempotency-key" not in route.calls.last.request.headers
    assert repr(AUTO) == "AUTO"


def test_non_creates_never_send_an_idempotency_key(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.post("/v1/teams").respond(201, json=example("teams.create") | {"members": []})
    tm.teams.create({"org_id": "O0020", "name": "x"})
    assert "idempotency-key" not in route.calls.last.request.headers


# ---------------------------------------------------------------------------
# ETag / If-Match / If-None-Match
# ---------------------------------------------------------------------------


def test_a_read_carries_its_etag_and_a_write_sends_it(tm: Taskadence, api: respx.MockRouter) -> None:
    api.get("/v1/tasks/T1").respond(json=task("T1"), headers={"ETag": '"abc"'})
    patch = api.patch("/v1/tasks/T1").respond(json=task("T1"))
    current = tm.tasks.get("T1")
    assert isinstance(current, models.TaskInDB) and current.etag == '"abc"'
    assert "etag" not in current.to_dict()  # never serialized
    tm.tasks.update("T1", {"status": "completed"}, if_match=current.etag)
    assert patch.calls.last.request.headers["if-match"] == '"abc"'


def test_a_stale_if_match_is_a_precondition_failed(tm: Taskadence, api: respx.MockRouter) -> None:
    api.patch("/v1/tasks/T1").respond(
        412,
        json={
            "type": "urn:taskadence:problem:precondition-failed",
            "title": "Precondition Failed",
            "status": 412,
            "detail": "If-Match does not match",
            "instance": "/v1/tasks/T1",
            "request_id": "r-9",
        },
    )
    with pytest.raises(PreconditionFailedError) as caught:
        tm.tasks.update("T1", {"status": "completed"}, if_match='"old"')
    assert caught.value.request_id == "r-9"


def test_if_none_match_returns_not_modified_on_304(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.get("/v1/tasks/T1").respond(304)
    result = tm.tasks.get("T1", if_none_match='"abc"')
    assert result is NotModified and not result
    assert route.calls.last.request.headers["if-none-match"] == '"abc"'


# ---------------------------------------------------------------------------
# typed responses
# ---------------------------------------------------------------------------


def test_list_items_are_typed(tm: Taskadence, api: respx.MockRouter) -> None:
    api.get("/v1/tasks").respond(json={"data": [card("T1"), card("T2")], "next_cursor": None})
    page = tm.tasks.list(org_id="O0020")
    assert [type(t) for t in page.data] == [models.TaskCardView, models.TaskCardView]


def test_a_204_returns_none_and_csv_returns_text(tm: Taskadence, api: respx.MockRouter) -> None:
    api.delete("/v1/task-attachments/A1").respond(204)
    assert tm.task_attachments.delete("A1") is None
    api.get("/v1/audit.csv").respond(
        200, text="event_id,action\n1,task.created\n", headers={"content-type": "text/csv"}
    )
    assert tm.audit.export(org_id="O0020").startswith("event_id,action")


def test_a_body_the_models_cannot_read_is_a_response_validation_error(tm: Taskadence, api: respx.MockRouter) -> None:
    broken = task("T1")
    del broken["task_id"]  # a required field missing
    api.get("/v1/tasks/T1").respond(json=broken)
    with pytest.raises(taskadence.ResponseValidationError) as caught:
        tm.tasks.read("T1")
    assert caught.value.operation == "tasks.read" and caught.value.body["title"] == broken["title"]


def test_an_unknown_value_of_a_nullable_enum_passes_through(tm: Taskadence, api: respx.MockRouter) -> None:
    """Forward compatibility: a status added to the API after this SDK was generated is kept as its string."""
    api.get("/v1/tasks/T1").respond(json=task("T1", status="teleported"))
    assert tm.tasks.read("T1").status == "teleported"


def test_an_undocumented_2xx_status_is_reported(tm: Taskadence, api: respx.MockRouter) -> None:
    api.get("/v1/tasks/T1").respond(202, json=task("T1"))
    with pytest.raises(taskadence.ResponseValidationError, match="HTTP 202"):
        tm.tasks.read("T1")


def test_a_caller_supplied_http_client_is_used_and_left_open(api: respx.MockRouter) -> None:
    api.get("/v1/me").respond(json=example("me.read"))
    http = httpx.Client()
    with Taskadence(token=TOKEN, base_url=BASE, http_client=http, headers={"X-Trace": "1"}) as tm:
        tm.me()
        assert api.calls.last.request.headers["x-trace"] == "1"
    assert not http.is_closed
    http.close()
