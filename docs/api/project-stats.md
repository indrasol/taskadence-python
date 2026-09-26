# `tm.project_stats`

A project's task statistics.

_Generated from `spec/openapi.public.json` by `scripts/generate.py` — do not edit by hand._

## `tm.project_stats.read(project_id: str, if_none_match: str | None = None)`

A project's task statistics.

- **HTTP:** `GET /v1/project-stats/{project_id}/stats`
- **operationId:** `project-stats.read`
- **Token scope:** `projects:read`
- **Returns:** `ProjectStatsInDB`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.
