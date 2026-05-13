"""Cart reservation routes."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.exceptions import ApplicationError
from app.db.session import get_db
from app.modules.cart.model import CartItem
from app.modules.cart.schema import (
    AddToCartRequest,
    CartItemResponse,
    CartResponse,
    UpdateCartRequest,
)
from app.modules.product.model import Product
from app.modules.user.model import User

CartRouter = APIRouter(prefix="/cart", tags=["cart"])


def _reservation_until() -> datetime:
    return datetime.now(UTC) + timedelta(minutes=settings.CART_RESERVATION_MINUTES)


async def _available_qty(product: Product, exclude_user_id: int, db: AsyncSession) -> int:
    now = datetime.now(UTC)
    from sqlalchemy import func

    result = await db.execute(
        select(func.coalesce(func.sum(CartItem.qty), 0)).where(
            CartItem.product_id == product.id,
            CartItem.reserved_until > now,
            CartItem.user_id != exclude_user_id,
        )
    )
    others_reserved: int = result.scalar_one()
    return max(0, product.stock_qty - others_reserved)


async def _build_cart_response(user_id: int, db: AsyncSession) -> CartResponse:
    now = datetime.now(UTC)
    rows = (
        await db.execute(
            select(CartItem, Product)
            .join(Product, CartItem.product_id == Product.id)
            .where(CartItem.user_id == user_id, CartItem.reserved_until > now)
            .order_by(CartItem.created_at)
        )
    ).all()

    items: list[CartItemResponse] = []
    currency = "KZT"
    for cart_item, product in rows:
        avail = await _available_qty(product, user_id, db)
        subtotal = product.price * cart_item.qty
        currency = product.currency
        items.append(
            CartItemResponse(
                product_id=product.id,
                product_name=product.name,
                product_sku=product.sku,
                unit_price=product.price,
                currency=product.currency,
                qty=cart_item.qty,
                subtotal=subtotal,
                reserved_until=cart_item.reserved_until,
                available_qty=avail,
            )
        )

    total = sum(i.subtotal for i in items) if items else Decimal("0")
    return CartResponse(items=items, total=total, currency=currency, item_count=len(items))


@CartRouter.get("", response_model=CartResponse)
async def get_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CartResponse:
    """Return active cart items for the current user."""
    await db.execute(
        delete(CartItem).where(
            CartItem.user_id == current_user.id,
            CartItem.reserved_until <= datetime.now(UTC),
        )
    )
    await db.commit()
    return await _build_cart_response(current_user.id, db)


@CartRouter.post("", response_model=CartResponse, status_code=status.HTTP_200_OK)
async def add_to_cart(
    body: AddToCartRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CartResponse:
    """Add a product to cart or refresh + update qty if already present."""
    product = await db.get(Product, body.product_id)
    if product is None or not product.is_active:
        raise ApplicationError("Product not found.", status_code=404)

    if body.qty < product.min_order_qty:
        raise ApplicationError(
            f"Minimum order quantity is {product.min_order_qty}.", status_code=400
        )

    avail = await _available_qty(product, current_user.id, db)
    if body.qty > avail:
        raise ApplicationError(
            f"Only {avail} unit(s) available.", status_code=409
        )

    result = await db.execute(
        select(CartItem).where(
            CartItem.user_id == current_user.id,
            CartItem.product_id == body.product_id,
        )
    )
    cart_item = result.scalar_one_or_none()

    if cart_item:
        cart_item.qty = body.qty
        cart_item.reserved_until = _reservation_until()
    else:
        cart_item = CartItem(
            user_id=current_user.id,
            product_id=body.product_id,
            qty=body.qty,
            reserved_until=_reservation_until(),
        )
        db.add(cart_item)

    await db.commit()
    return await _build_cart_response(current_user.id, db)


@CartRouter.patch("/{product_id}", response_model=CartResponse)
async def update_cart_item(
    product_id: int,
    body: UpdateCartRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CartResponse:
    """Update quantity of an existing cart item."""
    result = await db.execute(
        select(CartItem).where(
            CartItem.user_id == current_user.id,
            CartItem.product_id == product_id,
        )
    )
    cart_item = result.scalar_one_or_none()
    if cart_item is None:
        raise ApplicationError("Item not in cart.", status_code=404)

    product = await db.get(Product, product_id)
    if product is None or not product.is_active:
        raise ApplicationError("Product not found.", status_code=404)

    if body.qty < product.min_order_qty:
        raise ApplicationError(
            f"Minimum order quantity is {product.min_order_qty}.", status_code=400
        )

    avail = await _available_qty(product, current_user.id, db)
    if body.qty > avail:
        raise ApplicationError(f"Only {avail} unit(s) available.", status_code=409)

    cart_item.qty = body.qty
    cart_item.reserved_until = _reservation_until()
    await db.commit()
    return await _build_cart_response(current_user.id, db)


@CartRouter.delete("/{product_id}", response_model=CartResponse)
async def remove_cart_item(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CartResponse:
    """Remove a single item from cart."""
    await db.execute(
        delete(CartItem).where(
            CartItem.user_id == current_user.id,
            CartItem.product_id == product_id,
        )
    )
    await db.commit()
    return await _build_cart_response(current_user.id, db)


@CartRouter.delete("", response_model=CartResponse)
async def clear_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CartResponse:
    """Remove all items from cart."""
    await db.execute(delete(CartItem).where(CartItem.user_id == current_user.id))
    await db.commit()
    return CartResponse(items=[], total=Decimal("0"), currency="KZT", item_count=0)
