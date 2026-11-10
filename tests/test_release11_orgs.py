"""Release 11 (API `feature/org-billing`, final model `2026-11-06`): the organization is the top level and billing is
the billing owner's (one card per person, in the web app). The account routes answer 410; state, the fee and the billing
owner are on the organization reads; a restricted, read-only or locked organization and a full one have typed errors;
billing and creating an organization stay out of the SDK because the API refuses every access token on those routes;
the legal notice is read without the token. Through `respx`, the routes and fields from the spec."""

from __future__ import annotations

import pytest
import respx

import taskadence
from taskadence import (
    AsyncTaskadence,
    BillingOwnerMustHandOverError,
    ConflictError,
    GoneError,
    LegalNotice,
    OrganizationLockedError,
    OrganizationReadOnlyError,
    OrganizationRestrictedError,
    OrganizationSuspendedError,
    PaymentRequiredError,
    RemovedInRelease10Error,
    RemovedInRelease11Error,
    StorageLimitReachedError,
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
# state, the fee and the billing owner on organizations; plan is gone
# ---------------------------------------------------------------------------


def test_organizations_carry_state_and_no_plan(tm: Taskadence, api: respx.MockRouter) -> None:
    card = example("organizations.list")["data"][0] | {
        "org_id": "O1",
        "name": "Acme",
        "state": "locked",
        "state_since": SINCE,
        "billing_owner_user_id": "U1",
        "grandfathered": True,
    }
    api.get("/v1/organizations").respond(json={"data": [card], "next_cursor": None})
    org = next(iter(tm.organizations.list()))
    assert isinstance(org, models.OrgCard) and org.state == "locked"
    assert org.state_since is not None and org.state_since.year == 2026
    assert (org.billing_owner_user_id, org.grandfathered) == ("U1", True)
    assert not hasattr(org, "plan") and not hasattr(org, "pending_billing_owner_user_id")

    api.get("/v1/me").respond(
        json=example("me.read")
        | {"organizations": [{"org_id": "O1", "name": "Acme", "role": "owner", "state": "active"}]}
    )
    mine = tm.me().organizations[0]
    assert isinstance(mine, models.MeOrganization) and mine.state == "active" and not hasattr(mine, "plan")
    assert not hasattr(tm.me(), "account")
    for name in ("OrgCard", "OrganizationInDB", "MeOrganization", "StorageUsage"):
        assert not {"plan", "pending_billing_owner_user_id"} & set(SCHEMAS[name]["properties"]), name
    assert set(SCHEMAS["StorageUsage"]["properties"]["state"]["enum"]) == {
        "active",
        "restricted",
        "read_only",
        "locked",
        "archived",
    }


@pytest.mark.parametrize(
    ("fee", "owner"),
    [
        ({"amount_cents": 100, "reason": "none"}, {"user_id": "U1", "name": "Ada"}),
        ({"amount_cents": 0, "reason": "first"}, {"user_id": "U1", "name": None}),
        ({"amount_cents": 0, "reason": "grandfathered"}, None),
    ],
)
def test_storage_names_the_fee_and_who_pays(
    tm: Taskadence, api: respx.MockRouter, fee: dict[str, object], owner: dict[str, object] | None
) -> None:
    body = example("organizations.storage") | {
        "org_id": "O1",
        "state": "active",
        "billing_exempt": False,
        "included_bytes": 10**10,
        "fee": fee,
        "billing_owner": owner,
    }
    api.get("/v1/organizations/O1/storage").respond(json=body)
    got = tm.organizations.storage("O1")
    assert isinstance(got, models.StorageUsage) and got.included_bytes == 10**10 and not hasattr(got, "plan")
    assert isinstance(got.fee, models.StorageFee)
    assert (int(got.fee.amount_cents), str(got.fee.reason)) == (fee["amount_cents"], fee["reason"])
    if owner is None:
        assert got.billing_owner is None
    else:
        assert isinstance(got.billing_owner, models.StorageBillingOwner)
        assert (got.billing_owner.user_id, got.billing_owner.name) == (owner["user_id"], owner["name"])
    assert not {"account_id", "account_used_bytes", "account_quota_bytes", "account_percent"} & set(
        SCHEMAS["StorageUsage"]["properties"]
    )
    assert set(SCHEMAS["StorageFee"]["properties"]["reason"]["enum"]) == {"first", "grandfathered", "exempt", "none"}


# ---------------------------------------------------------------------------
# the typed 423s and 409s
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("slug", "cls", "state"),
    [
        ("organization-restricted", OrganizationRestrictedError, "restricted"),
        ("organization-read-only", OrganizationReadOnlyError, "read_only"),
        ("organization-locked", OrganizationLockedError, "locked"),
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


def test_a_locked_organization_says_when_it_is_archived_and_deleted(tm: Taskadence, api: respx.MockRouter) -> None:
    lock = {"state": "locked", "since": SINCE, "archive_on": "2026-12-05", "delete_on": "2027-01-04"}
    body = problem(423, URN + "organization-locked", "It is locked.", errors=[lock])
    route = api.get("/v1/organizations/O1/storage").respond(423, json=body)
    with pytest.raises(OrganizationLockedError) as caught:
        tm.organizations.storage("O1")
    err = caught.value
    assert isinstance(err, OrganizationSuspendedError) and route.call_count == 1
    assert (err.state, err.since, err.archive_on, err.delete_on) == ("locked", SINCE, "2026-12-05", "2027-01-04")


def test_a_full_organization_is_a_typed_402(tm: Taskadence, api: respx.MockRouter, slept: list[float]) -> None:
    manage = "https://app.taskadence.com/settings?tab=storage"
    body = problem(
        402,
        URN + "storage-limit-reached",
        "Uploads are paused.",
        bytes_used=10**10 + 5,
        included_bytes=10**10,
        manage_url=manage,
    )
    route = api.get("/v1/organizations/O1/storage").respond(402, json=body)
    with pytest.raises(StorageLimitReachedError) as caught:
        tm.organizations.storage("O1")
    err = caught.value
    assert isinstance(err, PaymentRequiredError) and err.status == 402 and route.call_count == 1 and slept == []
    assert (err.bytes_used, err.included_bytes, err.manage_url) == (10**10 + 5, 10**10, manage)
    api.get("/v1/organizations/O2/storage").respond(402, json=problem(402))
    with pytest.raises(PaymentRequiredError) as plain:
        tm.organizations.storage("O2")
    assert type(plain.value) is PaymentRequiredError


def test_the_pending_payment_answer_is_gone() -> None:
    types = {p["type"] for p in SPEC["x-problem-types"]}
    assert URN + "organization-pending-payment" not in types
    assert URN + "organization-pending-payment" not in taskadence.errors.BY_TYPE
    assert not hasattr(taskadence, "OrganizationPendingPaymentError")


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
        ("storage-limit-reached", 402),
        ("billing-owner-must-hand-over", 409),
        ("organization-restricted", 423),
        ("organization-read-only", 423),
        ("organization-locked", 423),
    ):
        assert types[URN + slug] == [status], slug
        assert URN + slug in taskadence.errors.BY_TYPE, slug
    assert URN + "email-in-other-account" not in taskadence.errors.BY_TYPE


# ---------------------------------------------------------------------------
# not in the SDK: the contract keeps them internal, and the API refuses a token there
# ---------------------------------------------------------------------------


def test_billing_and_creating_an_organization_are_not_sdk_methods() -> None:
    ops = set(taskadence.OPERATIONS)
    assert not any(op.startswith(("support", "billing", "legal")) or "billing" in op for op in ops)
    assert "organizations.create" not in ops
    assert not any("billing" in path or "legal" in path for path in SPEC["paths"])
    assert "post" not in SPEC["paths"]["/v1/organizations"]
    tm = Taskadence(token="tkd_test_x")
    assert not hasattr(tm, "support") and not hasattr(tm, "billing")
    for name in ("billing", "billing_invoices", "billing_preflight", "billing_setup_session", "set_billing_email"):
        assert not hasattr(tm.me, name), name
    for name in ("create", "billing", "set_billing_owner", "cancel_billing_owner"):
        assert not hasattr(tm.organizations, name), name


# ---------------------------------------------------------------------------
# the legal notice: public, outside the contract, read without the token
# ---------------------------------------------------------------------------

NOTICE = {
    "effective_date": "2026-12-01",
    "terms_url": "https://taskadence.com/terms",
    "privacy_url": "https://taskadence.com/privacy",
    "headline": "Changes to our Terms and Privacy Policy, effective December 1, 2026",
}


def test_the_legal_notice_is_read_without_the_token(tm: Taskadence, api: respx.MockRouter) -> None:
    route = api.get("/v1/legal/notice").respond(json=NOTICE, headers={"Cache-Control": "public, max-age=300"})
    notice = tm.legal_notice()
    assert notice == LegalNotice(**NOTICE)
    sent = route.calls.last.request
    assert "authorization" not in {k.lower() for k in sent.headers} and sent.headers["TasKadence-Version"]
    api.get("/v1/legal/notice").respond(204)
    assert tm.legal_notice() is None


@pytest.mark.anyio
async def test_the_legal_notice_async(atm: AsyncTaskadence, api: respx.MockRouter) -> None:
    route = api.get("/v1/legal/notice").respond(json=NOTICE)
    assert (await atm.legal_notice()) == LegalNotice(**NOTICE)
    assert "authorization" not in {k.lower() for k in route.calls.last.request.headers}
    api.get("/v1/legal/notice").respond(204)
    assert (await atm.legal_notice()) is None


def test_a_legal_notice_the_sdk_does_not_know_is_a_validation_error(tm: Taskadence, api: respx.MockRouter) -> None:
    api.get("/v1/legal/notice").respond(json={"effective_date": "2026-12-01"})
    with pytest.raises(taskadence.ResponseValidationError):
        tm.legal_notice()
