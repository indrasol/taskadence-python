"""Models → pandas (the `pandas` extra: `pip install "taskadence[pandas]"`).

`to_dataframe(items)` builds one row per model from its wire form (`to_dict()`, the API's own field names), then:

- a nested object becomes dotted columns, one level deep: `type_data` → `type_data.severity`, `type_data.bug_status`, …
  (keys differ per task type, so a column is empty where a task has no such key);
- a list of scalars becomes one comma-separated string: `tags` → `"api, backend"`, `restricted_to` → `"ada, lin"`;
  a list of objects stays a Python list in its cell;
- columns ending in `_at` are parsed as timezone-aware datetimes (missing → `NaT`), and `_date` columns as
  `datetime.date` objects (missing → `None`); a column is left as text when any value does not parse.

`Page.to_dataframe()` / `AsyncPage.to_dataframe()` call this over every page.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd

_INSTALL = 'pandas is not installed: `pip install "taskadence[pandas]"` to use to_dataframe().'


def _pandas() -> Any:
    try:
        import pandas
    except ImportError as exc:  # pragma: no cover - exercised by test_dataframe via a blocked import
        raise ImportError(_INSTALL) from exc
    return pandas


def _row(item: Any) -> dict[str, Any]:
    if isinstance(item, Mapping):
        raw: Mapping[str, Any] = item
    elif hasattr(item, "to_dict"):
        raw = item.to_dict()
    else:
        raise TypeError(f"cannot make a row of {type(item).__name__}")
    row: dict[str, Any] = {}
    for key, value in raw.items():
        if isinstance(value, Mapping):
            if not value:
                row[key] = None
            for sub, subvalue in value.items():
                row[f"{key}.{sub}"] = subvalue
        elif isinstance(value, list) and all(not isinstance(v, (Mapping, list)) for v in value):
            row[key] = ", ".join(str(v) for v in value)
        else:
            row[key] = value
    return row


def to_dataframe(items: Iterable[Any]) -> pd.DataFrame:
    pandas = _pandas()
    frame = pandas.DataFrame([_row(item) for item in items])
    for column in frame.columns:
        name = str(column)
        if name.endswith("_at"):
            parsed = pandas.to_datetime(frame[column], errors="coerce", utc=True, format="ISO8601")
            if parsed.notna().sum() == frame[column].notna().sum():
                frame[column] = parsed
        elif name.endswith("_date"):
            parsed = pandas.to_datetime(frame[column], errors="coerce", format="ISO8601")
            if parsed.notna().sum() == frame[column].notna().sum():
                frame[column] = [value.date() if pandas.notna(value) else None for value in parsed]
    return frame
