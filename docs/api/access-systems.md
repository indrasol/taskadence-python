# `tm.access_systems`

The systems people request access to (a cloud, GitHub, a SaaS seat...): their access levels, which need an end date, who approves, and a connected system's resources and roles to pick from. Read-only.

_Generated from `spec/openapi.public.json` by `scripts/generate.py`. Do not edit by hand._

## `tm.access_systems.list(org_id: str, include_archived: bool | None = None, if_none_match: str | None = None)`

List the organization's access systems.

- **HTTP:** `GET /v1/access-systems`
- **operationId:** `access-systems.list`
- **Token scope:** `tasks:read`
- **Returns:** `AccessSystemList`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.

## `tm.access_systems.read(system_id: str, if_none_match: str | None = None)`

Read an access system.

- **HTTP:** `GET /v1/access-systems/{system_id}`
- **operationId:** `access-systems.read`
- **Token scope:** `tasks:read`
- **Returns:** `AccessSystemOut`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.

## `tm.access_systems.resources(system_id: str, type: str | None = None, q: str | None = None, cursor: str | None = None, if_none_match: str | None = None)`

A connected system's resources to request.

- **HTTP:** `GET /v1/access-systems/{system_id}/resources`
- **operationId:** `access-systems.resources`
- **Token scope:** `tasks:read`
- **Returns:** `AccessResourceList`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.

## `tm.access_systems.roles(system_id: str, type: str | None = None, if_none_match: str | None = None)`

The roles a system's resource type offers.

- **HTTP:** `GET /v1/access-systems/{system_id}/roles`
- **operationId:** `access-systems.roles`
- **Token scope:** `tasks:read`
- **Returns:** `AccessRoleList`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.
