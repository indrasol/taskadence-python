# `tm.sections`

Sections of a project, a team or a person's own list.

_Generated from `spec/openapi.public.json` by `scripts/generate.py` — do not edit by hand._

## `tm.sections.list(org_id: str, scope_type: str, scope_id: str | None = None, scope_ids: Sequence[str] | None = None, limit: int | None = None, cursor: str | None = None, sort_by: str | None = None, sort_order: str | None = None)`

List a scope's sections (or several scopes').

- **HTTP:** `GET /v1/sections`
- **operationId:** `sections.list`
- **Token scope:** `tasks:read`
- **Returns:** `Page[SectionOut] | Page[SectionOut]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.

## `tm.sections.create(body: SectionCreate | Mapping[str, Any])`

Create a section.

- **HTTP:** `POST /v1/sections`
- **operationId:** `sections.create`
- **Token scope:** `tasks:write`
- **Returns:** `SectionOut`

## `tm.sections.reorder(body: SectionReorder | Mapping[str, Any])`

Reorder a scope's sections.

- **HTTP:** `POST /v1/sections/reorder`
- **operationId:** `sections.reorder`
- **Token scope:** `tasks:write`
- **Returns:** `list[SectionOut]`

## `tm.sections.update(section_id: str, body: SectionUpdate | Mapping[str, Any])`

Rename a section.

- **HTTP:** `PATCH /v1/sections/{section_id}`
- **operationId:** `sections.update`
- **Token scope:** `tasks:write`
- **Returns:** `SectionOut`

## `tm.sections.delete(section_id: str)`

Delete a section.

- **HTTP:** `DELETE /v1/sections/{section_id}`
- **operationId:** `sections.delete`
- **Token scope:** `tasks:write`
- **Returns:** `Acknowledgement`
