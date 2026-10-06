"""Guard (5.8c Part D): prose spells the product as the wordmark, `TasKadence`.

Identifiers, package names, imports, environment variables and URLs stay `Taskadence` / `taskadence`
(`from taskadence import Taskadence`, `TASKADENCE_TOKEN`, `X-Taskadence-Event`); only running text changes. The
wordmark lives in ONE constant, `taskadence._brand.BRAND_NAME`; the MCP proxies keep a twin each (they do not depend
on the SDK), and this test holds all three to it.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

import taskadence
from taskadence._brand import _PROSE_NAME, BRAND_NAME, wordmark
from taskadence.cli import app

ROOT = Path(__file__).resolve().parent.parent
FENCE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
INLINE_CODE = re.compile(r"`[^`\n]*`")
LINK_TARGET = re.compile(r"\]\([^)]*\)|https?://\S+")


def test_the_wordmark_is_one_constant_with_two_twins() -> None:
    assert BRAND_NAME == "TasKadence"
    python_twin = (ROOT / "packages/taskadence-mcp/src/taskadence_mcp/config.py").read_text(encoding="utf-8")
    node_twin = (ROOT / "packages/mcp-node/src/config.ts").read_text(encoding="utf-8")
    assert f'BRAND_NAME = "{BRAND_NAME}"' in python_twin
    assert f"export const BRAND_NAME = '{BRAND_NAME}';" in node_twin


def test_wordmark_changes_prose_and_leaves_code_alone() -> None:
    assert wordmark("What's new in Taskadence.") == "What's new in TasKadence."
    assert wordmark("Taskadence's MCP server") == "TasKadence's MCP server"
    for code in (
        "`Taskadence(token=…)`",
        "AsyncTaskadence",
        "TaskadenceError",
        "X-Taskadence-Event",
        "Taskadence-Version",
        "https://example.com/Taskadence",
        "Taskadence(token=t)",
    ):
        assert wordmark(code) == code


def _tracked_markdown() -> list[str]:
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z", "*.md"],  # noqa: S607 - git from PATH
            cwd=ROOT,
            capture_output=True,
            check=True,
            text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("not a git checkout (an sdist): the guard runs in the repository")
    return [p for p in out.split("\0") if p]


def test_markdown_prose_uses_the_wordmark() -> None:
    offenders = []
    for rel in _tracked_markdown():
        path = ROOT / rel
        if not path.exists():
            continue
        prose = LINK_TARGET.sub("", INLINE_CODE.sub("", FENCE.sub("", path.read_text(encoding="utf-8"))))
        offenders += [f"{rel}: {line.strip()[:100]}" for line in prose.splitlines() if _PROSE_NAME.search(line)]
    assert not offenders, f"prose must say {BRAND_NAME}:\n" + "\n".join(offenders)


def test_cli_help_and_version_use_the_wordmark() -> None:
    runner = CliRunner()
    help_ = runner.invoke(app, ["--help"])
    version = runner.invoke(app, ["--version"])
    assert help_.exit_code == 0 and BRAND_NAME in help_.output
    assert (
        version.exit_code == 0 and version.output.strip() == f"{BRAND_NAME} CLI (taskadence) {taskadence.__version__}"
    )
    assert not _PROSE_NAME.search(help_.output + version.output)
