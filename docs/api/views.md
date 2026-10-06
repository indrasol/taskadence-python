# `tm.views`

Saved views and the tasks they show.

_Generated from `spec/openapi.public.json` by `scripts/generate.py`. Do not edit by hand._

## `tm.views.list(org_id: str, scope: str | None = None, resource: str | None = None, limit: int | None = None, cursor: str | None = None, sort_by: str | None = None, sort_order: str | None = None)`

Saved views you can read (filter by `resource`: task or project).

- **HTTP:** `GET /v1/views`
- **operationId:** `views.list`
- **Token scope:** `tasks:read`
- **Returns:** `Page[ViewOut]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.

## `tm.views.create(body: ViewCreate | Mapping[str, Any])`

Save a view of the task list or the projects list (`resource`).

- **HTTP:** `POST /v1/views`
- **operationId:** `views.create`
- **Token scope:** `tasks:write`
- **Returns:** `ViewOut`

## `tm.views.read(view_id: str, if_none_match: str | None = None)`

Read a saved view (its `resource` says which list it queries).

- **HTTP:** `GET /v1/views/{view_id}`
- **operationId:** `views.read`
- **Token scope:** `tasks:read`
- **Returns:** `ViewOut`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.

## `tm.views.update(view_id: str, body: ViewUpdate | Mapping[str, Any], if_match: str | None = None)`

Update a saved view.

- **HTTP:** `PATCH /v1/views/{view_id}`
- **operationId:** `views.update`
- **Token scope:** `tasks:write`
- **Returns:** `ViewOut`
- **Conditional write:** `if_match=obj.etag` → `PreconditionFailedError` (412) when stale.

## `tm.views.delete(view_id: str, if_match: str | None = None)`

Delete a saved view.

- **HTTP:** `DELETE /v1/views/{view_id}`
- **operationId:** `views.delete`
- **Token scope:** `tasks:write`
- **Returns:** `ViewDeleted`
- **Conditional write:** `if_match=obj.etag` → `PreconditionFailedError` (412) when stale.

## `tm.views.duplicate(view_id: str, body: ViewDuplicate | Mapping[str, Any])`

Duplicate a saved view.

- **HTTP:** `POST /v1/views/{view_id}/duplicate`
- **operationId:** `views.duplicate`
- **Token scope:** `tasks:write`
- **Returns:** `ViewOut`

## `tm.views.rows(view_id: str, limit: int | None = None, cursor: str | None = None, include_inaccessible: bool | None = None)`

The rows a saved view shows: tasks or projects, per its `resource`.

- **HTTP:** `GET /v1/views/{view_id}/rows`
- **operationId:** `views.rows`
- **Token scope:** `tasks:read`
- **Returns:** `Page[TaskCardView] | Page[ProjectCard]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.
