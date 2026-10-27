# `tm.availability`

Who in the organization is unavailable, and when.

_Generated from `spec/openapi.public.json` by `scripts/generate.py`. Do not edit by hand._

## `tm.availability.range(org_id: str, from_: str | None = None, to: str | None = None, if_none_match: str | None = None)`

Everyone's availability over a date range.

- **HTTP:** `GET /v1/organizations/{org_id}/availability`
- **operationId:** `availability.range`
- **Token scope:** `members:read`
- **Returns:** `AvailabilityRange`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.
- **Also:** `tm.organizations.availability` (same call).

## `tm.availability.create(org_id: str, body: AvailabilityCreate | Mapping[str, Any])`

Mark someone unavailable (yourself, or anyone as an admin).

- **HTTP:** `POST /v1/organizations/{org_id}/availability`
- **operationId:** `availability.create`
- **Token scope:** `org:write`
- **Returns:** `AvailabilityEntry`

## `tm.availability.update(org_id: str, entry_id: str, body: AvailabilityUpdate | Mapping[str, Any])`

Change an unavailability entry.

- **HTTP:** `PUT /v1/organizations/{org_id}/availability/{entry_id}`
- **operationId:** `availability.update`
- **Token scope:** `org:write`
- **Returns:** `AvailabilityEntry`

## `tm.availability.delete(org_id: str, entry_id: str)`

Remove an unavailability entry.

- **HTTP:** `DELETE /v1/organizations/{org_id}/availability/{entry_id}`
- **operationId:** `availability.delete`
- **Token scope:** `org:write`
- **Returns:** `AvailabilityDeleted`

## `tm.availability.mark_mine(body: MyAvailabilitySet | Mapping[str, Any])`

Mark your own days unavailable.

- **HTTP:** `PUT /v1/me/availability`
- **operationId:** `availability.mark_mine`
- **Token scope:** `org:write`
- **Returns:** `AvailabilityEntry`
- **Also:** `tm.me.set_availability` (same call).
