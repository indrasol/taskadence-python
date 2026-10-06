"""The 5.8 rename's compatibility path: everything is emitted under the Taskadence names, and the pre-rename
(TasksMate) inputs still work — `TASKSMATE_*` variables (with a DeprecationWarning), `urn:tasksmate:problem:…` problem
types, `tm_live_` / `tm_test_` tokens, and the CLI's old keyring service and config directory."""

from __future__ import annotations

import warnings
from pathlib import Path

import httpx
import pytest
import respx
from typer.testing import CliRunner

import taskadence
from taskadence import errors
from taskadence._brand import BRAND_NAME, getenv, is_access_token, problem_slug
from taskadence.cli import _config, app

from .conftest import BASE, TOKEN

LEGACY_TOKEN = "tm_live_" + "z" * 43  # minted before the rename: still a valid token


def test_the_brand_is_taskadence() -> None:
    assert BRAND_NAME == "TasKadence"  # the wordmark (5.8c); identifiers below stay `Taskadence`
    assert taskadence.Taskadence.__name__ == "Taskadence" and taskadence.AsyncTaskadence.__name__ == "AsyncTaskadence"
    assert taskadence.DEFAULT_BASE_URL == "https://api.taskadence.com"


def test_the_new_variable_is_read_without_a_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TASKADENCE_TOKEN", TOKEN)
    monkeypatch.setenv("TASKSMATE_TOKEN", LEGACY_TOKEN)  # the new name wins, silently
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert getenv("TASKADENCE_TOKEN") == TOKEN


def test_a_legacy_variable_still_works_with_a_deprecation_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TASKADENCE_TOKEN", raising=False)
    monkeypatch.delenv("TASKADENCE_API_URL", raising=False)
    monkeypatch.setenv("TASKSMATE_TOKEN", LEGACY_TOKEN)
    monkeypatch.setenv("TASKSMATE_API_URL", "https://legacy.example.test/v1")
    with pytest.warns(DeprecationWarning) as caught:
        tm = taskadence.Taskadence()
    assert any("TASKSMATE_TOKEN is deprecated: TasKadence reads TASKADENCE_TOKEN" in str(w.message) for w in caught)
    assert tm.base_url == "https://legacy.example.test"
    assert tm._core._headers["Authorization"] == f"Bearer {LEGACY_TOKEN}"
    assert {str(w.message).split(" ")[0] for w in caught} == {"TASKSMATE_TOKEN", "TASKSMATE_API_URL"}
    assert all(w.filename == __file__ for w in caught), "the warning points at the caller, not the SDK"


def test_requests_carry_the_new_header_names(tm: taskadence.Taskadence, api: respx.MockRouter) -> None:
    route = api.get("/v1/me").respond(json={})
    with pytest.raises(taskadence.ResponseValidationError):
        tm.me()
    headers = route.calls.last.request.headers
    assert "taskadence-version" in headers and headers["user-agent"].startswith("taskadence-python/")
    assert not any("tasksmate" in name.lower() for name in headers)


@pytest.mark.parametrize("prefix", ["urn:taskadence:problem:", "urn:tasksmate:problem:"])
def test_both_problem_type_urns_map_to_the_same_exception(prefix: str) -> None:
    body = {"type": prefix + "token-expired", "title": "Unauthorized", "status": 401, "detail": "expired"}
    exc = errors.from_response(httpx.Response(401, json=body))
    assert type(exc) is errors.TokenExpiredError and exc.slug == "token-expired"
    assert errors.error_class(412, prefix + "precondition-failed") is errors.PreconditionFailedError
    assert problem_slug(prefix + "rate-limit") == "rate-limit"


def test_an_unknown_urn_namespace_is_not_a_problem_slug() -> None:
    assert problem_slug("urn:other:problem:token-expired") is None
    assert errors.error_class(401, "urn:other:problem:token-expired") is errors.AuthenticationError


@pytest.mark.parametrize("token", ["tkd_live_abc", "tkd_test_abc", "tm_live_abc", "tm_test_abc"])
def test_new_and_legacy_token_prefixes_are_access_tokens(token: str) -> None:
    assert is_access_token(token)


@pytest.mark.parametrize("token", ["tkd_abc", "tmr_abc", "whsec_abc", "live_abc", ""])
def test_other_strings_are_not_access_tokens(token: str) -> None:
    assert not is_access_token(token)


# ---------------------------------------------------------------------------
# the CLI
# ---------------------------------------------------------------------------

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
    monkeypatch.delenv("TASKADENCE_TOKEN", raising=False)
    monkeypatch.delenv("TASKADENCE_API_URL", raising=False)
    return tmp_path


@pytest.fixture
def ring(monkeypatch: pytest.MonkeyPatch) -> FakeKeyring:
    fake = FakeKeyring()
    monkeypatch.setattr(_config, "_keyring", lambda: fake)
    return fake


def test_the_cli_accepts_a_legacy_token(home: Path, ring: FakeKeyring) -> None:
    result = runner.invoke(app, ["auth", "login", "--token", LEGACY_TOKEN, "--no-verify"])
    assert result.exit_code == 0, result.output
    assert ring.store[("taskadence", "default")] == LEGACY_TOKEN


def test_the_cli_reads_a_legacy_env_token(home: Path, ring: FakeKeyring, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TASKSMATE_TOKEN", LEGACY_TOKEN)
    with pytest.warns(DeprecationWarning, match="TASKSMATE_TOKEN"):
        creds = _config.load()
    assert (creds.token, creds.source) == (LEGACY_TOKEN, "env")


def test_the_cli_reads_the_legacy_keyring_service_and_logout_clears_it(home: Path, ring: FakeKeyring) -> None:
    ring.store[("tasksmate", "default")] = LEGACY_TOKEN
    assert _config.load().token == LEGACY_TOKEN
    ring.store[("taskadence", "default")] = TOKEN
    assert _config.load().token == TOKEN  # the new service wins
    _config.forget()
    assert ring.store == {}


def test_the_cli_reads_the_legacy_config_file(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_config, "_keyring", lambda: None)
    legacy = home / "tasksmate" / "config.toml"
    legacy.parent.mkdir()
    legacy.write_text(f'api_url = "{BASE}"\ntoken = "{LEGACY_TOKEN}"\n')
    creds = _config.load()
    assert (creds.token, creds.source, creds.api_url) == (LEGACY_TOKEN, "file", BASE)
    _config.forget()
    assert not legacy.exists()
    assert _config.read_config() == {"api_url": BASE}  # carried over to ~/.config/taskadence/
    assert (home / "taskadence" / "config.toml").exists()
