"""`Taskadence` and `AsyncTaskadence`: configuration, the resource namespaces, lifetime."""

from __future__ import annotations

from collections.abc import Mapping
from types import TracebackType

import httpx

from ._core import AsyncCore, SyncCore
from ._generated import models
from ._operations import API_VERSION, DEFAULT_BASE_URL
from .resources import AsyncResources, SyncResources

DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_MAX_RETRY_AFTER = 60.0


class Taskadence(SyncResources):
    """The TasKadence API.

        from taskadence import Taskadence

        tm = Taskadence()                                  # token from TASKADENCE_TOKEN
        for task in tm.tasks.list(org_id="O0020", filter={"status": ["in_progress"]}):
            print(task.task_id, task.title)

    `token`: a TasKadence access token (`tkd_live_…`; a pre-rename `tm_live_…` works too), else `TASKADENCE_TOKEN`.
    `base_url`: else `TASKADENCE_API_URL`, else the spec's first server (`taskadence.DEFAULT_BASE_URL`); a trailing
    `/v1` is accepted. Safe requests are retried `max_retries` times (see `taskadence._core`); a `Retry-After` over
    `max_retry_after` seconds is not waited out.
    `api_version` is sent as `Taskadence-Version` (default: the API date this SDK was generated from).
    """

    def __init__(
        self,
        token: str | None = None,
        base_url: str | None = None,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        api_version: str | None = None,
        max_retry_after: float = DEFAULT_MAX_RETRY_AFTER,
        headers: Mapping[str, str] | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._core = SyncCore(
            token,
            base_url,
            timeout=timeout,
            max_retries=max_retries,
            api_version=api_version,
            default_base_url=DEFAULT_BASE_URL,
            spec_version=API_VERSION,
            max_retry_after=max_retry_after,
            headers=headers,
            http_client=http_client,
        )
        self._attach(self._core)

    @property
    def base_url(self) -> str:
        return self._core.base_url

    @property
    def api_version(self) -> str:
        return self._core.api_version

    def close(self) -> None:
        """Close the HTTP connection pool (not an `http_client` you passed in)."""
        self._core.close()

    def __enter__(self) -> Taskadence:
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"Taskadence(base_url={self.base_url!r})"


class AsyncTaskadence(AsyncResources):
    """`Taskadence` for asyncio: the same namespaces and methods, awaited; lists are `AsyncPage`s (`async for`).

    async with AsyncTaskadence() as tm:
        me = await tm.me()
        async for task in await tm.tasks.list(org_id=me.organizations[0].org_id):
            ...
    """

    def __init__(
        self,
        token: str | None = None,
        base_url: str | None = None,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        api_version: str | None = None,
        max_retry_after: float = DEFAULT_MAX_RETRY_AFTER,
        headers: Mapping[str, str] | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._core = AsyncCore(
            token,
            base_url,
            timeout=timeout,
            max_retries=max_retries,
            api_version=api_version,
            default_base_url=DEFAULT_BASE_URL,
            spec_version=API_VERSION,
            max_retry_after=max_retry_after,
            headers=headers,
            http_client=http_client,
        )
        self._attach(self._core)

    @property
    def base_url(self) -> str:
        return self._core.base_url

    @property
    def api_version(self) -> str:
        return self._core.api_version

    async def close(self) -> None:
        await self._core.aclose()

    async def __aenter__(self) -> AsyncTaskadence:
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        await self.close()

    def __repr__(self) -> str:
        return f"AsyncTaskadence(base_url={self.base_url!r})"


__all__ = ["AsyncTaskadence", "Taskadence", "models"]
