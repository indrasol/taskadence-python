"""The product's name and every name derived from it, in ONE place — plus the pre-rename (TasksMate) spellings that
are still accepted on input. Nothing here is emitted under the old name: the legacy values are read, never sent.

- `BRAND_NAME`: what messages and help text call the product.
- Environment: `TASKADENCE_*` first; a `TASKSMATE_*` variable still works, with a `DeprecationWarning` (`getenv`).
- Problem types: the API emits `urn:taskadence:problem:…`; `urn:tasksmate:problem:…` (older servers) is read the same.
- Access tokens: issued as `tkd_live_…` / `tkd_test_…`; `tm_live_…` / `tm_test_…` tokens minted before the rename
  keep working.
"""

from __future__ import annotations

import os
import sys
import warnings
from types import FrameType

BRAND_NAME = "Taskadence"
SLUG = "taskadence"

ENV_PREFIX = "TASKADENCE_"
LEGACY_ENV_PREFIX = "TASKSMATE_"  # pre-rename; read with a DeprecationWarning

URN_PREFIX = "urn:taskadence:problem:"
LEGACY_URN_PREFIX = "urn:tasksmate:problem:"  # pre-rename servers
URN_PREFIXES = (URN_PREFIX, LEGACY_URN_PREFIX)

TOKEN_PREFIXES = ("tkd_live_", "tkd_test_")
LEGACY_TOKEN_PREFIXES = ("tm_live_", "tm_test_")  # minted before the rename; still valid
ACCEPTED_TOKEN_PREFIXES = TOKEN_PREFIXES + LEGACY_TOKEN_PREFIXES

LEGACY_SLUG = "tasksmate"  # the CLI's keyring service and config directory before the rename (read, then migrated)


def getenv(name: str) -> str | None:
    """`TASKADENCE_<name>`, else the deprecated `TASKSMATE_<name>` (with a `DeprecationWarning`), else None.

    `name` is the full new name (`TASKADENCE_TOKEN`) or its suffix (`TOKEN`). An empty value counts as unset.
    """
    suffix = name.removeprefix(ENV_PREFIX)
    value = os.environ.get(ENV_PREFIX + suffix)
    if value:
        return value
    legacy = os.environ.get(LEGACY_ENV_PREFIX + suffix)
    if legacy:
        warnings.warn(
            f"{LEGACY_ENV_PREFIX}{suffix} is deprecated: {BRAND_NAME} reads {ENV_PREFIX}{suffix}. "
            f"Rename the variable; the old name will stop working in a future release.",
            DeprecationWarning,
            stacklevel=_caller_level(),
        )
        return legacy
    return None


def _caller_level() -> int:
    """The `stacklevel` that points the warning at the first frame outside this package (the user's code)."""
    level = 2
    frame: FrameType | None = sys._getframe(2)
    while frame is not None and str(frame.f_globals.get("__name__", "")).startswith(SLUG):
        level, frame = level + 1, frame.f_back
    return level


def problem_slug(type_: str) -> str | None:
    """`token-expired` for `urn:taskadence:problem:token-expired` (or the legacy `urn:tasksmate:…`); else None."""
    for prefix in URN_PREFIXES:
        if type_.startswith(prefix):
            return type_[len(prefix) :]
    return None


def is_access_token(value: str) -> bool:
    """True for a token-shaped access token: `tkd_live_` / `tkd_test_`, or the pre-rename `tm_live_` / `tm_test_`."""
    return value.startswith(ACCEPTED_TOKEN_PREFIXES)
