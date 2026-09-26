# `tm.projects`

Projects: create, read, update, delete, reorder.

_Generated from `spec/openapi.public.json` by `scripts/generate.py` — do not edit by hand._

## `tm.projects.create(body: ProjectCreate | Mapping[str, Any], idempotency_key: str | None = AUTO)`

Create a project.

- **HTTP:** `POST /v1/projects`
- **operationId:** `projects.create`
- **Token scope:** `projects:write`
- **Returns:** `ProjectCard`
- **Idempotent create:** an `Idempotency-Key` is sent (and reused by retries) unless `idempotency_key=None`.

## `tm.projects.list(org_id: str, show_all: bool | None = None, limit: int | None = None, cursor: str | None = None, sort_by: str | None = None, sort_order: str | None = None)`

List an organization's projects you can read.

- **HTTP:** `GET /v1/projects/{org_id}`
- **operationId:** `projects.list`
- **Token scope:** `projects:read`
- **Returns:** `Page[ProjectCard]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.

## `tm.projects.read(project_id: str, if_none_match: str | None = None)`

Read a project.

- **HTTP:** `GET /v1/projects/detail/{project_id}`
- **operationId:** `projects.read`
- **Token scope:** `projects:read`
- **Returns:** `ProjectInDB`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.

## `tm.projects.replace(project_id: str, body: ProjectUpdate | Mapping[str, Any], if_match: str | None = None)`

Update a project (PUT; partial).

- **HTTP:** `PUT /v1/projects/{project_id}`
- **operationId:** `projects.replace`
- **Token scope:** `projects:write`
- **Returns:** `ProjectInDB`
- **Conditional write:** `if_match=obj.etag` → `PreconditionFailedError` (412) when stale.

## `tm.projects.update(project_id: str, body: ProjectUpdate | Mapping[str, Any], if_match: str | None = None)`

Update a project (JSON merge-patch).

- **HTTP:** `PATCH /v1/projects/{project_id}`
- **operationId:** `projects.update`
- **Token scope:** `projects:write`
- **Returns:** `ProjectInDB`
- **Conditional write:** `if_match=obj.etag` → `PreconditionFailedError` (412) when stale.

## `tm.projects.delete(project_id: str, if_match: str | None = None)`

Delete (archive) a project.

- **HTTP:** `DELETE /v1/projects/{project_id}`
- **operationId:** `projects.delete`
- **Token scope:** `projects:write`
- **Returns:** `Acknowledgement`
- **Conditional write:** `if_match=obj.etag` → `PreconditionFailedError` (412) when stale.

## `tm.projects.reorder(body: ProjectOrder | Mapping[str, Any])`

Reorder the organization's projects (owner / admin).

- **HTTP:** `POST /v1/projects/reorder`
- **operationId:** `projects.reorder`
- **Token scope:** `projects:write`
- **Returns:** `ProjectsReordered`
