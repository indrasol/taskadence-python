# `tm.project_resources`

Links and files attached to a project.

_Generated from `spec/openapi.public.json` by `scripts/generate.py`. Do not edit by hand._

## `tm.project_resources.create(body: ProjectResourceCreate | Mapping[str, Any], project_id: str)`

Add a link resource to a project.

- **HTTP:** `POST /v1/project-resources`
- **operationId:** `project-resources.create`
- **Token scope:** `projects:write`
- **Returns:** `ProjectResourceInDB`

## `tm.project_resources.list(project_id: str, search: str | None = None, resource_type: str | None = None, limit: int | None = None, cursor: str | None = None, sort_by: str | None = None, sort_order: str | None = None)`

List a project's resources.

- **HTTP:** `GET /v1/project-resources`
- **operationId:** `project-resources.list`
- **Token scope:** `projects:read`
- **Returns:** `Page[ProjectResourceInDB]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.

## `tm.project_resources.read(resource_id: str, project_id: str, if_none_match: str | None = None)`

Read a project resource.

- **HTTP:** `GET /v1/project-resources/{resource_id}`
- **operationId:** `project-resources.read`
- **Token scope:** `projects:read`
- **Returns:** `ProjectResourceInDB`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.

## `tm.project_resources.update(resource_id: str, body: ProjectResourceUpdate | Mapping[str, Any], project_id: str, if_match: str | None = None)`

Update a project resource.

- **HTTP:** `PUT /v1/project-resources/{resource_id}`
- **operationId:** `project-resources.update`
- **Token scope:** `projects:write`
- **Returns:** `ProjectResourceInDB`
- **Conditional write:** `if_match=obj.etag` → `PreconditionFailedError` (412) when stale.

## `tm.project_resources.delete(resource_id: str, project_id: str, if_match: str | None = None)`

Delete a project resource.

- **HTTP:** `DELETE /v1/project-resources/{resource_id}`
- **operationId:** `project-resources.delete`
- **Token scope:** `projects:write`
- **Returns:** `Acknowledgement`
- **Conditional write:** `if_match=obj.etag` → `PreconditionFailedError` (412) when stale.

## `tm.project_resources.upload(project_id: str, file: FileInput, project_name: str | None = None, title: str | None = None)`

Upload a file resource (multipart).

- **HTTP:** `POST /v1/project-resources/upload`
- **operationId:** `project-resources.upload`
- **Token scope:** `projects:write`
- **Returns:** `ProjectResourceInDB`
