"""The quickstart against a live API — `pytest -m integration`. Skipped unless TASKSMATE_TOKEN, TASKSMATE_API_URL and
TASKSMATE_ORG are set (CI's `integration` job sets them from secrets when present). It writes one task and one saved
view in that organization and deletes both."""

from __future__ import annotations

import os
import runpy
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

REQUIRED = ("TASKSMATE_TOKEN", "TASKSMATE_API_URL", "TASKSMATE_ORG")


@pytest.mark.skipif(not all(os.environ.get(k) for k in REQUIRED), reason="needs " + ", ".join(REQUIRED))
def test_the_quickstart_round_trip() -> None:
    module = runpy.run_path(str(Path(__file__).resolve().parent.parent / "examples" / "quickstart.py"))
    assert module["main"]() == 0
