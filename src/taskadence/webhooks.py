"""Receiving Taskadence webhooks: verify the signature, then parse the event.

    from taskadence import webhooks

    def handle(request):                         # any framework: you need the headers and the RAW body bytes
        if not webhooks.verify(SECRET, request.headers, request.body):
            return 400
        event = webhooks.parse(request.body)     # a typed WebhookEvent, generated from the spec
        if event.type_ == "task.updated":
            ...
        return 200

The recipe is `taskadence-api/docs/api/WEBHOOKS_WORKFLOW.md` (Standard Webhooks): the signed message is
`"{webhook-id}.{webhook-timestamp}.{raw body}"`, the HMAC-SHA256 key is the base64-DECODED part of the secret after
`whsec_`, and `webhook-signature` holds one or more space-separated `v1,<base64>` values.

ROTATION, both ways. After "rotate secret" Taskadence signs with the old AND the new secret for 24 h (two values in the
header), so a receiver still holding the old secret keeps verifying; and a receiver may pass BOTH secrets
(`verify([new, old], …)`) while it switches over. A timestamp further than `tolerance` seconds from now is refused
(a replayed capture). Compare in constant time; verify the raw bytes — never a re-serialized JSON.

THE EVENT is the spec's `WebhookEvent` (`components.schemas.WebhookEvent`; the spec's `webhooks` map has one entry per
event type), generated like every other model: `type_` (the generator's name for `type`), `created_at` a datetime,
`actor`, `data.before` / `data.after`, and `additional_properties` keeping any field a newer API version adds.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import re
import time
from collections.abc import Mapping, Sequence
from typing import Any

from ._generated.models import WebhookActor, WebhookEvent, WebhookEventData

SECRET_PREFIX = "whsec_"  # noqa: S105 - the prefix, not a secret
DEFAULT_TOLERANCE = 300


class WebhookVerificationError(ValueError):
    """Raised by `verify(..., raise_on_failure=True)`; the message says which check failed (never the secret)."""


class WebhookParseError(ValueError):
    """Raised by `parse` when the body is not a Taskadence webhook event (not a JSON object, or a field missing)."""


# The generated models parse with `datetime.fromisoformat`, which on Python 3.10 accepts neither a `Z` suffix nor a
# fraction other than 3 or 6 digits — and Postgres trims trailing zeros (`…:13.8361+00:00`). Normalized before parsing.
_ISO_FRACTION = re.compile(r"(\.\d{1,6})\d*(?=[+-]\d{2}:\d{2}$|$)")


def _iso(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
    return _ISO_FRACTION.sub(lambda m: m.group(1).ljust(7, "0"), text, count=1)


def _header(headers: Mapping[str, str], name: str) -> str | None:
    getter = getattr(headers, "get", None)
    value = getter(name) if getter else None
    if value is None:
        value = next((v for k, v in headers.items() if k.lower() == name), None)
    return value


def _key(secret: str) -> bytes:
    try:
        return base64.b64decode(secret.removeprefix(SECRET_PREFIX), validate=True)
    except (binascii.Error, ValueError):
        raise WebhookVerificationError("the secret is not a Taskadence webhook secret (`whsec_` + base64)") from None


def sign(secret: str, msg_id: str, timestamp: int, body: bytes) -> str:
    """The `v1,<base64>` signature Taskadence sends — for tests of your own receiver."""
    digest = hmac.new(_key(secret), f"{msg_id}.{timestamp}.".encode() + body, hashlib.sha256).digest()
    return "v1," + base64.b64encode(digest).decode()


def verify(
    secret: str | Sequence[str],
    headers: Mapping[str, str],
    body: bytes | str,
    tolerance: int = DEFAULT_TOLERANCE,
    *,
    now: float | None = None,
    raise_on_failure: bool = False,
) -> bool:
    """True when `body` was signed by Taskadence with `secret` (or any of several secrets) within `tolerance` seconds.

    `headers`: the request's headers (any mapping; names are matched case-insensitively). `body`: the RAW request body.
    """

    def fail(reason: str) -> bool:
        if raise_on_failure:
            raise WebhookVerificationError(reason)
        return False

    msg_id = _header(headers, "webhook-id")
    stamp = _header(headers, "webhook-timestamp")
    signatures = _header(headers, "webhook-signature")
    if not (msg_id and stamp and signatures):
        return fail("missing webhook-id, webhook-timestamp or webhook-signature")
    try:
        timestamp = int(stamp)
    except ValueError:
        return fail("webhook-timestamp is not an integer")
    if abs((time.time() if now is None else now) - timestamp) > tolerance:
        return fail(f"webhook-timestamp is more than {tolerance} s away from now (a replay, or a skewed clock)")
    raw = body.encode() if isinstance(body, str) else bytes(body)
    secrets = [secret] if isinstance(secret, str) else list(secret)
    offered = [s for s in signatures.split(" ") if s.startswith("v1,")]
    for candidate in secrets:
        expected = sign(candidate, msg_id, timestamp, raw)
        if any(hmac.compare_digest(expected, sig) for sig in offered):
            return True
    return fail("no signature matches the secret")


def parse(body: bytes | str | Mapping[str, Any]) -> WebhookEvent:
    """The event, typed (the generated `WebhookEvent`). Parse only a body `verify` accepted."""
    try:
        data = dict(body) if isinstance(body, Mapping) else json.loads(body)
        if not isinstance(data, dict):
            raise WebhookParseError("a webhook body is a JSON object")
        return WebhookEvent.from_dict({**data, "created_at": _iso(data.get("created_at"))})
    except WebhookParseError:
        raise
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise WebhookParseError(f"not a Taskadence webhook event ({type(exc).__name__}: {exc})") from None


__all__ = [
    "DEFAULT_TOLERANCE",
    "WebhookActor",
    "WebhookEvent",
    "WebhookEventData",
    "WebhookParseError",
    "WebhookVerificationError",
    "parse",
    "sign",
    "verify",
]
