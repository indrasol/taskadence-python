# `tm.access_requests`

Access requests: file one or several, list the ones you filed or decide, read one. Filing grants nothing: the system's approvers approve and grant in the app.

_Generated from `spec/openapi.public.json` by `scripts/generate.py`. Do not edit by hand._

## `tm.access_requests.create(body: AccessRequestCreate | Mapping[str, Any], idempotency_key: str | None = AUTO)`

File an access request.

- **HTTP:** `POST /v1/access-requests`
- **operationId:** `access-requests.create`
- **Token scope:** `tasks:write`
- **Returns:** `AccessRequestOut`
- **Idempotent create:** an `Idempotency-Key` is sent (and reused by retries) unless `idempotency_key=None`.

## `tm.access_requests.list(org_id: str, scope: str | None = None, state: str | None = None, if_none_match: str | None = None)`

List the access requests you filed or decide.

- **HTTP:** `GET /v1/access-requests`
- **operationId:** `access-requests.list`
- **Token scope:** `tasks:read`
- **Returns:** `AccessRequestList`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.

## `tm.access_requests.create_batch(body: AccessBatchCreate | Mapping[str, Any], idempotency_key: str | None = AUTO)`

File up to 20 access requests (per-item results).

- **HTTP:** `POST /v1/access-requests/batch`
- **operationId:** `access-requests.create_batch`
- **Token scope:** `tasks:write`
- **Returns:** `AccessBatchCreated`
- **Idempotent create:** an `Idempotency-Key` is sent (and reused by retries) unless `idempotency_key=None`.

## `tm.access_requests.read(task_id: str, if_none_match: str | None = None)`

Read an access request.

- **HTTP:** `GET /v1/access-requests/{task_id}`
- **operationId:** `access-requests.read`
- **Token scope:** `tasks:read`
- **Returns:** `AccessRequestOut`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.
