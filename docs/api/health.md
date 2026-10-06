# `tm.health`

Liveness.

_Generated from `spec/openapi.public.json` by `scripts/generate.py`. Do not edit by hand._

## `tm.health.read(if_none_match: str | None = None)`

Liveness probe.

- **HTTP:** `GET /v1/health`
- **operationId:** `health.read`
- **Returns:** `Health`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.
