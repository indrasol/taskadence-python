# `tm.connected_apps`

The OAuth apps you have connected to TasksMate, and disconnecting them.

_Generated from `spec/openapi.public.json` by `scripts/generate.py` — do not edit by hand._

## `tm.connected_apps.list(limit: int | None = None, cursor: str | None = None, sort_by: str | None = None, sort_order: str | None = None)`

The OAuth apps you have connected.

- **HTTP:** `GET /v1/me/connected-apps`
- **operationId:** `connected-apps.list`
- **Returns:** `Page[ConnectedApp]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.

## `tm.connected_apps.delete(grant_id: str)`

Disconnect an app (its tokens for you are revoked).

- **HTTP:** `DELETE /v1/me/connected-apps/{grant_id}`
- **operationId:** `connected-apps.delete`
- **Token scope:** `admin`
- **Returns:** `ConnectedAppRevoked`
