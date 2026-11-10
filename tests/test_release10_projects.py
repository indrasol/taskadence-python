"""Release 10, step 2 (API `feature/ia-redesign` b403694): project `members`, a workload row's `active_sprint`, and the
410 problem type — through `respx`, bodies from the spec's examples. Its account half left with release 11
(`test_release11_orgs.py`)."""

from __future__ import annotations

import json

import pytest
import respx

from taskadence import (
    GoneError,
    RemovedInRelease10,
    RemovedInRelease10Error,
    Taskadence,
    models,
)
from taskadence._generated.types import Unset

from .conftest import SPEC, example, operation, problem

# ---------------------------------------------------------------------------
# projects: members, position
# ---------------------------------------------------------------------------


def test_projects_say_members_not_team_members(tm: Taskadence, api: respx.MockRouter) -> None:
    created = example("projects.create") | {"project_id": "P1", "members": ["U1", "U2"], "position": 3}
    route = api.post("/v1/projects").respond(json=created)
    got = tm.projects.create(models.ProjectCreate(org_id="O1", name="Web", members=["ada", "lin"]))
    sent = json.loads(route.calls.last.request.content)
    assert sent["members"] == ["ada", "lin"] and "team_members" not in sent
    assert got.members == ["U1", "U2"] and got.position == 3 and not hasattr(got, "team_members")
    for name in ("ProjectCreate", "ProjectUpdate", "ProjectInDB", "ProjectCard"):
        assert "team_members" not in SPEC["components"]["schemas"][name]["properties"], name
    upd = api.patch("/v1/projects/P1").respond(json=example("projects.update"))
    tm.projects.update("P1", models.ProjectUpdate(members=["U3"]))
    assert json.loads(upd.calls.last.request.content) == {"members": ["U3"]}


def test_the_single_project_read_returns_its_position(tm: Taskadence, api: respx.MockRouter) -> None:
    api.get("/v1/projects/detail/P1").respond(json=example("projects.read") | {"project_id": "P1", "position": 4})
    project = tm.projects.read("P1")
    assert isinstance(project, models.ProjectInDB) and project.position == 4
    _, _, op = operation("projects.read")
    ref = op["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    assert "position" in SPEC["components"]["schemas"][ref.rsplit("/", 1)[-1]]["properties"]


def test_project_stats_count_members(tm: Taskadence, api: respx.MockRouter) -> None:
    schema = SPEC["components"]["schemas"]["ProjectStatsInDB"]
    assert "members" in schema["required"] and "team_members" not in schema["properties"]


# ---------------------------------------------------------------------------
# workload: active_sprint
# ---------------------------------------------------------------------------


def workload(*people: dict[str, object]) -> dict[str, object]:
    body = example("workload.read") | {"org_id": "O1", "project_id": None}
    row = body["people"][0]
    body["people"] = [row | p for p in people]
    return body


def test_a_workload_row_names_the_persons_active_sprint(tm: Taskadence, api: respx.MockRouter) -> None:
    sprint = {"sprint_id": "SP1", "name": "Sprint 7", "done": 3, "total": 8}
    api.get("/v1/organizations/O1/workload").respond(
        json=workload({"user_id": "U1", "active_sprint": sprint}, {"user_id": "U2", "active_sprint": None})
    )
    rows = tm.workload.read("O1").people
    assert isinstance(rows, list)
    busy, free = rows
    assert isinstance(busy.active_sprint, models.WorkloadSprint)
    assert (busy.active_sprint.sprint_id, busy.active_sprint.name) == ("SP1", "Sprint 7")
    assert (busy.active_sprint.done, busy.active_sprint.total) == (3, 8)
    assert free.active_sprint is None


def test_an_older_workload_row_without_active_sprint_still_parses(tm: Taskadence, api: respx.MockRouter) -> None:
    body = workload({"user_id": "U1"})
    del body["people"][0]["active_sprint"]
    api.get("/v1/organizations/O1/workload").respond(json=body)
    assert isinstance(tm.organizations.workload("O1").people[0].active_sprint, Unset)


# ---------------------------------------------------------------------------
# errors: 410 removed-in-release-10
# ---------------------------------------------------------------------------


def removed(**extra: object) -> dict[str, object]:
    return problem(
        410,
        "urn:taskadence:problem:removed-in-release-10",
        "This endpoint was removed in release 10. Teams left the product.",
        changelog="https://docs.taskadence.com/changelog",
        **extra,
    )


def test_a_removed_route_is_typed_names_the_changelog_and_is_not_retried(
    tm: Taskadence, api: respx.MockRouter, slept: list[float]
) -> None:
    route = api.get("/v1/me").respond(410, json=removed(successor="/v1/sprints"))
    with pytest.raises(RemovedInRelease10Error) as caught:
        tm.me.get()
    err = caught.value
    assert isinstance(err, GoneError) and RemovedInRelease10 is RemovedInRelease10Error
    assert err.changelog == "https://docs.taskadence.com/changelog" and err.successor == "/v1/sprints"
    assert "https://docs.taskadence.com/changelog" in str(err) and "/v1/sprints" in str(err)
    assert route.call_count == 1 and slept == []  # a safe GET, and still no retry


def test_a_410_without_extensions_still_links_the_changelog(tm: Taskadence, api: respx.MockRouter) -> None:
    api.get("/v1/me").respond(410, json=problem(410, "urn:taskadence:problem:removed-in-release-10", "Gone."))
    with pytest.raises(RemovedInRelease10Error) as caught:
        tm.me.get()
    assert caught.value.successor is None and str(caught.value).endswith("See https://docs.taskadence.com/changelog")


def test_a_plain_410_is_a_gone_error(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.get("/v1/me").respond(410, json=problem(410))
    with pytest.raises(GoneError) as caught:
        tm.me.get()
    assert not isinstance(caught.value, RemovedInRelease10Error) and route.call_count == 1


def test_the_new_problem_types_are_in_the_spec() -> None:
    types = {p["type"]: p["statuses"] for p in SPEC["x-problem-types"]}
    assert "urn:taskadence:problem:email-in-other-account" not in types  # removed in release 11
    assert types["urn:taskadence:problem:removed-in-release-10"] == [410]
