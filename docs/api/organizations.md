# `tm.organizations`

Organizations you belong to, and their settings.

_Generated from `spec/openapi.public.json` by `scripts/generate.py` — do not edit by hand._

## `tm.organizations.list(limit: int | None = None, cursor: str | None = None, sort_by: str | None = None, sort_order: str | None = None)`

Organizations you belong to or are invited to.

- **HTTP:** `GET /v1/organizations`
- **operationId:** `organizations.list`
- **Token scope:** `org:read`
- **Returns:** `Page[OrgCard]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.

## `tm.organizations.read(org_id: str, if_none_match: str | None = None)`

Read an organization.

- **HTTP:** `GET /v1/organizations/{org_id}`
- **operationId:** `organizations.read`
- **Token scope:** `org:read`
- **Returns:** `OrganizationInDB`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.

## `tm.organizations.settings(org_id: str, if_none_match: str | None = None)`

Read an organization's settings.

- **HTTP:** `GET /v1/organizations/{org_id}/settings`
- **operationId:** `organizations.settings`
- **Token scope:** `org:read`
- **Returns:** `OrganizationSettingsOut`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.

## `tm.organizations.update_settings(org_id: str, body: OrganizationSettingsUpdate | Mapping[str, Any], if_match: str | None = None)`

Update an organization's settings.

- **HTTP:** `PUT /v1/organizations/{org_id}/settings`
- **operationId:** `organizations.update_settings`
- **Token scope:** `org:write`
- **Returns:** `OrganizationSettingsOut`
- **Conditional write:** `if_match=obj.etag` → `PreconditionFailedError` (412) when stale.

## `tm.organizations.access_review(org_id: str, if_none_match: str | None = None)`

Access review: every member and the tokens they hold (owner / admin; JSON or CSV).

- **HTTP:** `GET /v1/organizations/{org_id}/access-review`
- **operationId:** `organizations.access_review`
- **Token scope:** `org:read`
- **Returns:** `AccessReview`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.
