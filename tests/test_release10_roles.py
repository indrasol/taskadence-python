"""Release 10, step 3 (API `feature/ia-redesign` e124d44): project roles `owner | member | viewer`, org owners / admins
as implicit project owners, `projects.list(scope=)`, batch members, task subscribers, and ids past 6 digits — through
`respx`, bodies from the spec's examples."""

from __future__ import annotations

import json
from typing import get_args

import pytest
import respx

from taskadence import AsyncTaskadence, Taskadence, models, webhooks
from taskadence._generated.models.project_member_in_db_source import ProjectMemberInDBSource

from .conftest import SPEC, example, operation, task
from .test_webhooks_dataframe_async import BODY

# ---------------------------------------------------------------------------
# roles
# ---------------------------------------------------------------------------


def test_project_roles_are_owner_member_viewer() -> None:
    assert set(get_args(models.ProjectRoleEnum)) == {"owner", "member", "viewer"}
    assert SPEC["components"]["schemas"]["ProjectRoleEnum"]["enum"] == ["owner", "member", "viewer"]
    assert set(get_args(ProjectMemberInDBSource)) == {"member", "org_owner", "org_admin"}


def test_the_sdk_sends_member(tm: Taskadence, api: respx.MockRouter) -> None:
    body = example("project-members.create") | {"project_id": "P1", "user_id": "U1", "project_role": "member"}
    route = api.post("/v1/project-members").respond(json=body)
    got = tm.project_members.create(models.ProjectMemberCreate(project_id="P1", user_id="U1", project_role="member"))
    assert json.loads(route.calls.last.request.content)["project_role"] == "member"
    assert got.project_role == "member" and got.source == "member" and got.removable is True


def test_org_owners_and_admins_are_listed_as_unremovable_owners(tm: Taskadence, api: respx.MockRouter) -> None:
    page = example("project-members.list")
    row = page["data"][0]
    page["data"] = [
        row | {"user_id": "U1", "project_role": "member", "source": "member", "removable": True},
        row | {"user_id": "U2", "project_role": "owner", "source": "org_admin", "removable": False},
    ]
    page["next_cursor"] = None
    route = api.get("/v1/project-members").respond(json=page)
    member, admin = list(tm.project_members.list(project_id="P1"))
    assert route.calls.last.request.url.params["project_id"] == "P1"
    assert (member.source, member.removable) == ("member", True)
    assert (admin.source, admin.project_role, admin.removable) == ("org_admin", "owner", False)


def test_a_project_names_its_implicit_owners_and_who_may_add_people(tm: Taskadence, api: respx.MockRouter) -> None:
    body = example("projects.read") | {"project_id": "P1", "members_can_add_people": True}
    body["editors_can_add_members"] = True  # the deprecated name, still answered
    body["implicit_members"] = [
        {"user_id": "U9", "username": "ada", "project_role": "owner", "source": "org_owner", "removable": False}
    ]
    api.get("/v1/projects/detail/P1").respond(json=body)
    got = tm.projects.read("P1")
    assert got.members_can_add_people is True and got.editors_can_add_members is True
    (owner,) = got.implicit_members
    assert isinstance(owner, models.ProjectImplicitMember)
    assert (owner.user_id, owner.source, owner.project_role, owner.removable) == ("U9", "org_owner", "owner", False)
    assert SPEC["components"]["schemas"]["ProjectInDB"]["properties"]["editors_can_add_members"]["deprecated"]


def test_members_can_add_people_is_sent_on_an_update(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.patch("/v1/projects/P1").respond(json=example("projects.update"))
    tm.projects.update("P1", models.ProjectUpdate(members_can_add_people=True))
    assert json.loads(route.calls.last.request.content) == {"members_can_add_people": True}


@pytest.mark.parametrize("scope", ["all", "mine"])
def test_projects_list_takes_a_scope(tm: Taskadence, api: respx.MockRouter, scope: str) -> None:
    page = example("projects.list") | {"next_cursor": None}
    route = api.get("/v1/projects/O1").respond(json=page)
    list(tm.projects.list("O1", scope=scope))
    assert route.calls.last.request.url.params["scope"] == scope


def test_projects_list_sends_no_scope_unless_asked(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.get("/v1/projects/O1").respond(json=example("projects.list") | {"next_cursor": None})
    list(tm.projects.list("O1"))
    assert "scope" not in route.calls.last.request.url.params


# ---------------------------------------------------------------------------
# batch members
# ---------------------------------------------------------------------------


def batch_added() -> dict[str, object]:
    body = example("project-members.create_batch")
    body["added"][0] |= {"project_id": "P1", "user_id": "U1", "project_role": "member"}
    body["skipped"] = [{"user_id": "U2", "reason": "already_member"}]
    return body


def test_add_many_wraps_the_list_and_answers_added_and_skipped(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.post("/v1/projects/P1/members/batch").respond(json=batch_added())
    got = tm.projects.members.add_many(
        "P1",
        [
            {"user_id": "U1", "project_role": "member"},
            models.ProjectMemberBatchItem(user_id="U2", project_role="viewer"),
        ],
    )
    assert json.loads(route.calls.last.request.content) == {
        "members": [{"user_id": "U1", "project_role": "member"}, {"user_id": "U2", "project_role": "viewer"}]
    }
    assert isinstance(got, models.ProjectMembersBatchAdded)
    assert [(m.user_id, m.project_role) for m in got.added] == [("U1", "member")]
    assert [(s.user_id, s.reason) for s in got.skipped] == [("U2", "already_member")]


def test_add_many_is_the_generated_create_batch(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.post("/v1/projects/P1/members/batch").respond(json=batch_added())
    tm.project_members.create_batch("P1", ({"user_id": "U1", "project_role": "owner"},))
    assert json.loads(route.calls.last.request.content) == {"members": [{"user_id": "U1", "project_role": "owner"}]}
    method, path, op = operation("project-members.create_batch")
    assert (method, path, op["x-scopes"]) == ("POST", "/v1/projects/{project_id}/members/batch", ["projects:write"])
    assert SPEC["components"]["schemas"]["ProjectMembersBatchAdd"]["properties"]["members"]["maxItems"] == 50


def test_add_many_refuses_a_mapping_instead_of_a_list(tm: Taskadence) -> None:
    with pytest.raises(TypeError, match="members must be a list"):
        tm.projects.members.add_many("P1", {"user_id": "U1", "project_role": "member"})  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# subscribers
# ---------------------------------------------------------------------------


def subscribers(*user_ids: str, me: bool = False) -> dict[str, object]:
    body = example("tasks.list_subscribers")
    item = body["subscribers"][0] if body.get("subscribers") else {}
    body |= {
        "task_id": "T1",
        "subscribers": [item | {"user_id": u, "username": u.lower()} for u in user_ids],
        "subscriber_ids": list(user_ids),
        "is_subscribed": me,
    }
    return body


def test_list_a_tasks_subscribers(tm: Taskadence, api: respx.MockRouter) -> None:
    api.get("/v1/tasks/T1/subscribers").respond(json=subscribers("U1", "U2", me=True))
    got = tm.tasks.subscribers("T1")
    assert isinstance(got, models.TaskSubscribers)
    assert got.subscriber_ids == ["U1", "U2"] and got.is_subscribed is True
    assert all(isinstance(s, models.TaskSubscriber) for s in got.subscribers)
    assert tm.tasks.subscribers == tm.tasks.list_subscribers  # the alias is the generated method


def test_set_the_full_list_of_subscribers(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.put("/v1/tasks/T1/subscribers").respond(json=subscribers("U3"))
    got = tm.tasks.set_subscribers("T1", ["U3"])
    assert json.loads(route.calls.last.request.content) == {"user_ids": ["U3"]}
    assert got.subscriber_ids == ["U3"]


def test_set_subscribers_to_nobody_and_refuse_a_bare_string(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.put("/v1/tasks/T1/subscribers").respond(json=subscribers())
    tm.tasks.set_subscribers("T1", [])
    assert json.loads(route.calls.last.request.content) == {"user_ids": []}
    with pytest.raises(TypeError, match="user_ids must be a list, not str"):
        tm.tasks.set_subscribers("T1", "U3")


def test_subscribe_and_unsubscribe_yourself(tm: Taskadence, api: respx.MockRouter) -> None:
    on = api.post("/v1/tasks/T1/subscribers/me").respond(json=subscribers("U1", me=True))
    off = api.delete("/v1/tasks/T1/subscribers/me").respond(json=subscribers())
    assert tm.tasks.subscribe("T1").is_subscribed is True and on.called
    assert tm.tasks.unsubscribe("T1").is_subscribed is False and off.called
    for op_id, scope in [
        ("tasks.list_subscribers", "tasks:read"),
        ("tasks.set_subscribers", "tasks:write"),
        ("tasks.subscribe", "tasks:write"),
        ("tasks.unsubscribe", "tasks:write"),
    ]:
        assert operation(op_id)[2]["x-scopes"] == [scope], op_id


def test_a_task_read_says_who_is_subscribed(tm: Taskadence, api: respx.MockRouter) -> None:
    api.get("/v1/tasks/T1").respond(json=task("T1", subscriber_ids=["U1", "U2"], is_subscribed=False))
    got = tm.tasks.read("T1")
    assert got.subscriber_ids == ["U1", "U2"] and got.is_subscribed is False


def test_a_task_from_a_list_has_no_subscribers_set(tm: Taskadence, api: respx.MockRouter) -> None:
    body = task("T1")
    body.pop("subscriber_ids", None)
    body.pop("is_subscribed", None)
    api.get("/v1/tasks/T1").respond(json=body)
    got = tm.tasks.read("T1")
    assert not got.subscriber_ids and not got.is_subscribed


# ---------------------------------------------------------------------------
# ids: 6 to 12 digits
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("task_id", ["T123456", "T1234567", "T123456789012"])
def test_ids_of_6_to_12_digits_reach_the_api_as_they_are(tm: Taskadence, api: respx.MockRouter, task_id: str) -> None:
    route = api.get(f"/v1/tasks/{task_id}").respond(json=task(task_id, project_id="P123456789012"))
    got = tm.tasks.read(task_id)
    assert route.called and got.task_id == task_id and got.project_id == "P123456789012"
    api.get(f"/v1/tasks/{task_id}/subscribers").respond(json=subscribers("U1") | {"task_id": task_id})
    assert tm.tasks.subscribers(task_id).task_id == task_id


def test_a_webhook_with_12_digit_ids_parses() -> None:
    body = json.loads(BODY) | {"id": "WD123456789012", "org_id": "O123456789012", "project_id": "P123456789012"}
    body["data"]["resource_id"] = "T123456789012"
    event = webhooks.parse(body)
    assert (event.id, event.project_id, event.data.resource_id) == ("WD123456789012", "P123456789012", "T123456789012")


def test_no_sdk_side_id_pattern_caps_the_width() -> None:
    """The spec declares no id `pattern`, and the SDK adds none: an id is an opaque string to it."""
    text = json.dumps(SPEC)
    assert "{6}" not in text and "\\d{6" not in text


# ---------------------------------------------------------------------------
# async
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_async_batch_members_and_subscribers(atm: AsyncTaskadence, api: respx.MockRouter) -> None:
    batch = api.post("/v1/projects/P1/members/batch").respond(json=batch_added())
    api.put("/v1/tasks/T1/subscribers").respond(json=subscribers("U1"))
    api.post("/v1/tasks/T1/subscribers/me").respond(json=subscribers("U1", me=True))
    got = await atm.projects.members.add_many("P1", [{"user_id": "U1", "project_role": "member"}])
    assert got.added[0].user_id == "U1" and batch.called
    assert (await atm.tasks.set_subscribers("T1", ["U1"])).subscriber_ids == ["U1"]
    assert (await atm.tasks.subscribe("T1")).is_subscribed is True
