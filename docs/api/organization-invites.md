# `tm.organization_invites`

Invitations into an organization.

_Generated from `spec/openapi.public.json` by `scripts/generate.py`. Do not edit by hand._

## `tm.organization_invites.create(body: OrganizationInviteCreate | Mapping[str, Any])`

Invite someone to an organization.

- **HTTP:** `POST /v1/organization-invites`
- **operationId:** `organization-invites.create`
- **Token scope:** `org:write`
- **Returns:** `OrganizationInviteInDB`

## `tm.organization_invites.list(org_id: str, search: str | None = None, email: str | None = None, status: str | None = None, limit: int | None = None, cursor: str | None = None, sort_by: str | None = None, sort_order: str | None = None)`

List an organization's pending invites.

- **HTTP:** `GET /v1/organization-invites/org/{org_id}`
- **operationId:** `organization-invites.list`
- **Token scope:** `org:read`
- **Returns:** `Page[OrganizationInviteInDB]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.

## `tm.organization_invites.mine(status: str | None = None, limit: int | None = None, cursor: str | None = None, sort_by: str | None = None, sort_order: str | None = None)`

Invites addressed to you.

- **HTTP:** `GET /v1/organization-invites/user`
- **operationId:** `organization-invites.mine`
- **Token scope:** `org:read`
- **Returns:** `Page[OrganizationInviteInDB]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.

## `tm.organization_invites.update(invite_id: str, body: OrganizationInviteUpdate | Mapping[str, Any])`

Change a pending invite's role.

- **HTTP:** `PUT /v1/organization-invites/{invite_id}`
- **operationId:** `organization-invites.update`
- **Token scope:** `org:write`
- **Returns:** `OrganizationInviteInDB`

## `tm.organization_invites.delete(invite_id: str)`

Revoke a pending invite.

- **HTTP:** `DELETE /v1/organization-invites/{invite_id}`
- **operationId:** `organization-invites.delete`
- **Token scope:** `org:write`
- **Returns:** `Acknowledgement`

## `tm.organization_invites.accept(invite_id: str)`

Accept an invite addressed to you.

- **HTTP:** `PUT /v1/organization-invites/{invite_id}/accept`
- **operationId:** `organization-invites.accept`
- **Token scope:** `org:write`
- **Returns:** `OrganizationInviteInDB`

## `tm.organization_invites.reject(invite_id: str)`

Decline an invite addressed to you.

- **HTTP:** `DELETE /v1/organization-invites/{invite_id}/reject`
- **operationId:** `organization-invites.reject`
- **Token scope:** `org:write`
- **Returns:** `Acknowledgement`
