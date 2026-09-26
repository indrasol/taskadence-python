# `tm.releases`

What's new in TasksMate.

_Generated from `spec/openapi.public.json` by `scripts/generate.py` — do not edit by hand._

## `tm.releases.whats_new(environment: str | None = None, since_days: int | None = None, repository: str | None = None, if_none_match: str | None = None)`

What's new — recent release notes (no app caller since 6.13's static carousel; public by the 4.1 decision).

- **HTTP:** `GET /v1/releases/whats-new`
- **operationId:** `releases.whats_new`
- **Returns:** `WhatsNewResponse`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.
