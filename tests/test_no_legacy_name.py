"""Guard (5.8): the old product name must not come back. Every tracked text file is scanned for the old spelling in
any case and with any separator (` `, `_`, `-` or none); a hit outside the allowlist below fails the test.

Keep the allowlist TIGHT. Each entry is a path and either None (the whole file) or a regex every hit line must match,
and each says WHY. Adding to it needs a reason that is a compatibility path or something out of this repo's control.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
# Built from parts so this file does not match itself.
OLD = re.compile("tasks" + r"[ _-]?" + "mate", re.IGNORECASE)
LEGACY_ENV = "TASKS" + "MATE_"

ALLOW: dict[str, re.Pattern[str] | None] = {
    # The one place the SDK keeps the pre-rename spellings it still ACCEPTS (env prefix, URN prefix, CLI keyring
    # service / config directory). Nothing is emitted under them.
    "src/taskadence/_brand.py": None,
    # The MCP proxies' twins of the above (they do not depend on the SDK): the legacy env prefix and its docs.
    "packages/taskadence-mcp/src/taskadence_mcp/config.py": None,
    "packages/mcp-node/src/config.ts": None,
    # Tests of the compatibility path: legacy env vars, legacy URNs, legacy keyring service / config directory.
    "tests/test_rename_compat.py": None,
    "packages/taskadence-mcp/tests/test_proxy.py": re.compile(LEGACY_ENV),
    "packages/mcp-node/test/proxy.test.ts": re.compile(LEGACY_ENV),
    # The CHANGELOG's rename entry names what was renamed (one `(5.8)` bullet per line).
    "CHANGELOG.md": re.compile(r"^- \(5\.8\) "),
}


def _tracked_text_files() -> list[str]:
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z"],  # noqa: S607 - git from PATH
            cwd=ROOT,
            capture_output=True,
            check=True,
            text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("not a git checkout (an sdist): the guard runs in the repository")
    return [p for p in out.split("\0") if p]


def test_the_old_name_appears_only_where_the_allowlist_says_why() -> None:
    offenders: list[str] = []
    for rel in _tracked_text_files():
        path = ROOT / rel
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
            continue  # binary, or deleted in the working tree
        if not OLD.search(rel) and not OLD.search(text):
            continue
        if OLD.search(rel):
            offenders.append(f"{rel}: the path itself")
        rule = ALLOW.get(rel, False)
        if rule is None:
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if OLD.search(line) and not (rule is not False and rule.search(line)):
                offenders.append(f"{rel}:{number}: {line.strip()[:120]}")
    assert not offenders, "the old product name is back:\n" + "\n".join(offenders)


def test_every_allowlist_entry_is_still_needed() -> None:
    _tracked_text_files()  # skips outside a git checkout, like the guard
    for rel, rule in ALLOW.items():
        text = (ROOT / rel).read_text(encoding="utf-8")
        hits = [line for line in text.splitlines() if OLD.search(line)]
        assert hits, f"{rel} no longer mentions the old name: remove it from the allowlist"
        if rule is not None:
            assert any(rule.search(line) for line in hits), f"{rel}: the allowlist pattern matches nothing"
