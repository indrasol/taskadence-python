"""`tm.legal_notice()`: the pending change to the Terms of Service and Privacy Policy, if any.

`GET /v1/legal/notice` is the web app's banner feed: unauthenticated and outside the public contract
(`spec/openapi.public.json`), so it is hand-written here and not generated. The API refuses every access token on a
route outside the contract, so this request is sent WITHOUT the client's token. 200 is a `LegalNotice`, 204 (no change
pending) is None.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from . import errors

PATH = "/v1/legal/notice"


@dataclass(frozen=True)
class LegalNotice:
    """The Terms / Privacy change and the day it takes effect."""

    effective_date: str
    """ISO date (`YYYY-MM-DD`) the changed Terms of Service and Privacy Policy take effect."""
    terms_url: str
    privacy_url: str
    headline: str
    """The banner's line, e.g. "Changes to our Terms and Privacy Policy, effective December 1, 2026"."""


def parse(response: httpx.Response) -> LegalNotice | None:
    if response.status_code >= 400:
        raise errors.from_response(response)
    if response.status_code == 204:
        return None
    try:
        body: Any = response.json()
        return LegalNotice(
            effective_date=str(body["effective_date"]),
            terms_url=str(body["terms_url"]),
            privacy_url=str(body["privacy_url"]),
            headline=str(body["headline"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise errors.ResponseValidationError(
            f"legal_notice: the response is not the notice this SDK knows ({exc!r})",
            operation="legal_notice",
            body=response.text,
        ) from exc
