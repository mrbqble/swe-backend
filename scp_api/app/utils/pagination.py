from math import ceil
from typing import Sequence, TypeVar

T = TypeVar("T")


def paginate(items: Sequence[T], limit: int, offset: int) -> dict[str, object]:
    total = len(items)
    limit = max(limit, 1)
    page_items = items[offset : offset + limit]
    return {
        "count": total,
        "pages": ceil(total / limit) if total else 0,
        "results": list(page_items),
    }
