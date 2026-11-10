"""Datetimes the API sends with a trailing `Z` parse on every supported Python. Python 3.10's `fromisoformat` refuses
the `Z` (3.11+ accepts it), and the generated models used to fall back to the raw string there, so on 3.10 every
datetime field was a `str` (`org.state_since.year` raised). They now parse through `_generated/_dt.parse_datetime`."""

from __future__ import annotations

import datetime
from collections.abc import Callable
from typing import Any

import pytest

from taskadence import models
from taskadence._generated._dt import parse_date, parse_datetime

from .conftest import example, task

UTC_FORMS = ["2026-11-05T10:00:00Z", "2026-11-05T10:00:00z", "2026-11-05T10:00:00+00:00"]


def _aware_2026(value: object) -> datetime.datetime:
    assert isinstance(value, datetime.datetime), f"parsed to {type(value).__name__}: {value!r}"
    assert value.year == 2026
    assert value.utcoffset() == datetime.timedelta(0)
    return value


@pytest.mark.parametrize("text", UTC_FORMS)
def test_parse_datetime_reads_z_and_offset_alike(text: str) -> None:
    assert _aware_2026(parse_datetime(text)) == datetime.datetime(2026, 11, 5, 10, tzinfo=datetime.timezone.utc)


@pytest.mark.parametrize(
    ("text", "micro"),
    [
        ("2026-11-05T10:00:13.8361+00:00", 836100),
        ("2026-11-05T10:00:13.5Z", 500000),
        ("2026-11-05T10:00:13.1234567Z", 123456),
    ],
)
def test_parse_datetime_reads_any_fraction(text: str, micro: int) -> None:
    """Postgres trims trailing zeros (`.8361`); 3.10 accepts only 3 or 6 digits."""
    assert _aware_2026(parse_datetime(text)).microsecond == micro


def test_parse_date() -> None:
    assert parse_date("2026-11-05") == datetime.date(2026, 11, 5)


def _org_card(since: str) -> object:
    body = example("organizations.list")["data"][0] | {"state_since": since}
    return models.OrgCard.from_dict(body).state_since


def _task_in_db(created: str) -> object:
    return models.TaskInDB.from_dict(task(created_at=created)).created_at


MODELS: list[tuple[str, Callable[[str], Any]]] = [
    ("OrgCard.state_since", _org_card),
    ("TaskInDB.created_at", _task_in_db),
]


@pytest.mark.parametrize("text", UTC_FORMS)
@pytest.mark.parametrize(("field", "read"), MODELS, ids=[name for name, _ in MODELS])
def test_a_model_field_is_an_aware_datetime(field: str, read: Callable[[str], Any], text: str) -> None:
    """`OrgCard.state_since` is nullable (try / except, fell back to `str`); `TaskInDB.created_at` is required (no
    fallback, so on 3.10 it raised)."""
    _aware_2026(read(text))
