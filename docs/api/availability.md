# `tm.availability`

Who on a team is unavailable, and when.

_Generated from `spec/openapi.public.json` by `scripts/generate.py`. Do not edit by hand._

## `tm.availability.range(team_id: str, from_: str | None = None, to: str | None = None, if_none_match: str | None = None)`

A team's availability over a date range.

- **HTTP:** `GET /v1/teams/{team_id}/availability`
- **operationId:** `availability.range`
- **Token scope:** `teams:read`
- **Returns:** `AvailabilityRange`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.

## `tm.availability.create(team_id: str, body: AvailabilityCreate | Mapping[str, Any])`

Mark someone unavailable.

- **HTTP:** `POST /v1/teams/{team_id}/availability`
- **operationId:** `availability.create`
- **Token scope:** `teams:write`
- **Returns:** `AvailabilityEntry`

## `tm.availability.update(team_id: str, entry_id: str, body: AvailabilityUpdate | Mapping[str, Any])`

Change an unavailability entry.

- **HTTP:** `PUT /v1/teams/{team_id}/availability/{entry_id}`
- **operationId:** `availability.update`
- **Token scope:** `teams:write`
- **Returns:** `AvailabilityEntry`

## `tm.availability.delete(team_id: str, entry_id: str)`

Remove an unavailability entry.

- **HTTP:** `DELETE /v1/teams/{team_id}/availability/{entry_id}`
- **operationId:** `availability.delete`
- **Token scope:** `teams:write`
- **Returns:** `AvailabilityDeleted`
