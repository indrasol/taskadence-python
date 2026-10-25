# `tm.account`

Your account: one per email, any number of organizations, one shared storage pool.

_Generated from `spec/openapi.public.json` by `scripts/generate.py`. Do not edit by hand._

## `tm.account.read(if_none_match: str | None = None)`

The caller's account: its organizations, the caller's account role and the storage pool.

- **HTTP:** `GET /v1/account`
- **operationId:** `account.read`
- **Token scope:** `account:read`
- **Returns:** `AccountOut`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.

## `tm.account.people(if_none_match: str | None = None)`

Everyone in the account with their role in each organization (account owner / admin).

- **HTTP:** `GET /v1/account/people`
- **operationId:** `account.people`
- **Token scope:** `account:read`
- **Returns:** `AccountPeople`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.

## `tm.account.storage(if_none_match: str | None = None)`

The account's storage pool: totals and the per-organization breakdown.

- **HTTP:** `GET /v1/storage`
- **operationId:** `account.storage`
- **Token scope:** `account:read`
- **Returns:** `AccountStorage`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.
- **Also:** `tm.storage.get` (same call).
