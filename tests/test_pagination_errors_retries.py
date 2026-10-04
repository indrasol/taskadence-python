"""Auto-paging, problem+json → typed exceptions, retries (Retry-After, idempotency), deprecation warnings, logging."""

from __future__ import annotations

import logging
import warnings

import httpx
import pytest
import respx

from taskadence import (
    APIConnectionError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    ForbiddenError,
    IdempotencyKeyInFlightError,
    IdempotencyKeyInvalidError,
    IdempotencyKeyReusedError,
    InsufficientScopeError,
    InternalError,
    InvalidParameterError,
    NotFoundError,
    PreconditionFailedError,
    RateLimitedError,
    Taskadence,
    TaskadenceError,
    TestTokenReadOnlyError,
    TokenExpiredError,
    TokenInvalidError,
    TokenPolicyError,
    TokenRevokedError,
    UnprocessableEntityError,
    UrlRefusedError,
    ValidationError,
    errors,
)

from .conftest import BASE, TOKEN, card, problem, task

URN = "urn:taskadence:problem:"

# ---------------------------------------------------------------------------
# pagination
# ---------------------------------------------------------------------------


def _pages(api: respx.MockRouter) -> respx.Route:
    """Three pages: 2 items, then an EMPTY page whose cursor is still set (the grammar allows it), then 1 item."""
    return api.get("/v1/tasks").mock(
        side_effect=[
            httpx.Response(200, json={"data": [card("T1"), card("T2")], "next_cursor": "c1"}),
            httpx.Response(200, json={"data": [], "next_cursor": "c2"}),
            httpx.Response(200, json={"data": [card("T3")], "next_cursor": None}),
        ]
    )


def test_iterating_a_page_follows_next_cursor_through_every_page(tm: Taskadence, api: respx.MockRouter) -> None:
    route = _pages(api)
    page = tm.tasks.list(org_id="O0020", filter={"status": ["in_progress"]}, limit=2)
    assert [t.task_id for t in page.data] == ["T1", "T2"] and page.next_cursor == "c1" and page.has_more
    assert [t.task_id for t in page] == ["T1", "T2", "T3"]
    cursors = [c.request.url.params.get("cursor") for c in route.calls]
    assert cursors == [None, "c1", "c2"]
    # the follow-up pages repeat the query exactly (the cursor is bound to it)
    assert {c.request.url.params["filter[status]"] for c in route.calls} == {"in_progress"}
    assert {c.request.url.params["limit"] for c in route.calls} == {"2"}


def test_pages_and_next_page(tm: Taskadence, api: respx.MockRouter) -> None:
    _pages(api)
    first = tm.tasks.list(org_id="O0020")
    assert [len(p.data) for p in first.pages()] == [2, 0, 1]
    _pages(api)
    second = tm.tasks.list(org_id="O0020").next_page()
    assert second is not None and second.data == [] and second.next_cursor == "c2"


def test_a_last_page_does_not_fetch_again(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.get("/v1/views/V1/rows").respond(json={"data": [card("T1")], "next_cursor": None})
    page = tm.views.rows("V1")
    assert [t.task_id for t in page] == ["T1"] and page.next_page() is None and route.call_count == 1


def test_a_cursor_that_never_advances_stops_instead_of_looping(tm: Taskadence, api: respx.MockRouter) -> None:
    from taskadence.pagination import PaginationError

    api.get("/v1/tasks").respond(json={"data": [card("T1")], "next_cursor": "same"})
    with pytest.raises(PaginationError):
        list(tm.tasks.list(org_id="O0020"))


def test_a_bare_array_is_read_as_one_page(tm: Taskadence, api: respx.MockRouter) -> None:
    """The pre-4.1 shape, tolerated exactly as the app's `unwrapList` tolerates it."""
    api.get("/v1/tasks").respond(json=[card("T1"), card("T2")])
    page = tm.tasks.list(org_id="O0020")
    assert [t.task_id for t in page] == ["T1", "T2"] and page.next_cursor is None


def test_an_envelope_with_extras_keeps_them(tm: Taskadence, api: respx.MockRouter) -> None:
    api.get("/v1/projects/P1/goals").respond(
        json={"project_id": "P1", "data": [], "next_cursor": None, "goals_tasks_total": 7, "goals_tasks_completed": 3}
    )
    page = tm.goals.list("P1")
    assert page.data == [] and page.envelope.goals_tasks_total == 7


# ---------------------------------------------------------------------------
# errors
# ---------------------------------------------------------------------------

CASES = [
    (400, URN + "invalid-parameter", InvalidParameterError, BadRequestError),
    (400, URN + "idempotency-key-invalid", IdempotencyKeyInvalidError, BadRequestError),
    (401, URN + "token-invalid", TokenInvalidError, AuthenticationError),
    (401, URN + "token-expired", TokenExpiredError, AuthenticationError),
    (401, URN + "token-revoked", TokenRevokedError, AuthenticationError),
    (403, URN + "insufficient-scope", InsufficientScopeError, ForbiddenError),
    (403, URN + "test-token-read-only", TestTokenReadOnlyError, ForbiddenError),
    (403, URN + "token-policy", TokenPolicyError, TaskadenceError),
    (409, URN + "idempotency-key-in-flight", IdempotencyKeyInFlightError, ConflictError),
    (412, URN + "precondition-failed", PreconditionFailedError, TaskadenceError),
    (422, URN + "validation", ValidationError, UnprocessableEntityError),
    (422, URN + "idempotency-key-reused", IdempotencyKeyReusedError, UnprocessableEntityError),
    (422, URN + "url-refused", UrlRefusedError, UnprocessableEntityError),
    (429, URN + "rate-limit", RateLimitedError, TaskadenceError),
    (500, URN + "internal", InternalError, TaskadenceError),
    (401, "about:blank", AuthenticationError, TaskadenceError),
    (403, "about:blank", ForbiddenError, TaskadenceError),
    (404, "about:blank", NotFoundError, TaskadenceError),
    (409, "about:blank", ConflictError, TaskadenceError),
    (503, "about:blank", InternalError, TaskadenceError),
]


@pytest.mark.parametrize(("status", "type_", "cls", "base"), CASES)
def test_every_problem_type_is_its_own_exception(
    status: int, type_: str, cls: type, base: type, api: respx.MockRouter
) -> None:
    api.get("/v1/tasks/T1").respond(
        status, json=problem(status, type_, "the detail"), headers={"Retry-After": "0"} if status == 429 else {}
    )
    tm = Taskadence(token=TOKEN, base_url=BASE, max_retries=0)
    with pytest.raises(cls) as caught:
        tm.tasks.read("T1")
    err = caught.value
    assert type(err) is cls and isinstance(err, base) and isinstance(err, errors.APIError)
    assert (err.status, err.type, err.detail, err.request_id) == (status, type_, "the detail", "req-123")
    assert "req-123" in str(err)


def test_the_422_error_list_is_kept_and_the_scope_is_named(tm: Taskadence, api: respx.MockRouter) -> None:
    api.post("/v1/tasks").respond(
        422,
        json=problem(
            422,
            URN + "validation",
            [{"loc": ["body", "title"], "msg": "Field required"}],
            errors=[{"loc": ["body", "title"], "msg": "Field required"}],
        ),
    )
    with pytest.raises(ValidationError) as caught:
        tm.tasks.create({"org_id": "O0020"})
    assert caught.value.detail == "Field required" and caught.value.errors[0]["loc"] == ["body", "title"]
    api.patch("/v1/tasks/T1").respond(
        403, json=problem(403, URN + "insufficient-scope", "needs tasks:write", errors=[{"required": "tasks:write"}])
    )
    with pytest.raises(InsufficientScopeError) as scoped:
        tm.tasks.update("T1", {"status": "completed"})
    assert scoped.value.required_scope == "tasks:write" and scoped.value.slug == "insufficient-scope"


def test_a_non_problem_body_still_maps_by_status(tm: Taskadence, api: respx.MockRouter) -> None:
    api.get("/v1/tasks/T1").respond(404, text="<html>gone</html>", headers={"X-Request-ID": "rid-7"})
    with pytest.raises(NotFoundError) as caught:
        tm.tasks.read("T1")
    assert caught.value.request_id == "rid-7" and caught.value.type == "about:blank"
    api.get("/v1/tasks/T2").respond(400, json={"message": "legacy shape"})
    with pytest.raises(BadRequestError, match="legacy shape"):
        tm.tasks.read("T2")


# ---------------------------------------------------------------------------
# retries
# ---------------------------------------------------------------------------


def test_a_get_is_retried_on_503_with_backoff(tm: Taskadence, api: respx.MockRouter, slept: list[float]) -> None:
    route = api.get("/v1/tasks/T1").mock(
        side_effect=[httpx.Response(503), httpx.Response(502), httpx.Response(200, json=task("T1"))]
    )
    assert tm.tasks.read("T1").task_id == "T1"
    assert route.call_count == 3 and len(slept) == 2
    assert 0.25 <= slept[0] <= 0.5 and 0.5 <= slept[1] <= 1.0  # exponential, with jitter


def test_429_honours_retry_after(tm: Taskadence, api: respx.MockRouter, slept: list[float]) -> None:
    api.get("/v1/tasks/T1").mock(
        side_effect=[
            httpx.Response(429, json=problem(429, URN + "rate-limit"), headers={"Retry-After": "7"}),
            httpx.Response(200, json=task("T1")),
        ]
    )
    tm.tasks.read("T1")
    assert slept == [7.0]


def test_a_retry_after_beyond_the_cap_is_raised_not_waited(
    tm: Taskadence, api: respx.MockRouter, slept: list[float]
) -> None:
    api.get("/v1/tasks/T1").respond(429, json=problem(429, URN + "rate-limit"), headers={"Retry-After": "3600"})
    with pytest.raises(RateLimitedError) as caught:
        tm.tasks.read("T1")
    assert caught.value.retry_after == 3600 and slept == []


def test_retries_stop_at_max_retries(api: respx.MockRouter, slept: list[float]) -> None:
    route = api.get("/v1/tasks/T1").respond(503)
    tm = Taskadence(token=TOKEN, base_url=BASE, max_retries=2)
    tm._core._sleep = slept.append
    with pytest.raises(InternalError):
        tm.tasks.read("T1")
    assert route.call_count == 3 and len(slept) == 2


def test_a_create_is_retried_with_the_same_idempotency_key(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.post("/v1/tasks").mock(side_effect=[httpx.Response(503), httpx.Response(200, json=task("T9"))])
    assert tm.tasks.create({"org_id": "O0020", "title": "x"}).task_id == "T9"
    keys = [c.request.headers["idempotency-key"] for c in route.calls]
    assert len(keys) == 2 and keys[0] == keys[1]


def test_a_post_without_an_idempotency_key_is_never_retried(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.post("/v1/tasks").respond(503)
    with pytest.raises(InternalError):
        tm.tasks.create({"org_id": "O0020", "title": "x"}, idempotency_key=None)
    assert route.call_count == 1
    other = api.post("/v1/teams").respond(503)  # not a create at all
    with pytest.raises(InternalError):
        tm.teams.create({"org_id": "O0020", "name": "x"})
    assert other.call_count == 1


def test_a_patch_is_retried_only_with_if_match(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.patch("/v1/tasks/T1").respond(503)
    with pytest.raises(InternalError):
        tm.tasks.update("T1", {"status": "completed"})
    assert route.call_count == 1
    route.reset()
    route.mock(side_effect=[httpx.Response(503), httpx.Response(200, json=task("T1"))])
    tm.tasks.update("T1", {"status": "completed"}, if_match='"e"')
    assert route.call_count == 2


def test_connection_errors_are_retried_then_raised(tm: Taskadence, api: respx.MockRouter, slept: list[float]) -> None:
    route = api.get("/v1/tasks/T1").mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(APIConnectionError, match="refused"):
        tm.tasks.read("T1")
    assert route.call_count == 4 and len(slept) == 3  # 1 + max_retries (3)


# ---------------------------------------------------------------------------
# deprecation + logging
# ---------------------------------------------------------------------------


def test_a_deprecated_response_warns_once_per_operation(tm: Taskadence, api: respx.MockRouter) -> None:
    api.get("/v1/tasks/T1").respond(
        json=task("T1"),
        headers={
            "Deprecation": "@1790294400",
            "Sunset": "Mon, 04 Jan 2027 00:00:00 GMT",
            "Link": '</v1/tasks?filter[task_type]=bug>; rel="successor-version"',
        },
    )
    with warnings.catch_warnings(record=True) as seen:
        warnings.simplefilter("always")
        tm.tasks.read("T1")
        tm.tasks.read("T1")
    deprecations = [w for w in seen if issubclass(w.category, DeprecationWarning)]
    assert len(deprecations) == 1
    assert "tasks.read" in str(deprecations[0].message) and "Mon, 04 Jan 2027" in str(deprecations[0].message)


def test_debug_logging_never_contains_the_token(
    tm: Taskadence, api: respx.MockRouter, caplog: pytest.LogCaptureFixture
) -> None:
    api.get("/v1/tasks").respond(json={"data": [card("T1")], "next_cursor": None}, headers={"X-Request-ID": "rid-1"})
    api.get("/v1/tasks/T1").respond(401, json=problem(401, URN + "token-invalid"))
    with caplog.at_level(logging.DEBUG):
        tm.tasks.list(org_id="O0020")
        with pytest.raises(TokenInvalidError) as caught:
            tm.tasks.read("T1")
    logged = "\n".join(r.getMessage() for r in caplog.records)
    assert "GET /v1/tasks -> 200" in logged and "rid-1" in logged
    assert TOKEN not in logged and TOKEN[:20] not in logged
    assert TOKEN not in str(caught.value) and TOKEN not in repr(caught.value)
    assert not any("authorization" in r.getMessage().lower() for r in caplog.records)
