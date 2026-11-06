"""Release 11 (API `feature/org-billing`): the organization is the top level. The account routes answer 410, plan and
state are on organizations, a suspended or waiting organization has typed errors, and billing stays out of the SDK
because the API refuses every access token on those routes. Through `respx`, the routes and fields from the spec."""

from __future__ import annotations

import pytest
import respx

import taskadence
from taskadence import (
    AsyncTaskadence,
    BillingOwnerMustHandOverError,
    ConflictError,
    GoneError,
    OrganizationPendingPaymentError,
    OrganizationReadOnlyError,
    OrganizationRestrictedError,
    OrganizationSuspendedError,
    RemovedInRelease10Error,
    RemovedInRelease11Error,
    Taskadence,
    TaskadenceError,
    models,
)

from .conftest import SPEC, example, problem

URN = "urn:taskadence:problem:"
SINCE = "2026-11-05T10:00:00Z"
SCHEMAS = SPEC["components"]["schemas"]


def gone(successor: str) -> dict[str, object]:
    detail = "The account level was removed: an organization is now the top level."
    return problem(410, URN + "gone", detail, successor=successor)


# ---------------------------------------------------------------------------
# the account methods: a typed 410 with the server's message
# ---------------------------------------------------------------------------

REMOVED = [
    ("/v1/account", "/v1/organizations", lambda tm: tm.account.read()),
    ("/v1/account", "/v1/organizations", lambda tm: tm.account.get()),
    ("/v1/account/people", "/v1/organizations/{org_id}/members", lambda tm: tm.account.people()),
    ("/v1/storage", "/v1/organizations/{org_id}/storage", lambda tm: tm.account.storage()),
    ("/v1/storage", "/v1/organizations/{org_id}/storage", lambda tm: tm.storage.get()),
]


@pytest.mark.parametrize(("path", "successor", "call"), REMOVED)
def test_a_removed_account_method_raises_the_410(
    tm: Taskadence, api: respx.MockRouter, slept: list[float], path: str, successor: str, call: object
) -> None:
    route = api.get(path).respond(410, json=gone(successor))
    with pytest.raises(RemovedInRelease11Error) as caught:
        call(tm)  # type: ignore[operator]
    err = caught.value
    assert isinstance(err, RemovedInRelease10Error) and isinstance(err, GoneError)
    assert "The account level was removed" in str(err) and err.successor == successor and successor in str(err)
    assert err.slug == "gone" and route.call_count == 1 and slept == []  # a safe GET, and still no retry


@pytest.mark.anyio
async def test_a_removed_account_method_raises_the_410_async(atm: AsyncTaskadence, api: respx.MockRouter) -> None:
    api.get("/v1/account").respond(410, json=gone("/v1/organizations"))
    api.get("/v1/storage").respond(410, json=gone("/v1/organizations/{org_id}/storage"))
    with pytest.raises(RemovedInRelease11Error):
        await atm.account.get()
    with pytest.raises(RemovedInRelease11Error):
        await atm.storage.get()


def test_the_account_is_gone_from_the_contract() -> None:
    assert not [name for name in SCHEMAS if name.startswith(("Account", "MeAccount"))]
    assert "account" not in SCHEMAS["MeOut"]["properties"]
    assert not hasattr(models, "AccountOut") and not hasattr(models, "MeAccount")
    for op_id in ("account.read", "account.people", "account.storage"):
        assert taskadence.OPERATIONS[op_id].method == "GET"
    assert not hasattr(taskadence, "EmailInOtherAccountError")


def test_the_deprecated_routes_answer_nothing_but_the_410() -> None:
    for path in ("/v1/account", "/v1/account/people", "/v1/storage"):
        operation = SPEC["paths"][path]["get"]
        assert operation["deprecated"] is True and set(operation["responses"]) == {"410"}, path


# ---------------------------------------------------------------------------
# plan and state on organizations; the storage read
# ---------------------------------------------------------------------------


def test_organizations_carry_plan_and_state(tm: Taskadence, api: respx.MockRouter) -> None:
    card = example("organizations.list")["data"][0] | {
        "org_id": "O1",
        "name": "Acme",
        "plan": "paid",
        "state": "read_only",
        "state_since": SINCE,
        "billing_owner_user_id": "U1",
        "pending_billing_owner_user_id": "U2",
        "grandfathered": False,
    }
    api.get("/v1/organizations").respond(json={"data": [card], "next_cursor": None})
    org = next(iter(tm.organizations.list()))
    assert isinstance(org, models.OrgCard) and (org.plan, org.state) == ("paid", "read_only")
    assert org.state_since is not None and org.state_since.year == 2026
    assert (org.billing_owner_user_id, org.pending_billing_owner_user_id, org.grandfathered) == ("U1", "U2", False)

    api.get("/v1/me").respond(
        json=example("me.read")
        | {"organizations": [{"org_id": "O1", "name": "Acme", "role": "owner", "plan": "free", "state": "active"}]}
    )
    mine = tm.me().organizations[0]
    assert isinstance(mine, models.MeOrganization) and (mine.plan, mine.state) == ("free", "active")
    assert not hasattr(tm.me(), "account")


def test_storage_measures_the_organization_alone(tm: Taskadence, api: respx.MockRouter) -> None:
    body = example("organizations.storage") | {
        "org_id": "O1",
        "plan": "paid",
        "state": "active",
        "billing_exempt": False,
    }
    api.get("/v1/organizations/O1/storage").respond(json=body)
    got = tm.organizations.storage("O1")
    assert isinstance(got, models.StorageUsage) and (got.plan, got.state, got.billing_exempt) == (
        "paid",
        "active",
        False,
    )
    assert not {"account_id", "account_used_bytes", "account_quota_bytes", "account_percent"} & set(
        SCHEMAS["StorageUsage"]["properties"]
    )


# ---------------------------------------------------------------------------
# the typed 423s and 409s
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("slug", "cls", "state"),
    [
        ("organization-restricted", OrganizationRestrictedError, "restricted"),
        ("organization-read-only", OrganizationReadOnlyError, "read_only"),
    ],
)
def test_a_423_says_the_state_and_since_and_is_not_retried(
    tm: Taskadence, api: respx.MockRouter, slept: list[float], slug: str, cls: type[TaskadenceError], state: str
) -> None:
    body = problem(423, URN + slug, "A card restores it.", errors=[{"state": state, "since": SINCE}])
    route = api.get("/v1/me").respond(423, json=body)
    with pytest.raises(cls) as caught:
        tm.me.get()
    err = caught.value
    assert isinstance(err, OrganizationSuspendedError) and err.status == 423 and err.detail == "A card restores it."
    assert (err.state, err.since) == (state, SINCE)
    assert route.call_count == 1 and slept == []


def test_a_plain_423_is_still_typed(tm: Taskadence, api: respx.MockRouter) -> None:
    api.get("/v1/me").respond(423, json=problem(423))
    with pytest.raises(OrganizationSuspendedError) as caught:
        tm.me.get()
    assert (caught.value.state, caught.value.since) == (None, None)


def test_a_waiting_organization_is_typed(tm: Taskadence, api: respx.MockRouter) -> None:
    route_name = "/v1/organizations/O1/billing/setup-session"
    body = problem(
        409, URN + "organization-pending-payment", "It waits for its card.", org_id="O1", setup_url_route=route_name
    )
    api.get("/v1/organizations/O1").respond(409, json=body)
    with pytest.raises(OrganizationPendingPaymentError) as caught:
        tm.organizations.read("O1")
    err = caught.value
    assert isinstance(err, ConflictError) and (err.org_id, err.setup_url_route) == ("O1", route_name)


def test_the_billing_owner_must_hand_over_first(tm: Taskadence, api: respx.MockRouter) -> None:
    route_name = "/v1/organizations/O1/billing-owner"
    body = problem(409, URN + "billing-owner-must-hand-over", "Hand it over.", org_id="O1", handover_route=route_name)
    api.get("/v1/me").respond(409, json=body)
    with pytest.raises(BillingOwnerMustHandOverError) as caught:
        tm.me.get()
    assert isinstance(caught.value, ConflictError)
    assert (caught.value.org_id, caught.value.handover_route) == ("O1", route_name)


def test_every_release_11_problem_type_is_in_the_spec_and_mapped() -> None:
    types = {p["type"]: p["statuses"] for p in SPEC["x-problem-types"]}
    for slug, status in (
        ("gone", 410),
        ("organization-pending-payment", 409),
        ("billing-owner-must-hand-over", 409),
        ("organization-restricted", 423),
        ("organization-read-only", 423),
    ):
        assert types[URN + slug] == [status], slug
        assert URN + slug in taskadence.errors.BY_TYPE, slug
    assert URN + "email-in-other-account" not in taskadence.errors.BY_TYPE


# ---------------------------------------------------------------------------
# not in the SDK: the contract keeps them internal, and the API refuses a token there
# ---------------------------------------------------------------------------


def test_billing_and_creating_an_organization_are_not_sdk_methods() -> None:
    ops = set(taskadence.OPERATIONS)
    assert not any(op.startswith(("support", "billing")) or "billing" in op for op in ops)
    assert "organizations.create" not in ops
    assert not any("billing" in path for path in SPEC["paths"])
    assert "post" not in SPEC["paths"]["/v1/organizations"]
    tm = Taskadence(token="tkd_test_x")
    assert not hasattr(tm, "support") and not hasattr(tm, "billing")
    for name in ("create", "billing", "set_billing_owner", "cancel_billing_owner"):
        assert not hasattr(tm.organizations, name), name
