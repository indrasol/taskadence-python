# `tm.sprints`

A project's sprints, and every sprint of an organization (Planning).

_Generated from `spec/openapi.public.json` by `scripts/generate.py`. Do not edit by hand._

## `tm.sprints.list(project_id: str, limit: int | None = None, cursor: str | None = None, sort_by: str | None = None, sort_order: str | None = None)`

List a project's sprints.

- **HTTP:** `GET /v1/projects/{project_id}/sprints`
- **operationId:** `sprints.list`
- **Token scope:** `projects:read`
- **Returns:** `Page[SprintOut]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.
- **Also:** `tm.projects.sprints` (same call).

## `tm.sprints.create(project_id: str, body: SprintCreate | Mapping[str, Any])`

Create a sprint in a project.

- **HTTP:** `POST /v1/projects/{project_id}/sprints`
- **operationId:** `sprints.create`
- **Token scope:** `projects:write`
- **Returns:** `SprintOut`

## `tm.sprints.list_org(org_id: str, limit: int | None = None, cursor: str | None = None, sort_by: str | None = None, sort_order: str | None = None)`

Every sprint you can read in an organization (Planning).

- **HTTP:** `GET /v1/sprints`
- **operationId:** `sprints.list_org`
- **Token scope:** `projects:read`
- **Returns:** `Page[SprintOut]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.

## `tm.sprints.read(sprint_id: str, if_none_match: str | None = None)`

Read a sprint.

- **HTTP:** `GET /v1/sprints/{sprint_id}`
- **operationId:** `sprints.read`
- **Token scope:** `projects:read`
- **Returns:** `SprintOut`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.

## `tm.sprints.update(sprint_id: str, body: SprintUpdate | Mapping[str, Any])`

Update a sprint (name, dates, status, position, project).

- **HTTP:** `PATCH /v1/sprints/{sprint_id}`
- **operationId:** `sprints.update`
- **Token scope:** `projects:write`
- **Returns:** `SprintOut`

## `tm.sprints.delete(sprint_id: str, reason: str | None = None)`

Delete a sprint (its tasks are unfiled).

- **HTTP:** `DELETE /v1/sprints/{sprint_id}`
- **operationId:** `sprints.delete`
- **Token scope:** `projects:write`
- **Returns:** `SprintDeleted`
