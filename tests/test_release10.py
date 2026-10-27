"""Release 10 (API `2026-10-24`): sprints belong to projects, capacity and workload are organization-wide, projects
have a `position`; teams, sections and test sprints are gone — through `respx`, bodies from the spec's examples."""

from __future__ import annotations

import datetime as dt
import json

import pytest
import respx

import taskadence
from taskadence import (
    AsyncTaskadence,
    ConflictError,
    SprintProjectMismatch,
    SprintProjectMismatchError,
    Taskadence,
    models,
)

from .conftest import SPEC, example, problem, task

# ---------------------------------------------------------------------------
# sprints
# ---------------------------------------------------------------------------


def sprint(sprint_id: str = "SP1", **fields: object) -> dict[str, object]:
    return example("sprints.read") | {"sprint_id": sprint_id, "project_id": "P1", "position": 0} | fields


def sprints(*items: dict[str, object]) -> dict[str, object]:
    """A one-page `{data, next_cursor, total}` envelope."""
    return {"data": list(items), "next_cursor": None, "total": len(items)}


def test_a_projects_sprints_are_listed_under_the_project(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.get("/v1/projects/P1/sprints").respond(json=sprints(sprint("SP1"), sprint("SP2", position=1)))
    via_project = list(tm.projects.sprints("P1"))
    via_sprints = list(tm.sprints.list("P1", limit=10))
    assert [s.sprint_id for s in via_project] == [s.sprint_id for s in via_sprints] == ["SP1", "SP2"]
    first = via_project[0]
    assert isinstance(first, models.SprintOut) and first.project_id == "P1" and via_project[1].position == 1
    assert route.calls.last.request.url.params["limit"] == "10"


def test_every_sprint_of_an_organization(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.get("/v1/sprints").respond(json=sprints(sprint("SP1"), sprint("SP9", project_id="P2")))
    assert [(s.sprint_id, s.project_id) for s in tm.sprints.list_org(org_id="O123456")] == [
        ("SP1", "P1"),
        ("SP9", "P2"),
    ]
    assert route.calls.last.request.url.params["org_id"] == "O123456"


def test_a_sprint_is_created_in_a_project(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.post("/v1/projects/P1/sprints").respond(201, json=sprint("SP3", name="Sprint 3", goal="Ship it"))
    created = tm.sprints.create(
        "P1", {"name": "Sprint 3", "start_date": dt.date(2027, 1, 4), "duration_weeks": 2, "goal": "Ship it"}
    )
    assert created.sprint_id == "SP3" and created.project_id == "P1" and created.goal == "Ship it"
    sent = json.loads(route.calls.last.request.content)
    assert sent == {"name": "Sprint 3", "start_date": "2027-01-04", "duration_weeks": 2, "goal": "Ship it"}
    with_model = models.SprintCreate(name="Sprint 4", start_date=dt.date(2027, 1, 18), end_date=dt.date(2027, 1, 29))
    tm.sprints.create("P1", with_model)
    assert json.loads(route.calls.last.request.content) == {
        "name": "Sprint 4",
        "start_date": "2027-01-18",
        "end_date": "2027-01-29",
    }


def test_a_sprint_update_is_a_patch_that_can_reorder_and_move(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.patch("/v1/sprints/SP1").respond(json=sprint("SP1", position=2, project_id="P2"))
    moved = tm.sprints.update("SP1", models.SprintUpdate(position=2, project_id="P2"))
    assert (moved.position, moved.project_id) == (2, "P2")
    assert json.loads(route.calls.last.request.content) == {"position": 2, "project_id": "P2"}


def test_a_sprint_is_read_and_deleted_by_its_own_id(tm: Taskadence, api: respx.MockRouter) -> None:
    api.get("/v1/sprints/SP1").respond(json=sprint("SP1"))
    deleted = api.delete("/v1/sprints/SP1").respond(204)
    assert tm.sprints.get("SP1").sprint_id == "SP1"
    tm.sprints.delete("SP1")
    assert deleted.called


def test_set_sprint_files_a_task(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.put("/v1/tasks/T1/sprint").respond(json=task("T1", sprint_id="SP1"))
    assert tm.tasks.set_sprint("T1", {"sprint_id": "SP1"}).sprint_id == "SP1"
    assert json.loads(route.calls.last.request.content) == {"sprint_id": "SP1"}


def test_a_sprint_of_another_project_is_a_sprint_project_mismatch(tm: Taskadence, api: respx.MockRouter) -> None:
    mismatch = problem(
        409,
        "urn:taskadence:problem:sprint-project-mismatch",
        "Sprint SP9 belongs to project P2; task T1 is in project P1",
        errors=[{"code": "sprint_project_mismatch", "task_project_id": "P1", "sprint_project_id": "P2"}],
    )
    route = api.put("/v1/tasks/T1/sprint").respond(
        409, json=mismatch, headers={"Content-Type": "application/problem+json"}
    )
    with pytest.raises(SprintProjectMismatchError) as caught:
        tm.tasks.set_sprint("T1", {"sprint_id": "SP9"})
    exc = caught.value
    assert isinstance(exc, ConflictError) and exc.status == 409 and exc.slug == "sprint-project-mismatch"
    assert exc.errors[0]["sprint_project_id"] == "P2" and exc.request_id == "req-123"
    assert SprintProjectMismatch is SprintProjectMismatchError is taskadence.errors.SprintProjectMismatch
    assert route.call_count == 1  # a 409 is an answer, not retried


def test_another_409_is_still_a_plain_conflict(tm: Taskadence, api: respx.MockRouter) -> None:
    api.patch("/v1/sprints/SP1").respond(409, json=problem(409, "urn:taskadence:problem:sprint-not-empty"))
    with pytest.raises(ConflictError) as caught:
        tm.sprints.update("SP1", {"project_id": "P2"})
    assert not isinstance(caught.value, SprintProjectMismatchError)


# ---------------------------------------------------------------------------
# capacity and workload (organization-wide)
# ---------------------------------------------------------------------------


def test_availability_over_a_range(tm: Taskadence, api: respx.MockRouter) -> None:
    body = example("availability.range") | {"org_id": "O123456"}
    route = api.get("/v1/organizations/O123456/availability").respond(json=body)
    away = tm.organizations.availability("O123456", from_="2027-01-04", to="2027-01-17")
    assert isinstance(away, models.AvailabilityRange) and away.org_id == "O123456"
    assert away.members[0].org_role is not None and away.entries[0].entry_id
    params = route.calls.last.request.url.params
    assert (params["from"], params["to"]) == ("2027-01-04", "2027-01-17")
    assert tm.availability.range("O123456").org_id == "O123456"  # the operationId's own name


def test_marking_my_own_days_away(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.put("/v1/me/availability").respond(json=example("availability.mark_mine"))
    entry = tm.me.set_availability(
        models.MyAvailabilitySet(
            org_id="O123456", start_date=dt.date(2027, 1, 11), end_date=dt.date(2027, 1, 12), note="Conference"
        )
    )
    assert isinstance(entry, models.AvailabilityEntry)
    assert json.loads(route.calls.last.request.content) == {
        "org_id": "O123456",
        "start_date": "2027-01-11",
        "end_date": "2027-01-12",
        "note": "Conference",
    }


def test_workload_rows_are_typed(tm: Taskadence, api: respx.MockRouter) -> None:
    person = {
        "user_id": "U1",
        "username": "ada",
        "open": 6,
        "in_progress": 2,
        "blocked": 1,
        "not_started": 3,
        "overdue": 1,
        "due_this_week": 2,
        "heavy": True,
        "top": [{"task_id": "T1", "title": "Ship", "project_id": "P1", "due_date": "2027-01-08", "status": "blocked"}],
    }
    body = example("workload.read") | {"org_id": "O123456", "project_id": "P1", "people": [person], "truncated": True}
    route = api.get("/v1/organizations/O123456/workload").respond(json=body)
    load = tm.organizations.workload("O123456", project_id="P1")
    assert isinstance(load, models.WorkloadOut) and load.truncated is True and load.project_id == "P1"
    row = load.people[0]
    assert isinstance(row, models.WorkloadPerson)
    assert (row.open_, row.in_progress, row.blocked, row.not_started, row.overdue, row.due_this_week) == (
        6,
        2,
        1,
        3,
        1,
        2,
    )
    assert row.heavy is True
    top = row.top[0]
    assert isinstance(top, models.WorkloadTask) and top.task_id == "T1" and top.due_date == dt.date(2027, 1, 8)
    assert isinstance(load.totals, models.WorkloadCounts)
    assert route.calls.last.request.url.params["project_id"] == "P1"
    tm.organizations.workload("O123456")
    assert "project_id" not in route.calls.last.request.url.params  # optional: the whole organization


@pytest.mark.anyio
async def test_the_new_calls_are_async_too(atm: AsyncTaskadence, api: respx.MockRouter) -> None:
    api.get("/v1/projects/P1/sprints").respond(json=sprints(sprint("SP1")))
    api.get("/v1/organizations/O1/workload").respond(json=example("workload.read"))
    api.put("/v1/me/availability").respond(json=example("availability.mark_mine"))
    assert [s.sprint_id async for s in await atm.projects.sprints("P1")] == ["SP1"]
    assert isinstance(await atm.organizations.workload("O1"), models.WorkloadOut)
    body = {"org_id": "O1", "start_date": "2027-01-11", "end_date": "2027-01-11"}
    assert isinstance(await atm.me.set_availability(body), models.AvailabilityEntry)


# ---------------------------------------------------------------------------
# projects: position
# ---------------------------------------------------------------------------


def test_a_project_has_a_position_and_an_update_sets_it(tm: Taskadence, api: respx.MockRouter) -> None:
    listed = example("projects.list")
    listed["data"][0] |= {"project_id": "P1", "position": 3}
    listed["next_cursor"] = None
    api.get("/v1/projects/O123456").respond(json=listed)
    assert next(iter(tm.projects.list("O123456"))).position == 3
    route = api.patch("/v1/projects/P1").respond(json=example("projects.update") | {"project_id": "P1"})
    tm.projects.update("P1", models.ProjectUpdate(position=0))
    assert json.loads(route.calls.last.request.content) == {"position": 0}


# ---------------------------------------------------------------------------
# removed: teams, sections and test sprints
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("resource", ["teams", "sections", "trackers", "test_sprints", "test_runs"])
def test_the_removed_resources_are_gone(tm: Taskadence, resource: str) -> None:
    assert not hasattr(tm, resource)
    assert not any(attr == resource for attr, _ in taskadence.resources.RESOURCE_METHODS.values())


@pytest.mark.parametrize("method", ["set_section", "set_test_run"])
def test_the_removed_task_methods_are_gone(tm: Taskadence, method: str) -> None:
    assert not hasattr(tm.tasks, method)


@pytest.mark.parametrize("method", ["pin_team", "unpin_team"])
def test_team_pins_are_gone(tm: Taskadence, method: str) -> None:
    assert not hasattr(tm.view_pins, method)


@pytest.mark.parametrize(
    "model", ["TaskInDB", "TaskCreate", "TaskUpdate", "TaskCardView", "ProjectInDB", "ProjectCard", "SprintOut"]
)
def test_no_model_carries_a_team_section_or_tracker_field(model: str) -> None:
    fields = set(SPEC["components"]["schemas"][model]["properties"])
    assert not fields & {"team_id", "section_id", "section_position", "tracker_id", "bug_id"}
    generated = getattr(models, model).__init__.__code__.co_varnames
    assert not set(generated) & {"team_id", "section_id", "tracker_id"}


@pytest.mark.parametrize("name", ["Team", "TeamOut", "TeamCreate", "SectionOut", "SectionCreate", "TaskSectionSet"])
def test_the_removed_models_are_gone(name: str) -> None:
    assert not hasattr(models, name)


def test_the_task_list_no_longer_takes_team_or_section(tm: Taskadence, api: respx.MockRouter) -> None:
    with pytest.raises(ValueError, match="team"):
        tm.tasks.list(org_id="O123456", filter={"team": "TM1"})
    with pytest.raises(TypeError):
        tm.tasks.list(org_id="O123456", section_scope="all")  # type: ignore[call-arg]


def test_no_webhook_event_names_a_team() -> None:
    assert not [name for name in SPEC["webhooks"] if name.startswith("team.") or ".team_" in name]
