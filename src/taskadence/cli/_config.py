"""Where the CLI keeps the access token and the API URL.

Resolution order for the token: `TASKADENCE_TOKEN` → the OS keyring (service `taskadence`, user `default`) → the config
file. For the URL: `--api-url` → `TASKADENCE_API_URL` → the config file → the SDK's default.

The pre-rename names (`_brand.LEGACY_ENV_PREFIX` variables, keyring service and config directory `_brand.LEGACY_SLUG`)
are still READ as a fallback (the variables with a deprecation warning), never written; `auth login` writes the new
places and `auth logout` clears both.

The config file is `$XDG_CONFIG_HOME/taskadence/config.toml` (default `~/.config/taskadence/config.toml`), in a
directory of mode 700, the file mode 600. The token is written there only when no usable keyring backend exists (or
`--no-keyring`). It holds a small TOML subset — `key = "string"` lines — so Python 3.10 (no `tomllib`) reads it too.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .._brand import LEGACY_SLUG, SLUG, getenv

SERVICE = SLUG
LEGACY_SERVICE = LEGACY_SLUG
USERNAME = "default"
_LINE = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(".*")\s*$')


def config_path(slug: str = SLUG) -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / slug / "config.toml"


def read_config() -> dict[str, str]:
    path = config_path()
    if not path.exists():
        path = config_path(LEGACY_SLUG)  # written before the rename; the next write goes to the new place
    return _parse(path)


def _parse(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text().splitlines():
        match = _LINE.match(line)
        if match:
            try:
                out[match.group(1)] = str(json.loads(match.group(2)))
            except ValueError:
                continue
    return out


def write_config(values: dict[str, str]) -> Path:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    text = "# taskadence CLI configuration — written by `tm auth login`. Keep it private (mode 600).\n"
    text += "".join(f"{key} = {json.dumps(value)}\n" for key, value in sorted(values.items()))
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write(text)
    os.chmod(path, 0o600)
    return path


def _keyring() -> Any | None:
    """The keyring module when a real backend is available, else None."""
    try:
        import keyring
        from keyring.backends import fail
    except ImportError:
        return None
    try:
        backend = keyring.get_keyring()
    except Exception:  # a broken keyring configuration must not break the CLI
        return None
    unusable: tuple[type, ...] = (fail.Keyring,)
    try:
        from keyring.backends import null

        unusable += (null.Keyring,)
    except ImportError:
        pass
    return None if isinstance(backend, unusable) else keyring


@dataclass
class Credentials:
    token: str | None
    source: str  # "env" | "keyring" | "file" | "none"
    api_url: str | None


def load(api_url: str | None = None) -> Credentials:
    config = read_config()
    url = api_url or getenv("API_URL") or config.get("api_url")
    env_token = getenv("TOKEN")
    if env_token:
        return Credentials(env_token, "env", url)
    ring = _keyring()
    if ring is not None:
        for service in (SERVICE, LEGACY_SERVICE):
            try:
                token = ring.get_password(service, USERNAME)
            except Exception:
                token = None
            if token:
                return Credentials(token, "keyring", url)
    if config.get("token"):
        return Credentials(config["token"], "file", url)
    return Credentials(None, "none", url)


def save(token: str, api_url: str | None, *, use_keyring: bool = True) -> str:
    """Store the token; returns where ("keyring" or the file path). The API URL always goes to the file."""
    config = read_config()
    config.pop("token", None)
    if api_url:
        config["api_url"] = api_url
    ring = _keyring() if use_keyring else None
    where = "the OS keyring"
    if ring is not None:
        try:
            ring.set_password(SERVICE, USERNAME, token)
        except Exception:
            ring = None
    if ring is None:
        config["token"] = token
        where = str(config_path())
    if config:
        write_config(config)
    return where


def forget() -> list[str]:
    """Remove the stored token everywhere it may be; returns the places it was removed from."""
    removed: list[str] = []
    ring = _keyring()
    if ring is not None:
        for service in (SERVICE, LEGACY_SERVICE):
            with contextlib.suppress(Exception):  # a keyring that cannot delete must not stop the file cleanup
                if ring.get_password(service, USERNAME):
                    ring.delete_password(service, USERNAME)
                    if "the OS keyring" not in removed:
                        removed.append("the OS keyring")
    config = read_config()
    if "token" in config:
        del config["token"]
        write_config(config)
        removed.append(str(config_path()))
    legacy = config_path(LEGACY_SLUG)
    if "token" in _parse(legacy):
        legacy.unlink()  # the pre-rename file; its api_url (if any) was carried over by the write above
        removed.append(str(legacy))
    return removed


def shown(token: str) -> str:
    """How the CLI names a token: its 12-character prefix, never the rest."""
    return token[:12] + "…"
