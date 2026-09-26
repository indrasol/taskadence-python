# `tm.project_members`

The members of a project and their roles.

_Generated from `spec/openapi.public.json` by `scripts/generate.py` — do not edit by hand._

## `tm.project_members.create(body: ProjectMemberCreate | Mapping[str, Any])`

Add a member to a project.

- **HTTP:** `POST /v1/project-members`
- **operationId:** `project-members.create`
- **Token scope:** `projects:write`
- **Returns:** `ProjectMemberInDB`

## `tm.project_members.list(project_id: str | None = None, search: str | None = None, role: str | None = None, limit: int | None = None, cursor: str | None = None, sort_by: str | None = None, sort_order: str | None = None)`

List a project's members.

- **HTTP:** `GET /v1/project-members`
- **operationId:** `project-members.list`
- **Token scope:** `projects:read`
- **Returns:** `Page[ProjectMemberInDB]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.

## `tm.project_members.read(user_id: str, project_id: str, if_none_match: str | None = None)`

Read one project member.

- **HTTP:** `GET /v1/project-members/{user_id}/{project_id}`
- **operationId:** `project-members.read`
- **Token scope:** `projects:read`
- **Returns:** `ProjectMemberInDB`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.

## `tm.project_members.replace(user_id: str, project_id: str, body: ProjectMemberUpdate | Mapping[str, Any], if_match: str | None = None)`

Change a project member's role (PUT).

- **HTTP:** `PUT /v1/project-members/{user_id}/{project_id}`
- **operationId:** `project-members.replace`
- **Token scope:** `projects:write`
- **Returns:** `ProjectMemberInDB`
- **Conditional write:** `if_match=obj.etag` → `PreconditionFailedError` (412) when stale.

## `tm.project_members.update(user_id: str, project_id: str, body: ProjectMemberUpdate | Mapping[str, Any], if_match: str | None = None)`

Change a project member's role.

- **HTTP:** `PATCH /v1/project-members/{user_id}/{project_id}`
- **operationId:** `project-members.update`
- **Token scope:** `projects:write`
- **Returns:** `ProjectMemberInDB`
- **Conditional write:** `if_match=obj.etag` → `PreconditionFailedError` (412) when stale.

## `tm.project_members.delete(user_id: str, project_id: str, if_match: str | None = None)`

Remove a project member.

- **HTTP:** `DELETE /v1/project-members/{user_id}/{project_id}`
- **operationId:** `project-members.delete`
- **Token scope:** `projects:write`
- **Returns:** `Acknowledgement`
- **Conditional write:** `if_match=obj.etag` → `PreconditionFailedError` (412) when stale.
