from typing import Generic, Sequence, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: Sequence[T]
    total: int
    page: int
    size: int
    pages: int


class PaginationParams(BaseModel):
    page: int = 1
    size: int = 20
    sort_by: str = "created_at"
    sort_desc: bool = True
    search: str = ""


def paginate(query, params: PaginationParams):
    total = query.count()
    if params.sort_desc:
        query = query.order_by(
            getattr(query.column_descriptions[0]["type"], params.sort_by).desc()
        )
    else:
        query = query.order_by(
            getattr(query.column_descriptions[0]["type"], params.sort_by).asc()
        )

    items = query.offset((params.page - 1) * params.size).limit(params.size).all()
    pages = (total + params.size - 1) // params.size
    return Page(
        items=items, total=total, page=params.page, size=params.size, pages=pages
    )
