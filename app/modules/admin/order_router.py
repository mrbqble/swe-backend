"""Admin: order management routes."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_admin
from app.core.exceptions import ApplicationError
from app.db.session import get_db
from app.modules.admin.model import AdminAction, AdminUser
from app.modules.order.model import Order, OrderItem
from app.modules.user.model import User
from app.utils.pagination import create_pagination_response

AdminOrderRouter = APIRouter(tags=["admin"])

_VALID_TRANSITIONS: dict[str, set[str]] = {
    "placed": {"paid"},
    "pending": {"paid"},  # backward-compat for old orders
    "paid": {"packed"},
    "packed": {"shipped"},
    "shipped": {"delivered"},
    "delivered": set(),
    "cancelled": set(),
}


def _can_transition(current: str, new: str) -> bool:
    if new == "cancelled":
        return current != "cancelled"
    return new in _VALID_TRANSITIONS.get(current, set())


def _order_dict(order: Order, user: User | None = None) -> dict[str, Any]:
    d: dict[str, Any] = {
        "id": order.id,
        "user_id": order.user_id,
        "status": order.status,
        "is_cancelled": order.is_cancelled,
        "total_amount": str(order.total_amount),
        "currency": order.currency,
        "notes": order.notes,
        "created_at": order.created_at.isoformat(),
        "updated_at": order.updated_at.isoformat(),
        "items": [
            {
                "id": i.id,
                "product_id": i.product_id,
                "product_name": i.product_name,
                "qty": i.qty,
                "unit_price": str(i.unit_price),
                "subtotal": str(i.subtotal),
            }
            for i in (order.items or [])
        ],
    }
    if user:
        d["user"] = {
            "id": user.id,
            "phone": user.phone,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }
    return d


@AdminOrderRouter.get("/orders")
async def list_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
    user_id: int | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List orders with filters. Includes user phone + name."""
    base = select(Order).options(selectinload(Order.items))

    if status:
        base = base.where(Order.status == status)
    if user_id is not None:
        base = base.where(Order.user_id == user_id)
    if date_from:
        try:
            base = base.where(Order.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            base = base.where(Order.created_at <= datetime.fromisoformat(date_to + "T23:59:59"))
        except ValueError:
            pass

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (
        await db.execute(
            base.order_by(Order.created_at.desc()).offset((page - 1) * limit).limit(limit)
        )
    ).scalars().all()

    # Batch-fetch users
    user_ids = list({o.user_id for o in rows})
    user_map: dict[int, User] = {}
    if user_ids:
        users = (await db.execute(select(User).where(User.id.in_(user_ids)))).scalars().all()
        user_map = {u.id: u for u in users}

    items = [_order_dict(o, user_map.get(o.user_id)) for o in rows]
    return create_pagination_response(items, page, limit, total).model_dump()


@AdminOrderRouter.patch("/orders/{order_id}/status")
async def update_order_status(
    order_id: int,
    body: dict,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update order status with transition validation."""
    new_status = body.get("status", "").strip().lower()
    if not new_status:
        raise ApplicationError("'status' field is required.")

    result = await db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise ApplicationError("Order not found.", status_code=404)

    if not _can_transition(order.status, new_status):
        raise ApplicationError(
            f"Cannot transition order from '{order.status}' to '{new_status}'."
        )

    before = {"status": order.status, "is_cancelled": order.is_cancelled}
    order.status = new_status
    if new_status == "cancelled":
        order.is_cancelled = True
    after = {"status": order.status, "is_cancelled": order.is_cancelled}

    action = AdminAction(
        admin_id=admin.id,
        action_type="update_order_status",
        target_type="order",
        target_id=order_id,
        before_data=before,
        after_data=after,
        ip=request.client.host if request.client else None,
    )
    db.add(action)
    await db.commit()
    await db.refresh(order)

    return _order_dict(order)
