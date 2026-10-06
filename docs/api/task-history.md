# `tm.task_history`

A task's change history.

_Generated from `spec/openapi.public.json` by `scripts/generate.py`. Do not edit by hand._

## `tm.task_history.list(task_id: str, title: str | None = None, limit: int | None = None, cursor: str | None = None, sort_by: str | None = None, sort_order: str | None = None)`

A task's change history.

- **HTTP:** `GET /v1/task-history`
- **operationId:** `task-history.list`
- **Token scope:** `tasks:read`
- **Returns:** `Page[TaskHistoryInDB]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.

## `tm.task_history.read(history_id: str, if_none_match: str | None = None)`

Read one history entry.

- **HTTP:** `GET /v1/task-history/{history_id}`
- **operationId:** `task-history.read`
- **Token scope:** `tasks:read`
- **Returns:** `TaskHistoryInDB`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.
