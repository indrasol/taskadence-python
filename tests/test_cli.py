"""`tm` — every command through typer's CliRunner, the API through respx, the keyring faked, the config in tmp."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from typer.testing import CliRunner

import tasksmate
from tasksmate.cli import _config, app

from .conftest import BASE, TOKEN, card, example, problem, task

runner = CliRunner()


class FakeKeyring:
    def __init__(self) -> None:
        self.store: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, user: str) -> str | None:
        return self.store.get((service, user))

    def set_password(self, service: str, user: str, value: str) -> None:
        self.store[(service, user)] = value

    def delete_password(self, service: str, user: str) -> None:
        del self.store[(service, user)]


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("COLUMNS", "220")
    monkeypatch.delenv("TASKSMATE_TOKEN", raising=False)
    monkeypatch.delenv("TASKSMATE_ORG", raising=False)
    monkeypatch.setenv("TASKSMATE_API_URL", BASE)
    return tmp_path


@pytest.fixture
def ring(monkeypatch: pytest.MonkeyPatch) -> FakeKeyring:
    fake = FakeKeyring()
    monkeypatch.setattr(_config, "_keyring", lambda: fake)
    return fake


@pytest.fixture
def no_ring(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_config, "_keyring", lambda: None)


@pytest.fixture
def signed_in(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TASKSMATE_TOKEN", TOKEN)


def invoke(*args: str, **kwargs: Any) -> Any:
    result = runner.invoke(app, list(args), **kwargs)
    return result


def no_token_in(result: Any) -> None:
    assert TOKEN not in result.output and TOKEN[:20] not in result.output


# ---------------------------------------------------------------------------
# version / usage
# ---------------------------------------------------------------------------


def test_version_and_usage_exit_codes(home: Path) -> None:
    result = invoke("--version")
    assert result.exit_code == 0 and tasksmate.__version__ in result.output
    assert invoke("tasks", "list", "--limit", "0").exit_code == 2  # usage error
    assert invoke("tasks", "frobnicate").exit_code == 2


# ---------------------------------------------------------------------------
# auth
# ---------------------------------------------------------------------------


def test_login_verifies_then_stores_in_the_keyring_never_echoing(
    home: Path, ring: FakeKeyring, api: respx.MockRouter
) -> None:
    api.get("/v1/me").respond(json=example("me.read"))
    result = invoke("auth", "login", "--token", TOKEN)
    assert result.exit_code == 0, result.output
    assert ring.store[("tasksmate", "default")] == TOKEN
    assert "Saved tm_live_xxxx… to the OS keyring" in result.output
    no_token_in(result)
    assert "token" not in _config.read_config()  # not in the file when a keyring exists
    status = invoke("auth", "status")
    assert status.exit_code == 0 and "from the OS keyring" in status.output
    no_token_in(status)


def test_login_prompts_hidden_when_no_token_is_given(home: Path, ring: FakeKeyring, api: respx.MockRouter) -> None:
    api.get("/v1/me").respond(json=example("me.read"))
    result = runner.invoke(app, ["auth", "login"], input=TOKEN + "\n")
    assert result.exit_code == 0 and ring.store[("tasksmate", "default")] == TOKEN
    no_token_in(result)


def test_without_a_keyring_the_token_goes_to_a_600_file(home: Path, no_ring: None, api: respx.MockRouter) -> None:
    api.get("/v1/me").respond(json=example("me.read"))
    result = invoke("auth", "login", "--token", TOKEN)
    path = _config.config_path()
    assert result.exit_code == 0 and str(path) in result.output
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600 and stat.S_IMODE(os.stat(path.parent).st_mode) == 0o700
    assert _config.read_config()["token"] == TOKEN
    assert _config.load().source == "file"
    logout = invoke("auth", "logout")
    assert logout.exit_code == 0 and "token" not in _config.read_config()


def test_a_refused_token_is_not_stored(home: Path, ring: FakeKeyring, api: respx.MockRouter) -> None:
    api.get("/v1/me").respond(401, json=problem(401, "urn:tasksmate:problem:token-revoked", "revoked"))
    result = invoke("auth", "login", "--token", TOKEN)
    assert result.exit_code == 1 and ring.store == {}
    assert invoke("auth", "login", "--token", "not-a-token").exit_code == 2


def test_the_environment_wins_over_the_stored_token(
    home: Path, ring: FakeKeyring, monkeypatch: pytest.MonkeyPatch
) -> None:
    ring.store[("tasksmate", "default")] = "tm_live_" + "k" * 43
    monkeypatch.setenv("TASKSMATE_TOKEN", TOKEN)
    assert _config.load().source == "env"


def test_not_signed_in_is_exit_1_with_a_hint(home: Path, no_ring: None) -> None:
    result = invoke("me")
    assert result.exit_code == 1 and "tm auth login" in result.output


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------


def test_me(signed_in: None, api: respx.MockRouter) -> None:
    api.get("/v1/me").respond(json=example("me.read"))
    result = invoke("me")
    assert result.exit_code == 0 and "Organizations" in result.output
    as_json = invoke("me", "--json")
    assert json.loads(as_json.output)["principal"] == example("me.read")["principal"]


def test_tasks_list_table_and_json(signed_in: None, api: respx.MockRouter) -> None:
    route = api.get("/v1/tasks").mock(
        side_effect=[
            httpx.Response(200, json={"data": [card("T1", title="Ship it")], "next_cursor": "c1"}),
            httpx.Response(200, json={"data": [card("T2", title="Test it")], "next_cursor": None}),
        ]
    )
    result = invoke("tasks", "list", "--org", "O0020", "--status", "in_progress", "--status", "blocked", "--table")
    assert result.exit_code == 0, result.output
    assert "T1" in result.output and "T2" in result.output and "2 rows" in result.output  # every page
    assert route.calls[0].request.url.params["filter[status]"] == "in_progress,blocked"
    no_token_in(result)
    api.get("/v1/tasks").respond(json={"data": [card("T3")], "next_cursor": None})
    as_json = invoke("tasks", "list", "--org", "O0020", "--json")
    assert [t["task_id"] for t in json.loads(as_json.output)] == ["T3"]


def test_tasks_list_uses_your_only_org_and_limit(signed_in: None, api: respx.MockRouter) -> None:
    me = example("me.read")
    me["organizations"] = [me["organizations"][0] | {"org_id": "O0020"}]
    api.get("/v1/me").respond(json=me)
    route = api.get("/v1/tasks").respond(json={"data": [card("T1"), card("T2")], "next_cursor": "c"})
    result = invoke("tasks", "list", "--limit", "1")
    assert result.exit_code == 0 and "1 row" in result.output
    assert route.calls.last.request.url.params["org_id"] == "O0020" and route.call_count == 1


def test_tasks_get_create_update(signed_in: None, api: respx.MockRouter) -> None:
    api.get("/v1/tasks/T1").respond(json=task("T1", title="Ship"), headers={"ETag": '"e1"'})
    assert "Ship" in invoke("tasks", "get", "T1").output
    created = api.post("/v1/tasks").respond(json=task("T9", title="New"))
    result = invoke("tasks", "create", "--org", "O0020", "--title", "New", "--project", "P1", "--due", "2026-10-01")
    assert result.exit_code == 0 and "Created T9" in result.output
    assert json.loads(created.calls.last.request.content) == {
        "org_id": "O0020",
        "title": "New",
        "project_id": "P1",
        "due_date": "2026-10-01",
    }
    assert "idempotency-key" in created.calls.last.request.headers
    patched = api.patch("/v1/tasks/T1").respond(json=task("T1", status="completed"))
    result = invoke("tasks", "update", "T1", "--status", "completed")
    assert result.exit_code == 0 and "Updated T1: status=completed" in result.output
    assert patched.calls.last.request.headers["if-match"] == '"e1"'
    assert invoke("tasks", "update", "T1").exit_code == 2  # nothing to change


def test_an_api_error_prints_the_problem_and_exits_1(signed_in: None, api: respx.MockRouter) -> None:
    api.get("/v1/tasks/T404").respond(404, json=problem(404, detail="Task not found"))
    result = invoke("tasks", "get", "T404")
    assert result.exit_code == 1
    assert "404" in result.output and "Task not found" in result.output and "request_id: req-123" in result.output


def test_projects_list(signed_in: None, api: respx.MockRouter) -> None:
    # the spec's own example for this list is all nulls (its example generator stops at depth 4) — a real card:
    project = {
        "org_id": "O0020",
        "name": "Platform",
        "project_id": "P96441",
        "tasks_total": 12,
        "tasks_completed": 4,
        "progress_percent": "33.3",
        "leads": [],
        "position": 0,
        "status": "in_progress",
    }
    api.get("/v1/projects/O0020").respond(json={"data": [project], "next_cursor": None})
    result = invoke("projects", "list", "--org", "O0020")
    assert result.exit_code == 0 and "P96441" in result.output and "Platform" in result.output


def test_views_rows_csv_json_table(signed_in: None, api: respx.MockRouter) -> None:
    api.get("/v1/views/V1/rows").respond(
        json={"data": [card("T1", tags=["a", "b"], type_data={"severity": "high"})], "next_cursor": None}
    )
    result = invoke("views", "rows", "V1", "--csv")
    lines = result.output.strip().splitlines()
    assert result.exit_code == 0 and "task_id" in lines[0] and "type_data.severity" in lines[0]
    assert "T1" in lines[1] and '"a, b"' in lines[1]
    assert json.loads(invoke("views", "rows", "V1", "--json").output)[0]["task_id"] == "T1"
    assert "T1" in invoke("views", "rows", "V1").output


def test_webhooks_list_test_deliveries(signed_in: None, api: respx.MockRouter) -> None:
    api.get("/v1/webhooks").respond(json=example("webhooks.list") | {"next_cursor": None})
    listed = invoke("webhooks", "list", "--org", "O0020")
    assert listed.exit_code == 0 and example("webhooks.list")["data"][0]["subscription_id"] in listed.output
    api.post("/v1/webhooks/WH1/test").respond(
        json=example("webhooks.test") | {"delivery_id": "WD9", "status": "succeeded", "response_status": 200}
    )
    tested = invoke("webhooks", "test", "WH1")
    assert tested.exit_code == 0 and "WD9: succeeded (HTTP 200)" in tested.output
    deliveries = example("webhooks.delivery")
    api.get("/v1/webhooks/WH1/deliveries").respond(
        json={"data": [deliveries | {"delivery_id": "WD9", "status": "succeeded"}], "next_cursor": None}
    )
    logged = invoke("webhooks", "deliveries", "WH1")
    assert logged.exit_code == 0 and "WD9" in logged.output


def test_tokens_list_shows_prefixes_only(signed_in: None, api: respx.MockRouter) -> None:
    api.get("/v1/tokens").respond(json=example("tokens.list") | {"next_cursor": None})
    result = invoke("tokens", "list", "--org", "O0020")
    assert result.exit_code == 0 and example("tokens.list")["data"][0]["token_prefix"] in result.output
    no_token_in(result)
