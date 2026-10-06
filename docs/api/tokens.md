# `tm.tokens`

TasKadence access tokens (`tkd_live_…` / `tkd_test_…`): mint, list, rename, revoke, rotate.

_Generated from `spec/openapi.public.json` by `scripts/generate.py`. Do not edit by hand._

## `tm.tokens.create(body: TokenCreate | Mapping[str, Any])`

Mint an access token (the token is shown once).

- **HTTP:** `POST /v1/tokens`
- **operationId:** `tokens.create`
- **Token scope:** `org:write`
- **Returns:** `TokenCreated`

## `tm.tokens.list(org_id: str, limit: int | None = None, cursor: str | None = None, sort_by: str | None = None, sort_order: str | None = None)`

Your access tokens (an owner / admin: the organization's).

- **HTTP:** `GET /v1/tokens`
- **operationId:** `tokens.list`
- **Token scope:** `org:read`
- **Returns:** `Page[TokenOut]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.

## `tm.tokens.read(token_id: str, if_none_match: str | None = None)`

Read an access token (never the token itself).

- **HTTP:** `GET /v1/tokens/{token_id}`
- **operationId:** `tokens.read`
- **Token scope:** `org:read`
- **Returns:** `TokenOut`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.

## `tm.tokens.update(token_id: str, body: TokenUpdate | Mapping[str, Any])`

Rename an access token.

- **HTTP:** `PATCH /v1/tokens/{token_id}`
- **operationId:** `tokens.update`
- **Token scope:** `org:write`
- **Returns:** `TokenOut`

## `tm.tokens.delete(token_id: str)`

Revoke an access token (effective on the next request).

- **HTTP:** `DELETE /v1/tokens/{token_id}`
- **operationId:** `tokens.delete`
- **Token scope:** `org:write`
- **Returns:** `TokenOut`

## `tm.tokens.rotate(token_id: str)`

Rotate: a new token with the same grant; the old one works 60 s more.

- **HTTP:** `POST /v1/tokens/{token_id}/rotate`
- **operationId:** `tokens.rotate`
- **Token scope:** `org:write`
- **Returns:** `TokenCreated`
