# `tm.workload`

Open work per person: who is heavy, who has capacity.

_Generated from `spec/openapi.public.json` by `scripts/generate.py`. Do not edit by hand._

## `tm.workload.read(org_id: str, project_id: str | None = None, if_none_match: str | None = None)`

Open work per person (who is heavy, who has capacity).

- **HTTP:** `GET /v1/organizations/{org_id}/workload`
- **operationId:** `workload.read`
- **Token scope:** `tasks:read`
- **Returns:** `WorkloadOut`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.
- **Also:** `tm.organizations.workload` (same call).
