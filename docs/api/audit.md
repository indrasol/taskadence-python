# `tm.audit`

The organization's audit log (owners and admins).

_Generated from `spec/openapi.public.json` by `scripts/generate.py`. Do not edit by hand._

## `tm.audit.list(org_id: str, cursor: str | None = None, resource_type: str | None = None, resource_id: str | None = None, project_id: str | None = None, action: str | None = None, actor: str | None = None, from_: str | None = None, to: str | None = None, limit: int | None = None)`

The organization's audit log (owner / admin).

- **HTTP:** `GET /v1/audit`
- **operationId:** `audit.list`
- **Token scope:** `admin`
- **Returns:** `Page[AuditPageDataItem]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.

## `tm.audit.export(org_id: str, resource_type: str | None = None, resource_id: str | None = None, project_id: str | None = None, action: str | None = None, actor: str | None = None, from_: str | None = None, to: str | None = None, limit: int | None = None, if_none_match: str | None = None)`

Export the audit log as CSV (owner / admin).

- **HTTP:** `GET /v1/audit.csv`
- **operationId:** `audit.export`
- **Token scope:** `admin`
- **Returns:** `str`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.

## `tm.audit.export_json(org_id: str, resource_type: str | None = None, resource_id: str | None = None, project_id: str | None = None, action: str | None = None, actor: str | None = None, from_: str | None = None, to: str | None = None, limit: int | None = None, if_none_match: str | None = None)`

Export the audit log as a JSON array (owner / admin; S.8).

- **HTTP:** `GET /v1/audit.json`
- **operationId:** `audit.export_json`
- **Token scope:** `admin`
- **Returns:** `list[AuditExportRow]`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.
