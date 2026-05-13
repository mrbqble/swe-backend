"""Product catalog routes."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.exceptions import ApplicationError
from app.db.session import get_db
from app.modules.cart.model import CartItem
from app.modules.product.model import Product
from app.modules.product.schema import ProductResponse
from app.modules.user.model import User
from app.utils.pagination import create_pagination_response

ProductRouter = APIRouter(prefix="/products", tags=["products"])


async def _available_qty(product_id: int, db: AsyncSession) -> int:
    """Return stock_qty minus all active (non-expired) cart reservations."""
    now = datetime.now(UTC)
    result = await db.execute(
        select(func.coalesce(func.sum(CartItem.qty), 0)).where(
            CartItem.product_id == product_id,
            CartItem.reserved_until > now,
        )
    )
    reserved: int = result.scalar_one()
    prod = await db.get(Product, product_id)
    if prod is None:
        return 0
    return max(0, prod.stock_qty - reserved)


def _to_response(product: Product, avail: int) -> ProductResponse:
    data = {c.key: getattr(product, c.key) for c in Product.__table__.columns}
    data["available_qty"] = avail
    return ProductResponse.model_validate(data)


@ProductRouter.get("", response_model=dict)
async def list_products(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None, description="Search by name or SKU"),
    category: str | None = Query(None),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List active products with optional search and filters."""
    base = select(Product).where(Product.is_active == True)  # noqa: E712

    if q:
        like = f"%{q}%"
        base = base.where((Product.name.ilike(like)) | (Product.sku.ilike(like)))
    if category:
        base = base.where(Product.category == category)
    if min_price is not None:
        base = base.where(Product.price >= min_price)
    if max_price is not None:
        base = base.where(Product.price <= max_price)

    total_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(total_q)).scalar_one()

    rows = (await db.execute(base.order_by(Product.name).offset((page - 1) * size).limit(size))).scalars().all()

    now = datetime.now(UTC)
    reserved_map: dict[int, int] = {}
    if rows:
        res = await db.execute(
            select(CartItem.product_id, func.coalesce(func.sum(CartItem.qty), 0))
            .where(CartItem.product_id.in_([p.id for p in rows]), CartItem.reserved_until > now)
            .group_by(CartItem.product_id)
        )
        reserved_map = {pid: qty for pid, qty in res.all()}

    items = [_to_response(p, max(0, p.stock_qty - reserved_map.get(p.id, 0))) for p in rows]
    return create_pagination_response(items, page, size, total).model_dump()


@ProductRouter.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Get a single product by ID."""
    product = await db.get(Product, product_id)
    if product is None or not product.is_active:
        raise ApplicationError("Product not found.", status_code=404)
    avail = await _available_qty(product_id, db)
    return _to_response(product, avail)
