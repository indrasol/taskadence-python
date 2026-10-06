# `tm.view_pins`

Your sidebar pins (views and projects).

_Generated from `spec/openapi.public.json` by `scripts/generate.py`. Do not edit by hand._

## `tm.view_pins.pin_view(view_id: str)`

Pin a view to your sidebar.

- **HTTP:** `PUT /v1/views/{view_id}/pin`
- **operationId:** `view-pins.pin_view`
- **Token scope:** `tasks:write`
- **Returns:** `PinOut`

## `tm.view_pins.unpin_view(view_id: str)`

Unpin a view.

- **HTTP:** `DELETE /v1/views/{view_id}/pin`
- **operationId:** `view-pins.unpin_view`
- **Token scope:** `tasks:write`
- **Returns:** `Acknowledgement`

## `tm.view_pins.list(org_id: str, limit: int | None = None, cursor: str | None = None, sort_by: str | None = None, sort_order: str | None = None)`

Your pins (views and projects), in order.

- **HTTP:** `GET /v1/view-pins`
- **operationId:** `view-pins.list`
- **Token scope:** `tasks:read`
- **Returns:** `Page[PinOut]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.

## `tm.view_pins.pin_project(project_id: str, org_id: str)`

Pin a project.

- **HTTP:** `PUT /v1/view-pins/projects/{project_id}`
- **operationId:** `view-pins.pin_project`
- **Token scope:** `tasks:write`
- **Returns:** `PinOut`

## `tm.view_pins.unpin_project(project_id: str)`

Unpin a project.

- **HTTP:** `DELETE /v1/view-pins/projects/{project_id}`
- **operationId:** `view-pins.unpin_project`
- **Token scope:** `tasks:write`
- **Returns:** `Acknowledgement`

## `tm.view_pins.reorder(body: PinOrder | Mapping[str, Any])`

Reorder your pins.

- **HTTP:** `PUT /v1/view-pins/order`
- **operationId:** `view-pins.reorder`
- **Token scope:** `tasks:write`
- **Returns:** `PinListPage`
