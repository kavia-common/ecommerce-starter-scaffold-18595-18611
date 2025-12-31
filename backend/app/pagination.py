from __future__ import annotations

from math import ceil

from flask import request


# PUBLIC_INTERFACE
def get_pagination_params(default_page: int = 1, default_page_size: int = 12, max_page_size: int = 100):
    """Get pagination params from query string.

    Query params:
      - page: int (1-based)
      - page_size: int

    Returns:
        tuple[int, int]: (page, page_size)
    """
    try:
        page = int(request.args.get("page", default_page))
    except ValueError:
        page = default_page
    try:
        page_size = int(request.args.get("page_size", default_page_size))
    except ValueError:
        page_size = default_page_size

    page = max(1, page)
    page_size = max(1, min(max_page_size, page_size))
    return page, page_size


# PUBLIC_INTERFACE
def build_pagination_metadata(total: int, page: int, page_size: int) -> dict:
    """Build pagination metadata similar to the scaffold's OpenAPI schema."""
    total_pages = max(1, ceil(total / page_size)) if total else 1
    prev_page = page - 1 if page > 1 else None
    next_page = page + 1 if page < total_pages else None
    return {
        "total": total,
        "total_pages": total_pages,
        "first_page": 1,
        "last_page": total_pages,
        "page": page,
        "previous_page": prev_page,
        "next_page": next_page,
    }
