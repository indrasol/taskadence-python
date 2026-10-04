"""Every model of the public API — the generated `attrs` classes (and `Literal` enums), re-exported.

    from taskadence.models import TaskCreate, TaskUpdate, TaskInDB, TaskCardView

Each model has `to_dict()` (the wire form) and `from_dict()`; fields the caller did not set are `UNSET` and are left
out of `to_dict()` — which is what a PATCH (JSON merge-patch) needs. A model read by a single GET also carries
`.etag`, for `if_match=` / `if_none_match=`.
"""

from ._generated import models as _generated_models
from ._generated.models import *  # noqa: F403
from ._generated.types import UNSET, Unset

__all__ = [*_generated_models.__all__, "UNSET", "Unset"]
