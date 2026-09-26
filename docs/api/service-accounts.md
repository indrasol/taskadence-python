# `tm.service_accounts`

Non-human organization members that hold access tokens. They cannot sign in.

_Generated from `spec/openapi.public.json` by `scripts/generate.py` — do not edit by hand._

## `tm.service_accounts.create(org_id: str, body: ServiceAccountCreate | Mapping[str, Any])`

Create a service account (owner / admin).

- **HTTP:** `POST /v1/organizations/{org_id}/service-accounts`
- **operationId:** `service-accounts.create`
- **Token scope:** `org:write`
- **Returns:** `ServiceAccountOut`

## `tm.service_accounts.list(org_id: str, limit: int | None = None, cursor: str | None = None, sort_by: str | None = None, sort_order: str | None = None)`

List an organization's service accounts (owner / admin).

- **HTTP:** `GET /v1/organizations/{org_id}/service-accounts`
- **operationId:** `service-accounts.list`
- **Token scope:** `org:read`
- **Returns:** `Page[ServiceAccountOut]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.

## `tm.service_accounts.update(org_id: str, user_id: str, body: ServiceAccountUpdate | Mapping[str, Any])`

Rename a service account.

- **HTTP:** `PATCH /v1/organizations/{org_id}/service-accounts/{user_id}`
- **operationId:** `service-accounts.update`
- **Token scope:** `org:write`
- **Returns:** `ServiceAccountOut`

## `tm.service_accounts.delete(org_id: str, user_id: str)`

Deactivate a service account and revoke its tokens (never a hard delete).

- **HTTP:** `DELETE /v1/organizations/{org_id}/service-accounts/{user_id}`
- **operationId:** `service-accounts.delete`
- **Token scope:** `org:write`
- **Returns:** `ServiceAccountOut`
