# `tm.sprints`

A team's sprints.

_Generated from `spec/openapi.public.json` by `scripts/generate.py`. Do not edit by hand._

## `tm.sprints.list(team_id: str, limit: int | None = None, cursor: str | None = None, sort_by: str | None = None, sort_order: str | None = None)`

List a team's sprints.

- **HTTP:** `GET /v1/teams/{team_id}/sprints`
- **operationId:** `sprints.list`
- **Token scope:** `teams:read`
- **Returns:** `Page[SprintOut]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.

## `tm.sprints.create(team_id: str, body: SprintCreate | Mapping[str, Any])`

Create a sprint.

- **HTTP:** `POST /v1/teams/{team_id}/sprints`
- **operationId:** `sprints.create`
- **Token scope:** `teams:write`
- **Returns:** `SprintOut`

## `tm.sprints.update(team_id: str, sprint_id: str, body: SprintUpdate | Mapping[str, Any])`

Update a sprint.

- **HTTP:** `PUT /v1/teams/{team_id}/sprints/{sprint_id}`
- **operationId:** `sprints.update`
- **Token scope:** `teams:write`
- **Returns:** `SprintOut`

## `tm.sprints.delete(team_id: str, sprint_id: str, reason: str | None = None)`

Delete a sprint (its tasks are unfiled).

- **HTTP:** `DELETE /v1/teams/{team_id}/sprints/{sprint_id}`
- **operationId:** `sprints.delete`
- **Token scope:** `teams:write`
- **Returns:** `SprintDeleted`
