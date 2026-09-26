# `tm.designations`

Job designations (global and per-organization).

_Generated from `spec/openapi.public.json` by `scripts/generate.py` — do not edit by hand._

## `tm.designations.list(org_id: str | None = None, grouped: bool | None = None, with_usage: bool | None = None, include_hidden: bool | None = None, include_inactive: bool | None = None, limit: int | None = None, cursor: str | None = None, sort_by: str | None = None, sort_order: str | None = None)`

List designations (flat list, or the grouped catalog).

- **HTTP:** `GET /v1/designations`
- **operationId:** `designations.list`
- **Token scope:** `org:read`
- **Returns:** `Page[Designation] | DesignationCatalog`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.

## `tm.designations.create(body: DesignationCreate | Mapping[str, Any])`

Create a custom designation.

- **HTTP:** `POST /v1/designations`
- **operationId:** `designations.create`
- **Token scope:** `org:write`
- **Returns:** `Designation`

## `tm.designations.read(designation_id: str, org_id: str | None = None, if_none_match: str | None = None)`

Read a designation.

- **HTTP:** `GET /v1/designations/{designation_id}`
- **operationId:** `designations.read`
- **Token scope:** `org:read`
- **Returns:** `Designation`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.

## `tm.designations.replace(designation_id: str, body: DesignationUpdate | Mapping[str, Any], org_id: str, if_match: str | None = None)`

Update a designation (PUT).

- **HTTP:** `PUT /v1/designations/{designation_id}`
- **operationId:** `designations.replace`
- **Token scope:** `org:write`
- **Returns:** `Designation`
- **Conditional write:** `if_match=obj.etag` → `PreconditionFailedError` (412) when stale.

## `tm.designations.update(designation_id: str, body: DesignationUpdate | Mapping[str, Any], org_id: str, if_match: str | None = None)`

Update a designation.

- **HTTP:** `PATCH /v1/designations/{designation_id}`
- **operationId:** `designations.update`
- **Token scope:** `org:write`
- **Returns:** `Designation`
- **Conditional write:** `if_match=obj.etag` → `PreconditionFailedError` (412) when stale.

## `tm.designations.delete(designation_id: str, org_id: str, if_match: str | None = None)`

Deactivate a custom designation.

- **HTTP:** `DELETE /v1/designations/{designation_id}`
- **operationId:** `designations.delete`
- **Token scope:** `org:write`
- **Returns:** `DesignationDeleted`
- **Conditional write:** `if_match=obj.etag` → `PreconditionFailedError` (412) when stale.

## `tm.designations.set_visibility(designation_id: str, body: VisibilityUpdate | Mapping[str, Any], org_id: str)`

Hide / pin a designation for an org.

- **HTTP:** `PUT /v1/designations/{designation_id}/visibility`
- **operationId:** `designations.set_visibility`
- **Token scope:** `org:write`
- **Returns:** `DesignationVisibility`
