"""`tasksmate.webhooks` against vectors signed by the backend's own signer, `to_dataframe()`, and `AsyncTasksMate`."""

from __future__ import annotations

import builtins
import datetime as dt
from typing import Any

import httpx
import pytest
import respx

from tasksmate import AsyncTasksMate, NotFoundError, NotModified, webhooks

from .conftest import card, problem, task

# Signed by Tasks-Mate-Backend's `app.services.webhook_crypto.signature_header` (71a97a4) — the real signer.
OLD = "whsec_AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8="
NEW = "whsec_ICEiIyQlJicoKSorLC0uLzAxMjM0NTY3ODk6Ozw9Pj8="
TS = 1790387945
BODY = (
    b'{"id":"WD000042","type":"task.updated","api_version":"2026-09-25","created_at":"2026-09-26T01:59:05Z",'
    b'"org_id":"O0020","project_id":"P96441","actor":{"kind":"user","id":"3f1c","username":"rithin"},'
    b'"data":{"resource_type":"task","resource_id":"T869658","before":{"status":"not_started"},'
    b'"after":{"status":"in_progress"}},"request_id":"9b2f"}'
)
SIG_NEW_ONLY = "v1,wXS+39TJCq+cyOlPEiVMQwSNuSdF3vbUPPUWf7RzVFc="
SIG_ROTATING = SIG_NEW_ONLY + " v1,D8TvfVQAbRRj7Qy2T1WPWe/1o8d0ol9h5CH44isgKts="


def headers(signature: str = SIG_NEW_ONLY, **extra: str) -> dict[str, str]:
    return {"webhook-id": "WD000042", "webhook-timestamp": str(TS), "webhook-signature": signature, **extra}


# ---------------------------------------------------------------------------
# webhooks
# ---------------------------------------------------------------------------


def test_a_server_signature_verifies() -> None:
    assert webhooks.verify(NEW, headers(), BODY, now=TS)
    assert webhooks.sign(NEW, "WD000042", TS, BODY) == SIG_NEW_ONLY  # the SDK signs exactly like the server
    assert webhooks.verify(NEW, httpx.Headers(headers()), BODY, now=TS + 299)  # any mapping, any header case
    assert webhooks.verify(NEW, {k.upper(): v for k, v in headers().items()}, BODY.decode(), now=TS)


def test_rotation_both_ways() -> None:
    # during TasksMate's 24 h grace the header carries both signatures: either secret verifies
    assert webhooks.verify(OLD, headers(SIG_ROTATING), BODY, now=TS)
    assert webhooks.verify(NEW, headers(SIG_ROTATING), BODY, now=TS)
    # a receiver switching over may hold both secrets
    assert webhooks.verify([OLD, NEW], headers(SIG_NEW_ONLY), BODY, now=TS)
    assert not webhooks.verify(OLD, headers(SIG_NEW_ONLY), BODY, now=TS)


@pytest.mark.parametrize(
    ("hdrs", "body", "now", "reason"),
    [
        (headers(), BODY + b" ", TS, "no signature matches"),  # a tampered body
        (headers(), BODY, TS + 301, "more than 300 s"),  # a replay
        (headers(), BODY, TS - 301, "more than 300 s"),
        ({"webhook-id": "WD000042", "webhook-signature": SIG_NEW_ONLY}, BODY, TS, "missing"),
        (headers(**{"webhook-timestamp": "soon"}), BODY, TS, "not an integer"),
        (headers(**{"webhook-id": "WD000043"}), BODY, TS, "no signature matches"),  # the id is signed too
        (headers("v2,abc"), BODY, TS, "no signature matches"),
    ],
)
def test_what_does_not_verify(hdrs: dict[str, str], body: bytes, now: int, reason: str) -> None:
    assert not webhooks.verify(NEW, hdrs, body, now=now)
    with pytest.raises(webhooks.WebhookVerificationError, match=reason):
        webhooks.verify(NEW, hdrs, body, now=now, raise_on_failure=True)


def test_a_malformed_secret_is_named_without_echoing_it() -> None:
    with pytest.raises(webhooks.WebhookVerificationError) as caught:
        webhooks.verify("whsec_!!not-base64!!", headers(), BODY, now=TS)
    assert "not-base64" not in str(caught.value)


def test_parse_gives_a_typed_event() -> None:
    event = webhooks.parse(BODY)
    assert (event.id, event.type, event.org_id, event.project_id) == ("WD000042", "task.updated", "O0020", "P96441")
    assert event.created_at == dt.datetime(2026, 9, 26, 1, 59, 5, tzinfo=dt.timezone.utc)
    assert event.actor is not None and event.actor.username == "rithin"
    assert event.data.resource_id == "T869658" and event.data.after == {"status": "in_progress"}
    later = webhooks.parse({**webhooks.parse(BODY).model_dump(mode="json"), "new_field": 1})
    assert later.model_extra == {"new_field": 1}  # forward compatible


# ---------------------------------------------------------------------------
# to_dataframe
# ---------------------------------------------------------------------------


def test_to_dataframe_flattens_and_types(tm: Any, api: respx.MockRouter) -> None:
    api.get("/v1/views/V1/rows").mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "data": [
                        card(
                            "T1",
                            tags=["api", "backend"],
                            type_data={"severity": "high"},
                            due_date="2026-10-01",
                            created_at="2026-09-25T12:00:00Z",
                        )
                    ],
                    "next_cursor": "c1",
                },
            ),
            httpx.Response(
                200,
                json={
                    "data": [card("T2", tags=[], type_data=None, due_date=None, created_at="2026-09-26T08:30:00Z")],
                    "next_cursor": None,
                },
            ),
        ]
    )
    frame = tm.views.rows("V1").to_dataframe()
    assert list(frame["task_id"]) == ["T1", "T2"]  # every page
    assert frame.loc[0, "tags"] == "api, backend" and frame.loc[0, "type_data.severity"] == "high"
    assert frame.loc[0, "due_date"] == dt.date(2026, 10, 1) and frame.loc[1, "due_date"] is None  # a missing date: None
    assert str(frame["created_at"].dtype).startswith("datetime64") and frame["created_at"].dt.tz is not None


def test_to_dataframe_one_page_only(tm: Any, api: respx.MockRouter) -> None:
    route = api.get("/v1/tasks").respond(json={"data": [card("T1")], "next_cursor": "c1"})
    frame = tm.tasks.list(org_id="O0020").to_dataframe(all_pages=False)
    assert frame.shape[0] == 1 and route.call_count == 1


def test_without_pandas_the_error_says_how_to_install(
    tm: Any, api: respx.MockRouter, monkeypatch: pytest.MonkeyPatch
) -> None:
    api.get("/v1/tasks").respond(json={"data": [card("T1")], "next_cursor": None})
    page = tm.tasks.list(org_id="O0020")
    real_import = builtins.__import__

    def blocked(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "pandas":
            raise ImportError("No module named 'pandas'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked)
    with pytest.raises(ImportError, match=r'pip install "tasksmate\[pandas\]"'):
        page.to_dataframe()


# ---------------------------------------------------------------------------
# AsyncTasksMate
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_async_lists_auto_page(atm: AsyncTasksMate, api: respx.MockRouter) -> None:
    api.get("/v1/tasks").mock(
        side_effect=[
            httpx.Response(200, json={"data": [card("T1")], "next_cursor": "c1"}),
            httpx.Response(200, json={"data": [card("T2")], "next_cursor": None}),
        ]
    )
    page = await atm.tasks.list(org_id="O0020")
    assert [t.task_id async for t in page] == ["T1", "T2"]


@pytest.mark.anyio
async def test_async_reads_writes_errors_and_retries(
    atm: AsyncTasksMate, api: respx.MockRouter, slept: list[float]
) -> None:
    api.get("/v1/tasks/T1").mock(
        side_effect=[httpx.Response(503), httpx.Response(200, json=task("T1"), headers={"ETag": '"e1"'})]
    )
    current = await atm.tasks.get("T1")
    assert current.etag == '"e1"' and len(slept) == 1
    api.get("/v1/tasks/T2").respond(304)
    assert await atm.tasks.get("T2", if_none_match='"e1"') is NotModified
    api.get("/v1/tasks/T3").respond(404, json=problem(404))
    with pytest.raises(NotFoundError):
        await atm.tasks.read("T3")
    route = api.post("/v1/tasks").respond(json=task("T4"))
    assert (await atm.tasks.create({"org_id": "O0020", "title": "x"})).task_id == "T4"
    assert "idempotency-key" in route.calls.last.request.headers


@pytest.mark.anyio
async def test_async_to_dataframe_and_context_manager(api: respx.MockRouter) -> None:
    api.get("/v1/tasks").respond(json={"data": [card("T1"), card("T2")], "next_cursor": None})
    async with AsyncTasksMate(token="tm_live_" + "y" * 43, base_url="https://api.tasksmate.test") as atm:
        frame = await (await atm.tasks.list(org_id="O0020")).to_dataframe()
        assert frame.shape[0] == 2
        me_callable = callable(atm.me)
    assert me_callable
