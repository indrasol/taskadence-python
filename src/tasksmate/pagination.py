"""Pages of a list operation (`{data, next_cursor}`), iterable across every page.

    page = tm.tasks.list(org_id="O0020", filter={"status": ["in_progress"]}, limit=100)
    page.data            # this page's items (typed models)
    page.next_cursor     # None on the last page
    for task in page:    # EVERY item, following next_cursor until it is None
        ...
    page.to_dataframe()  # every item of every page, as a pandas DataFrame (the `pandas` extra)

The API's grammar allows a page to be short — even empty — while `next_cursor` is still set; iteration keeps
following the cursor until it is None, never stopping on a short page.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    import pandas as pd

T = TypeVar("T")


class Page(Generic[T]):
    """One page of a list, and the way to the next."""

    def __init__(
        self,
        data: list[T],
        next_cursor: str | None,
        *,
        envelope: Any = None,
        etag: str | None = None,
        fetch_next: Callable[[str], Page[T]] | None = None,
    ) -> None:
        self.data = data
        self.next_cursor = next_cursor
        self.envelope = envelope  # the generated envelope model (e.g. `ProjectGoalsOut` carries its sums too)
        self.etag = etag
        self._fetch_next = fetch_next

    @property
    def has_more(self) -> bool:
        return self.next_cursor is not None

    def next_page(self) -> Page[T] | None:
        """The next page, or None on the last one."""
        if self.next_cursor is None or self._fetch_next is None:
            return None
        return self._fetch_next(self.next_cursor)

    def pages(self) -> Iterator[Page[T]]:
        """This page and every page after it."""
        page: Page[T] | None = self
        while page is not None:
            yield page
            page = page.next_page()

    def auto_paging(self) -> Iterator[T]:
        """Every item of this page and the pages after it."""
        for page in self.pages():
            yield from page.data

    def __iter__(self) -> Iterator[T]:
        return self.auto_paging()

    def to_dataframe(self, *, all_pages: bool = True) -> pd.DataFrame:
        """The items as a DataFrame (flattening: `tasksmate.dataframe`). `all_pages=False`: this page only."""
        from .dataframe import to_dataframe

        return to_dataframe(list(self.auto_paging()) if all_pages else self.data)

    def __repr__(self) -> str:
        return f"<Page of {len(self.data)} items, next_cursor={'…' if self.next_cursor else None}>"


class AsyncPage(Generic[T]):
    """`Page` for `AsyncTasksMate`: `async for item in page`, `await page.next_page()`."""

    def __init__(
        self,
        data: list[T],
        next_cursor: str | None,
        *,
        envelope: Any = None,
        etag: str | None = None,
        fetch_next: Callable[[str], Awaitable[AsyncPage[T]]] | None = None,
    ) -> None:
        self.data = data
        self.next_cursor = next_cursor
        self.envelope = envelope
        self.etag = etag
        self._fetch_next = fetch_next

    @property
    def has_more(self) -> bool:
        return self.next_cursor is not None

    async def next_page(self) -> AsyncPage[T] | None:
        if self.next_cursor is None or self._fetch_next is None:
            return None
        return await self._fetch_next(self.next_cursor)

    async def pages(self) -> AsyncIterator[AsyncPage[T]]:
        page: AsyncPage[T] | None = self
        while page is not None:
            yield page
            page = await page.next_page()

    async def auto_paging(self) -> AsyncIterator[T]:
        async for page in self.pages():
            for item in page.data:
                yield item

    def __aiter__(self) -> AsyncIterator[T]:
        return self.auto_paging()

    async def to_dataframe(self, *, all_pages: bool = True) -> pd.DataFrame:
        from .dataframe import to_dataframe

        items = [item async for item in self.auto_paging()] if all_pages else self.data
        return to_dataframe(items)

    def __repr__(self) -> str:
        return f"<AsyncPage of {len(self.data)} items, next_cursor={'…' if self.next_cursor else None}>"
