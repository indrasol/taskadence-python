"""Guard (S.23b): the two MCP READMEs (`taskadence-mcp` on PyPI, `@taskadence/mcp` on npm) stay in sync.

They describe the same proxy, so every section is the same text once each package's own words (its name, its run
command, its runtime) are swapped for a placeholder. Only the opening (title, badges, the twin line), "2. Install …"
and "Requirements" are each package's own. Fix a README by changing both.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PYTHON = ROOT / "packages/taskadence-mcp/README.md"
NODE = ROOT / "packages/mcp-node/README.md"
# Longest first: the run command contains the package name, which contains the runner.
OWN_WORDS = {
    PYTHON: [
        ("uvx taskadence-mcp", "{RUN}"),
        ('"command": "uvx"', "{COMMAND}"),
        ('"args": ["taskadence-mcp"]', "{ARGS}"),
        ("taskadence-mcp", "{PKG}"),
        ("uvx", "{RUNNER}"),
        ("Python 3.10", "{RUNTIME}"),
        ("python --version", "{VERSION_CMD}"),
    ],
    NODE: [
        ("npx -y @taskadence/mcp", "{RUN}"),
        ('"command": "npx"', "{COMMAND}"),
        ('"args": ["-y", "@taskadence/mcp"]', "{ARGS}"),
        ("@taskadence/mcp", "{PKG}"),
        ("npx", "{RUNNER}"),
        ("Node.js 20", "{RUNTIME}"),
        ("node --version", "{VERSION_CMD}"),
    ],
}
OWN_SECTIONS = re.compile(r"^(2\. Install |Requirements$)")
HEADING = re.compile(r"^(#{2,3}) (.+)$", re.MULTILINE)


def _sections(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    for word, placeholder in OWN_WORDS[path]:
        text = text.replace(word, placeholder)
    marks = list(HEADING.finditer(text))
    return {
        m.group(2): text[m.end() : marks[i + 1].start() if i + 1 < len(marks) else len(text)]
        for i, m in enumerate(marks)
    }


def test_the_two_mcp_readmes_have_the_same_sections() -> None:
    python, node = _sections(PYTHON), _sections(NODE)
    assert [h for h in python if not OWN_SECTIONS.match(h)] == [h for h in node if not OWN_SECTIONS.match(h)]
    assert any(OWN_SECTIONS.match(h) for h in python) and any(OWN_SECTIONS.match(h) for h in node)


@pytest.mark.parametrize("heading", [h for h in _sections(PYTHON) if not OWN_SECTIONS.match(h)])
def test_a_shared_section_reads_the_same_in_both(heading: str) -> None:
    assert _sections(PYTHON)[heading] == _sections(NODE).get(heading), f"'{heading}' differs: change both READMEs"
