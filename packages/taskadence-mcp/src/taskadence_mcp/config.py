"""Where the proxy connects, as whom, and with which options — flags first, then the environment.

The names are `TASKADENCE_*` on purpose — the environment of the *packages* (and of the `tm` CLI, which reads
the same `TASKADENCE_TOKEN` / `TASKADENCE_API_URL`). The pre-rename `TASKSMATE_*` names are still read when the new one
is unset, with a `DeprecationWarning` (printed on stderr by the console script). `…_TM` suffixes are the API's own
server-side convention; do not "fix" these to match it.

    TASKADENCE_TOKEN         required — a `tkd_live_…` / `tkd_test_…` access token (Developers → Tokens; a pre-rename
                             `tm_live_…` / `tm_test_…` token works too)
    TASKADENCE_API_URL       the API's origin (default: production); `/mcp` is added here
    TASKADENCE_MCP_READONLY  `1` / `true` → `?readonly=1`: the SERVER lists and allows only read tools
    TASKADENCE_MCP_GROUPS    `tasks,projects` → `?groups=…`: the SERVER enables only those groups (`me` is always on)

Flags `--api-url`, `--readonly` / `--no-readonly`, `--groups` win over the environment. There is no `--token` flag:
a command line is visible to every process on the machine.
"""

from __future__ import annotations

import os
import re
import warnings
from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import quote

BRAND_NAME = "Taskadence"
SLUG = "taskadence"
ENV_PREFIX = "TASKADENCE_"
LEGACY_ENV_PREFIX = "TASKSMATE_"  # pre-rename; read with a DeprecationWarning when the new name is unset

TOKEN_ENV = ENV_PREFIX + "TOKEN"  # the variable NAME
URL_ENV = ENV_PREFIX + "API_URL"
READONLY_ENV = ENV_PREFIX + "MCP_READONLY"
GROUPS_ENV = ENV_PREFIX + "MCP_GROUPS"

# The production API — the Python SDK's DEFAULT_BASE_URL (the backend's clients table names the same one).
DEFAULT_API_URL = "https://api.taskadence.com"
MCP_PATH = "/mcp"

_TRUE, _FALSE = frozenset({"1", "true", "yes", "on"}), frozenset({"0", "false", "no", "off", ""})
# `tkd_live_` / `tkd_test_`, and the pre-rename `tm_live_` / `tm_test_` (those tokens keep working).
_TOKEN_SHAPED = re.compile(r"(?:tkd|tm)_(?:live|test)_[A-Za-z0-9_-]*")


class ConfigError(ValueError):
    """A configuration the proxy cannot start with. The message never contains the token."""


@dataclass(frozen=True)
class Config:
    token: str = field(repr=False)
    api_url: str
    readonly: bool = False
    groups: tuple[str, ...] | None = None

    @property
    def mcp_url(self) -> str:
        """`<api>/mcp[?readonly=1][&groups=a,b]` — the remote server's own URL contract (5.1)."""
        query = []
        if self.readonly:
            query.append("readonly=1")
        if self.groups is not None:
            query.append("groups=" + quote(",".join(self.groups), safe=","))
        return f"{self.api_url}{MCP_PATH}" + ("?" + "&".join(query) if query else "")


def redact(text: str) -> str:
    """Anything token-shaped becomes `tkd_…` — a belt for every line this package writes."""
    return _TOKEN_SHAPED.sub("tkd_…", text)


def _env(env: Mapping[str, str], name: str) -> str | None:
    """`name` (a `TASKADENCE_*` variable), else its deprecated `TASKSMATE_*` twin with a `DeprecationWarning`."""
    if name in env:
        return env[name]
    legacy = LEGACY_ENV_PREFIX + name.removeprefix(ENV_PREFIX)
    if legacy in env:
        warnings.warn(
            f"{legacy} is deprecated: {SLUG}-mcp reads {name}. Rename it in the client's MCP config.",
            DeprecationWarning,
            stacklevel=3,
        )
        return env[legacy]
    return None


def _bool(name: str, value: str) -> bool:
    v = value.strip().lower()
    if v in _TRUE:
        return True
    if v in _FALSE:
        return False
    raise ConfigError(f"{name} must be 1 or 0 (got {value!r})")


def _groups(value: str) -> tuple[str, ...]:
    groups = tuple(dict.fromkeys(g.strip().lower() for g in value.split(",") if g.strip()))
    if not groups:
        raise ConfigError(
            "groups is empty: name at least one group (e.g. tasks,projects), or leave it unset for the default"
        )
    return groups


def _api_url(value: str) -> str:
    url = value.strip().rstrip("/").removesuffix(MCP_PATH).removesuffix("/v1").rstrip("/")
    if not url.startswith(("http://", "https://")):
        raise ConfigError(f"{URL_ENV} / --api-url must start with http:// or https:// (got {redact(value)!r})")
    return url


def load_config(
    *,
    api_url: str | None = None,
    readonly: bool | None = None,
    groups: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> Config:
    """The flags (None = not given) over the environment."""
    env = os.environ if environ is None else environ
    token = (_env(env, TOKEN_ENV) or "").strip()
    if not token:
        raise ConfigError(
            f"{TOKEN_ENV} is not set: create an access token in {BRAND_NAME} (Developers → Tokens) and put it in the "
            f"client's MCP config as {TOKEN_ENV}"
        )
    url = _api_url(api_url if api_url is not None else (_env(env, URL_ENV) or DEFAULT_API_URL))
    ro = readonly if readonly is not None else _bool(READONLY_ENV, _env(env, READONLY_ENV) or "")
    raw_groups = groups if groups is not None else (_env(env, GROUPS_ENV) or None)  # an empty variable = unset
    return Config(token=token, api_url=url, readonly=ro, groups=_groups(raw_groups) if raw_groups is not None else None)
