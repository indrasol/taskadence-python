# `tm.me`

Who the caller is: the principal and its organizations / roles.

_Generated from `spec/openapi.public.json` by `scripts/generate.py` — do not edit by hand._

## `tm.me.read(if_none_match: str | None = None)`

The authenticated principal and its organizations / roles.

- **HTTP:** `GET /v1/me`
- **operationId:** `me.read`
- **Returns:** `MeOut`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.
