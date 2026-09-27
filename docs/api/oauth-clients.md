# `tm.oauth_clients`

Third-party OAuth apps your organization registers: redirect URIs, allowed scopes, the client secret (shown once, rotated with a 24 h grace), revocation.

_Generated from `spec/openapi.public.json` by `scripts/generate.py` — do not edit by hand._

## `tm.oauth_clients.list(org_id: str, limit: int | None = None, cursor: str | None = None, sort_by: str | None = None, sort_order: str | None = None)`

An organization's OAuth apps (owner / admin).

- **HTTP:** `GET /v1/oauth/clients`
- **operationId:** `oauth-clients.list`
- **Token scope:** `admin`
- **Returns:** `Page[OAuthClientOut]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.

## `tm.oauth_clients.create(body: OAuthClientCreate | Mapping[str, Any])`

Register an OAuth app (a confidential app's secret is shown once).

- **HTTP:** `POST /v1/oauth/clients`
- **operationId:** `oauth-clients.create`
- **Token scope:** `admin`
- **Returns:** `OAuthClientCreated`

## `tm.oauth_clients.read(client_id: str, if_none_match: str | None = None)`

Read an OAuth app (never its secret).

- **HTTP:** `GET /v1/oauth/clients/{client_id}`
- **operationId:** `oauth-clients.read`
- **Token scope:** `admin`
- **Returns:** `OAuthClientOut`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.

## `tm.oauth_clients.update(client_id: str, body: OAuthClientUpdate | Mapping[str, Any])`

Change an OAuth app's name, links, redirect URIs or scopes.

- **HTTP:** `PATCH /v1/oauth/clients/{client_id}`
- **operationId:** `oauth-clients.update`
- **Token scope:** `admin`
- **Returns:** `OAuthClientOut`

## `tm.oauth_clients.delete(client_id: str)`

Revoke an OAuth app, every connection to it and its tokens.

- **HTTP:** `DELETE /v1/oauth/clients/{client_id}`
- **operationId:** `oauth-clients.delete`
- **Token scope:** `admin`
- **Returns:** `OAuthClientOut`

## `tm.oauth_clients.rotate_secret(client_id: str)`

Rotate an app's secret (shown once; the old one works 24 h more).

- **HTTP:** `POST /v1/oauth/clients/{client_id}/rotate-secret`
- **operationId:** `oauth-clients.rotate_secret`
- **Token scope:** `admin`
- **Returns:** `OAuthClientCreated`
