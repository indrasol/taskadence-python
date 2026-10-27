"""Release 10, step 2 (API `feature/ia-redesign` b403694): the account (read-only), the account's storage, `me.account`,
project `members`, a workload row's `active_sprint`, and the 409 / 410 problem types — through `respx`, bodies from
the spec's examples."""

from __future__ import annotations

import json
from typing import get_args

import pytest
import respx

import taskadence
from taskadence import (
    AsyncTaskadence,
    ConflictError,
    EmailInOtherAccount,
    EmailInOtherAccountError,
    GoneError,
    RemovedInRelease10,
    RemovedInRelease10Error,
    Taskadence,
    models,
)
from taskadence._generated.types import Unset

from .conftest import SPEC, example, operation, problem

# ---------------------------------------------------------------------------
# the account
# ---------------------------------------------------------------------------


def account_storage(**fields: object) -> dict[str, object]:
    body = example("account.storage") | {
        "account_id": "A1",
        "bytes_used": 12_000_000_000,
        "quota_bytes": 10_000_000_000,
        "available_bytes": 0,
        "overage_bytes": 2_000_000_000,
        "percent": 120.0,
        "status": "metered",
        "payment_method_on_file": True,
    }
    body["orgs"] = [
        {
            "org_id": "O1",
            "name": "Indrasol",
            "bytes_used": 9_000_000_000,
            "file_count": 40,
            "percent_of_quota": 90.0,
            "deleted": False,
        },
        {"org_id": "O2", "name": "Labs", "bytes_used": 3_000_000_000, "percent_of_quota": 30.0, "deleted": True},
    ]
    return body | fields


def account(**fields: object) -> dict[str, object]:
    body = example("account.read") | {"account_id": "A1", "name": "Indrasol", "my_role": "owner"}
    body["billing"] = {"exempt_message": None}
    body["orgs"] = [
        {"org_id": "O1", "name": "Indrasol", "my_role": "owner", "member_count": 12, "bytes_used": 9_000_000_000},
        {"org_id": "O2", "name": "Labs", "my_role": None, "member_count": 3, "bytes_used": 3_000_000_000},
    ]
    body["storage"] = account_storage()
    return body | fields


def test_the_account_with_its_orgs_members_and_storage(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.get("/v1/account").respond(json=account())
    got = tm.account.get()
    assert isinstance(got, models.AccountOut) and route.called
    assert (got.account_id, got.name, got.my_role, got.can_create_orgs) == ("A1", "Indrasol", "owner", False)
    assert [(o.org_id, o.member_count) for o in got.orgs] == [("O1", 12), ("O2", 3)]
    assert got.orgs[1].my_role is None  # an org of the account the caller is not in
    assert isinstance(got.storage, models.AccountStorage) and got.storage.status == "metered"
    assert isinstance(got.billing, models.AccountBillingBrief) and got.billing.exempt_message is None
    assert tm.account.read().account_id == "A1"  # `get` is `read`


def test_an_exempt_account_is_told_so_and_nothing_else(tm: Taskadence, api: respx.MockRouter) -> None:
    message = "Your account is exempt from billing. No charge for this account."
    api.get("/v1/account").respond(json=account(billing={"exempt_message": message}))
    got = tm.account.get()
    assert got.billing.exempt_message == message
    for schema in ("AccountOut", "AccountBillingBrief", "AccountStorage", "StorageUsage"):
        props = SPEC["components"]["schemas"][schema]["properties"]
        assert not {"exempt", "billing_exempt", "exempt_reason", "exempt_until"} & set(props), schema


def test_the_account_people(tm: Taskadence, api: respx.MockRouter) -> None:
    body = example("account.people") | {"account_id": "A1"}
    body["people"] = [
        {
            "user_id": "U1",
            "username": "ada",
            "email": "ada@example.com",
            "account_role": "owner",
            "orgs": [{"org_id": "O1", "name": "Indrasol", "role": "owner"}, {"org_id": "O2", "role": "member"}],
        },
        {"user_id": "U9", "username": "otto", "kind": "user", "account_role": None, "other_account": True, "orgs": []},
    ]
    route = api.get("/v1/account/people").respond(json=body)
    got = tm.account.people()
    assert isinstance(got, models.AccountPeople) and route.called
    ada, otto = got.people
    assert isinstance(ada, models.AccountPerson) and ada.account_role is not None
    assert ada.account_role == "owner" and [(o.org_id, o.role) for o in ada.orgs] == [
        ("O1", "owner"),
        ("O2", "member"),
    ]
    assert isinstance(ada.orgs[0], models.PersonOrg)
    assert otto.other_account is True and otto.account_role is None and otto.kind == "user"


def test_the_account_people_are_for_owners_and_admins(tm: Taskadence, api: respx.MockRouter) -> None:
    api.get("/v1/account/people").respond(403, json=problem(403, detail="Account owners and admins only"))
    with pytest.raises(taskadence.ForbiddenError):
        tm.account.people()


def test_the_account_storage_is_tm_storage_get(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.get("/v1/storage").respond(json=account_storage())
    got = tm.storage.get()
    again = tm.account.storage()
    assert route.call_count == 2 and isinstance(got, models.AccountStorage)
    assert (got.bytes_used, got.quota_bytes, got.overage_bytes) == (12_000_000_000, 10_000_000_000, 2_000_000_000)
    assert got.status == "metered" and got.payment_method_on_file is True and got.percent == 120.0
    assert [(o.org_id, o.deleted) for o in got.orgs] == [("O1", False), ("O2", True)]
    assert isinstance(got.orgs[0], models.AccountStorageOrg) and got.orgs[0].file_count == 40
    assert again.to_dict() == got.to_dict()
    statuses = SPEC["components"]["schemas"]["AccountStorage"]["properties"]["status"]["enum"]
    assert set(get_args(models.AccountStorageStatus)) == set(statuses) and "metered" in statuses


def test_the_account_is_read_only_and_token_scoped_account_read() -> None:
    for op_id in ("account.read", "account.people", "account.storage"):
        method, _, op = operation(op_id)
        assert method == "GET" and op["x-scopes"] == ["account:read"], op_id
        assert taskadence.OPERATIONS[op_id].method == "GET"
    paths = [p for p in SPEC["paths"] if p.startswith("/v1/account") or "billing" in p]
    assert sorted(paths) == ["/v1/account", "/v1/account/people"]  # no billing route, no write on /v1/account*
    assert {m for p in paths for m in SPEC["paths"][p]} == {"get"}
    assert not any("billing" in name for name in dir(tm_resources()))


def tm_resources() -> object:
    return Taskadence(token="tkd_test_x").organizations


def test_an_orgs_storage_reads_the_account(tm: Taskadence, api: respx.MockRouter) -> None:
    body = example("organizations.storage") | {
        "org_id": "O1",
        "account_id": "A1",
        "account_used_bytes": 12_000_000_000,
        "account_quota_bytes": 10_000_000_000,
        "account_percent": 120.0,
        "exempt_message": None,
        "status": "metered",
    }
    api.get("/v1/organizations/O1/storage").respond(json=body)
    got = tm.organizations.storage("O1")
    assert isinstance(got, models.StorageUsage)
    assert (got.account_id, got.account_used_bytes, got.account_quota_bytes, got.account_percent) == (
        "A1",
        12_000_000_000,
        10_000_000_000,
        120.0,
    )
    assert got.exempt_message is None and not hasattr(got, "billing_exempt")
    assert "billing_exempt" not in SPEC["components"]["schemas"]["StorageUsage"]["properties"]


def test_me_names_the_account(tm: Taskadence, api: respx.MockRouter) -> None:
    body = example("me.read") | {"account": {"account_id": "A1", "name": "Indrasol", "role": "admin"}}
    api.get("/v1/me").respond(json=body)
    me = tm.me.get()
    assert isinstance(me.account, models.MeAccount)
    assert (me.account.account_id, me.account.name, me.account.role) == ("A1", "Indrasol", "admin")
    api.get("/v1/me").respond(json=example("me.read") | {"account": None})
    assert tm.me().account is None


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
# errors: 409 email_in_other_account, 410 removed-in-release-10
# ---------------------------------------------------------------------------

EMAIL_TAKEN = problem(
    409,
    "urn:taskadence:problem:email-in-other-account",
    "This person already uses TasKadence with another account. One email can belong to one account.",
    errors=[{"loc": ["body", "email"], "msg": "…", "code": "email_in_other_account"}],
)


def test_an_invite_of_an_email_in_another_account_is_typed(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.post("/v1/organization-invites").respond(409, json=EMAIL_TAKEN)
    with pytest.raises(EmailInOtherAccountError) as caught:
        tm.organization_invites.create({"org_id": "O1", "email": "otto@example.com"})
    err = caught.value
    assert isinstance(err, ConflictError) and EmailInOtherAccount is EmailInOtherAccountError
    assert err.status == 409 and err.slug == "email-in-other-account"
    assert err.errors[0]["code"] == "email_in_other_account"
    assert route.call_count == 1


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
    assert types["urn:taskadence:problem:email-in-other-account"] == [409]
    assert types["urn:taskadence:problem:removed-in-release-10"] == [410]


# ---------------------------------------------------------------------------
# not in the SDK; async
# ---------------------------------------------------------------------------


def test_support_tickets_and_billing_are_not_sdk_methods() -> None:
    ops = set(taskadence.OPERATIONS)
    assert not any(op.startswith(("support", "billing")) or "billing" in op for op in ops)
    assert not any(p.startswith(("/v1/support", "/v1/account/billing")) for p in SPEC["paths"])
    tm = Taskadence(token="tkd_test_x")
    assert not hasattr(tm, "support") and not hasattr(tm, "billing")
    assert not [m for m in dir(tm.account) if not m.startswith("_") and m not in ("get", "read", "people", "storage")]


@pytest.mark.anyio
async def test_async_account_storage_and_me(atm: AsyncTaskadence, api: respx.MockRouter) -> None:
    api.get("/v1/account").respond(json=account())
    api.get("/v1/storage").respond(json=account_storage())
    api.get("/v1/account/people").respond(json={"account_id": "A1", "people": []})
    assert (await atm.account.get()).account_id == "A1"
    assert (await atm.storage.get()).status == "metered"
    assert (await atm.account.people()).people == []
