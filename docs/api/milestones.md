# `tm.milestones`

A team's milestones.

_Generated from `spec/openapi.public.json` by `scripts/generate.py` — do not edit by hand._

## `tm.milestones.list(team_id: str, limit: int | None = None, cursor: str | None = None, sort_by: str | None = None, sort_order: str | None = None)`

List a team's milestones.

- **HTTP:** `GET /v1/teams/{team_id}/milestones`
- **operationId:** `milestones.list`
- **Token scope:** `teams:read`
- **Returns:** `Page[MilestoneOut]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.

## `tm.milestones.create(team_id: str, body: MilestoneCreate | Mapping[str, Any])`

Create a milestone.

- **HTTP:** `POST /v1/teams/{team_id}/milestones`
- **operationId:** `milestones.create`
- **Token scope:** `teams:write`
- **Returns:** `MilestoneOut`

## `tm.milestones.update(team_id: str, milestone_id: str, body: MilestoneUpdate | Mapping[str, Any])`

Update / close a milestone.

- **HTTP:** `PUT /v1/teams/{team_id}/milestones/{milestone_id}`
- **operationId:** `milestones.update`
- **Token scope:** `teams:write`
- **Returns:** `MilestoneOut`

## `tm.milestones.delete(team_id: str, milestone_id: str, reason: str | None = None)`

Delete a milestone.

- **HTTP:** `DELETE /v1/teams/{team_id}/milestones/{milestone_id}`
- **operationId:** `milestones.delete`
- **Token scope:** `teams:write`
- **Returns:** `MilestoneDeleted`
