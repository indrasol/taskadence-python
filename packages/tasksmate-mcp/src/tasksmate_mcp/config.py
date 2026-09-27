"""Where the proxy connects, as whom, and with which options — flags first, then the environment.

The names are `TASKSMATE_*` on purpose — the environment of the *packages* (and of the `tm` CLI, which reads the
same `TASKSMATE_TOKEN` / `TASKSMATE_API_URL`). `…_TM` suffixes are the API's own server-side convention; do not
"fix" these to match it.

    TASKSMATE_TOKEN         required — a `tm_live_…` / `tm_test_…` access token (Developers → Tokens)
    TASKSMATE_API_URL       the API's origin (default: production); `/mcp` is added here
    TASKSMATE_MCP_READONLY  `1` / `true` → `?readonly=1`: the SERVER lists and allows only read tools
    TASKSMATE_MCP_GROUPS    `tasks,projects` → `?groups=…`: the SERVER enables only those groups (`me` is always on)

Flags `--api-url`, `--readonly` / `--no-readonly`, `--groups` win over the environment. There is no `--token` flag:
a command line is visible to every process on the machine.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import quote

TOKEN_ENV = "TASKSMATE_TOKEN"  # noqa: S105 - the variable NAME
URL_ENV = "TASKSMATE_API_URL"
READONLY_ENV = "TASKSMATE_MCP_READONLY"
GROUPS_ENV = "TASKSMATE_MCP_GROUPS"

# The production API — the Python SDK's DEFAULT_BASE_URL (the backend's clients table names the same one).
DEFAULT_API_URL = "https://tasksmate-fdfsarhnf5gacfb7.eastus-01.azurewebsites.net"
MCP_PATH = "/mcp"

_TRUE, _FALSE = frozenset({"1", "true", "yes", "on"}), frozenset({"0", "false", "no", "off", ""})
_TOKEN_SHAPED = re.compile(r"tm_(?:live|test)_[A-Za-z0-9_-]*")


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
    """Anything token-shaped becomes `tm_…` — a belt for every line this package writes."""
    return _TOKEN_SHAPED.sub("tm_…", text)


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
    token = (env.get(TOKEN_ENV) or "").strip()
    if not token:
        raise ConfigError(
            f"{TOKEN_ENV} is not set: create an access token in TasksMate (Developers → Tokens) and put it in the "
            f"client's MCP config as {TOKEN_ENV}"
        )
    url = _api_url(api_url if api_url is not None else (env.get(URL_ENV) or DEFAULT_API_URL))
    ro = readonly if readonly is not None else _bool(READONLY_ENV, env.get(READONLY_ENV, ""))
    raw_groups = groups if groups is not None else (env.get(GROUPS_ENV) or None)  # an empty variable = unset
    return Config(token=token, api_url=url, readonly=ro, groups=_groups(raw_groups) if raw_groups is not None else None)
