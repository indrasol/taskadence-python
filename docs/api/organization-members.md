# `tm.organization_members`

The members of an organization and their roles.

_Generated from `spec/openapi.public.json` by `scripts/generate.py` — do not edit by hand._

## `tm.organization_members.list(org_id: str, search: str | None = None, role: str | None = None, is_active: bool | None = None, limit: int | None = None, cursor: str | None = None, sort_by: str | None = None, sort_order: str | None = None)`

List an organization's members.

- **HTTP:** `GET /v1/organization-members/{org_id}`
- **operationId:** `organization-members.list`
- **Token scope:** `org:read`
- **Returns:** `Page[OrganizationMemberInDB]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.

## `tm.organization_members.read(user_id: str, org_id: str, if_none_match: str | None = None)`

Read one member.

- **HTTP:** `GET /v1/organization-members/{user_id}/{org_id}`
- **operationId:** `organization-members.read`
- **Token scope:** `org:read`
- **Returns:** `OrganizationMemberInDB`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.

## `tm.organization_members.replace(user_id: str, org_id: str, body: OrganizationMemberUpdate | Mapping[str, Any], if_match: str | None = None)`

Change a member's role / designation (PUT).

- **HTTP:** `PUT /v1/organization-members/{user_id}/{org_id}`
- **operationId:** `organization-members.replace`
- **Token scope:** `org:write`
- **Returns:** `OrganizationMemberInDB`
- **Conditional write:** `if_match=obj.etag` → `PreconditionFailedError` (412) when stale.

## `tm.organization_members.update(user_id: str, org_id: str, body: OrganizationMemberUpdate | Mapping[str, Any], if_match: str | None = None)`

Change a member's role / designation.

- **HTTP:** `PATCH /v1/organization-members/{user_id}/{org_id}`
- **operationId:** `organization-members.update`
- **Token scope:** `org:write`
- **Returns:** `OrganizationMemberInDB`
- **Conditional write:** `if_match=obj.etag` → `PreconditionFailedError` (412) when stale.

## `tm.organization_members.delete(user_id: str, org_id: str, if_match: str | None = None)`

Remove a member.

- **HTTP:** `DELETE /v1/organization-members/{user_id}/{org_id}`
- **operationId:** `organization-members.delete`
- **Token scope:** `org:write`
- **Returns:** `Acknowledgement`
- **Conditional write:** `if_match=obj.etag` → `PreconditionFailedError` (412) when stale.
