# `tm.roadmap`

Roadmaps (read): organization, project, team, and a task's stops.

_Generated from `spec/openapi.public.json` by `scripts/generate.py` — do not edit by hand._

## `tm.roadmap.org(org_id: str, if_none_match: str | None = None)`

The organization's roadmap.

- **HTTP:** `GET /v1/roadmap`
- **operationId:** `roadmap.org`
- **Token scope:** `projects:read`
- **Returns:** `RoadmapOut`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.

## `tm.roadmap.project(project_id: str, if_none_match: str | None = None)`

A project's roadmap.

- **HTTP:** `GET /v1/projects/{project_id}/roadmap`
- **operationId:** `roadmap.project`
- **Token scope:** `projects:read`
- **Returns:** `RoadmapOut`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.

## `tm.roadmap.team(team_id: str, if_none_match: str | None = None)`

A team's roadmap.

- **HTTP:** `GET /v1/teams/{team_id}/roadmap`
- **operationId:** `roadmap.team`
- **Token scope:** `projects:read`
- **Returns:** `RoadmapOut`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.

## `tm.roadmap.task_stops(task_id: str, limit: int | None = None, cursor: str | None = None, sort_by: str | None = None, sort_order: str | None = None)`

The roadmap stops a task is on.

- **HTTP:** `GET /v1/tasks/{task_id}/roadmap`
- **operationId:** `roadmap.task_stops`
- **Token scope:** `projects:read`
- **Returns:** `Page[TaskRoadmapStop]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.
