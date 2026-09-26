# `tm.teams`

Teams, their members and their task list.

_Generated from `spec/openapi.public.json` by `scripts/generate.py` — do not edit by hand._

## `tm.teams.create(body: TeamCreate | Mapping[str, Any])`

Create a team.

- **HTTP:** `POST /v1/teams`
- **operationId:** `teams.create`
- **Token scope:** `teams:write`
- **Returns:** `TeamDetail`

## `tm.teams.list(org_id: str, search: str | None = None, limit: int | None = None, cursor: str | None = None, sort_by: str | None = None, sort_order: str | None = None)`

List an organization's teams.

- **HTTP:** `GET /v1/teams`
- **operationId:** `teams.list`
- **Token scope:** `teams:read`
- **Returns:** `Page[TeamOut]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.

## `tm.teams.read(team_id: str, if_none_match: str | None = None)`

Read a team (with its members).

- **HTTP:** `GET /v1/teams/{team_id}`
- **operationId:** `teams.read`
- **Token scope:** `teams:read`
- **Returns:** `TeamDetail`
- **Conditional read:** `if_none_match=obj.etag` → `NotModified` when unchanged.

## `tm.teams.replace(team_id: str, body: TeamUpdate | Mapping[str, Any], if_match: str | None = None)`

Update a team (PUT; partial).

- **HTTP:** `PUT /v1/teams/{team_id}`
- **operationId:** `teams.replace`
- **Token scope:** `teams:write`
- **Returns:** `TeamDetail`
- **Conditional write:** `if_match=obj.etag` → `PreconditionFailedError` (412) when stale.

## `tm.teams.update(team_id: str, body: TeamUpdate | Mapping[str, Any], if_match: str | None = None)`

Update a team (JSON merge-patch).

- **HTTP:** `PATCH /v1/teams/{team_id}`
- **operationId:** `teams.update`
- **Token scope:** `teams:write`
- **Returns:** `TeamDetail`
- **Conditional write:** `if_match=obj.etag` → `PreconditionFailedError` (412) when stale.

## `tm.teams.delete(team_id: str, detach: bool | None = None, reason: str | None = None, if_match: str | None = None)`

Delete a team.

- **HTTP:** `DELETE /v1/teams/{team_id}`
- **operationId:** `teams.delete`
- **Token scope:** `teams:write`
- **Returns:** `TeamDeleted`
- **Conditional write:** `if_match=obj.etag` → `PreconditionFailedError` (412) when stale.

## `tm.teams.add_member(team_id: str, body: TeamMemberCreate | Mapping[str, Any])`

Add a member to a team.

- **HTTP:** `POST /v1/teams/{team_id}/members`
- **operationId:** `teams.add_member`
- **Token scope:** `teams:write`
- **Returns:** `TeamMemberOut`

## `tm.teams.replace_member(team_id: str, user_id: str, body: TeamMemberUpdate | Mapping[str, Any])`

Change a team member's role (PUT).

- **HTTP:** `PUT /v1/teams/{team_id}/members/{user_id}`
- **operationId:** `teams.replace_member`
- **Token scope:** `teams:write`
- **Returns:** `TeamMemberOut`

## `tm.teams.update_member(team_id: str, user_id: str, body: TeamMemberUpdate | Mapping[str, Any])`

Change a team member's role.

- **HTTP:** `PATCH /v1/teams/{team_id}/members/{user_id}`
- **operationId:** `teams.update_member`
- **Token scope:** `teams:write`
- **Returns:** `TeamMemberOut`

## `tm.teams.remove_member(team_id: str, user_id: str)`

Remove a team member.

- **HTTP:** `DELETE /v1/teams/{team_id}/members/{user_id}`
- **operationId:** `teams.remove_member`
- **Token scope:** `teams:write`
- **Returns:** `Acknowledgement`

## `tm.teams.list_tasks(team_id: str, limit: int | None = None, cursor: str | None = None, sort_by: str | None = None, sort_order: str | None = None, include_inaccessible: bool | None = None, section_scope: str | None = None)`

A team's unfiled tasks (the team List's read; task-list envelope).

- **HTTP:** `GET /v1/teams/{team_id}/intake`
- **operationId:** `teams.list_tasks`
- **Token scope:** `teams:read`
- **Returns:** `Page[TaskCardView]`
- **List:** returns a `Page`; iterating it follows `next_cursor` through every page.
