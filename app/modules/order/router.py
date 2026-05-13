"""Order routes."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user
from app.core.exceptions import ApplicationError
from app.db.session import get_db
from app.modules.cart.model import CartItem
from app.modules.order.model import Order, OrderItem
from app.modules.order.schema import CreateOrderRequest, OrderResponse
from app.modules.product.model import Product
from app.modules.user.model import User
from app.utils.pagination import create_pagination_response

OrderRouter = APIRouter(prefix="/orders", tags=["orders"])


@OrderRouter.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    body: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Create an order from the current user's active cart."""
    now = datetime.now(UTC)

    rows = (
        await db.execute(
            select(CartItem, Product)
            .join(Product, CartItem.product_id == Product.id)
            .where(CartItem.user_id == current_user.id, CartItem.reserved_until > now)
            .with_for_update()
        )
    ).all()

    if not rows:
        raise ApplicationError("Your cart is empty or all reservations have expired.", status_code=400)

    order_items: list[OrderItem] = []
    total = 0

    for cart_item, product in rows:
        if not product.is_active:
            raise ApplicationError(f"'{product.name}' is no longer available.", status_code=409)
        if product.stock_qty < cart_item.qty:
            raise ApplicationError(
                f"Insufficient stock for '{product.name}': "
                f"{product.stock_qty} available, {cart_item.qty} requested.",
                status_code=409,
            )
        subtotal = product.price * cart_item.qty
        total += subtotal
        product.stock_qty -= cart_item.qty
        order_items.append(
            OrderItem(
                product_id=product.id,
                product_name=product.name,
                qty=cart_item.qty,
                unit_price=product.price,
                subtotal=subtotal,
            )
        )

    order = Order(
        user_id=current_user.id,
        status="pending",
        total_amount=total,
        currency="KZT",
        notes=body.notes,
    )
    db.add(order)
    await db.flush()

    for item in order_items:
        item.order_id = order.id
        db.add(item)

    await db.execute(delete(CartItem).where(CartItem.user_id == current_user.id))
    await db.commit()

    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order.id)
    )
    return OrderResponse.model_validate(result.scalar_one())


@OrderRouter.get("", response_model=dict)
async def list_orders(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List all orders for the current user, newest first."""
    from sqlalchemy import func

    base = select(Order).where(Order.user_id == current_user.id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()

    rows = (
        await db.execute(
            base.options(selectinload(Order.items))
            .order_by(Order.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
    ).scalars().all()

    items = [OrderResponse.model_validate(o) for o in rows]
    return create_pagination_response(items, page, size, total).model_dump()


@OrderRouter.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Get a single order by ID (owner only)."""
    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if order is None or order.user_id != current_user.id:
        raise ApplicationError("Order not found.", status_code=404)
    return OrderResponse.model_validate(order)
