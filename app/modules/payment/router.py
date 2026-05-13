"""Payment routes."""

import logging
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user
from app.core.exceptions import ApplicationError
from app.db.session import get_db
from app.modules.ip_too.model import IpToo
from app.modules.order.model import Order, OrderItem
from app.modules.payment.model import Payment
from app.modules.product.model import Product
from app.modules.user.model import User
from app.utils.kaspi import create_kaspi_payment

PaymentRouter = APIRouter(prefix="/payments", tags=["payments"])
logger = logging.getLogger(__name__)


def _payment_dict(p: Payment) -> dict[str, Any]:
    return {
        "id": p.id,
        "order_id": p.order_id,
        "provider": p.provider,
        "status": p.status,
        "provider_payment_id": p.provider_payment_id,
        "amount": p.amount,
        "created_at": p.created_at.isoformat(),
        "updated_at": p.updated_at.isoformat(),
    }


@PaymentRouter.post("/initiate")
async def initiate_payment(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Initiate payment for a placed order."""
    order_id = body.get("order_id")
    method = body.get("method", "").strip().lower()

    if not order_id or not isinstance(order_id, int):
        raise ApplicationError("'order_id' (integer) is required.")
    if method not in ("kaspi", "cash", "invoice"):
        raise ApplicationError("'method' must be 'kaspi', 'cash', or 'invoice'.")

    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_id, Order.user_id == current_user.id)
    )
    order = result.scalar_one_or_none()
    if order is None:
        raise ApplicationError("Order not found.", status_code=404)
    if order.status != "placed":
        raise ApplicationError(
            f"Order is already in status '{order.status}'. Only 'placed' orders can be paid."
        )

    if method == "invoice":
        ip_too = (
            await db.execute(
                select(IpToo).where(
                    IpToo.user_id == current_user.id,
                    IpToo.is_active == True,  # noqa: E712
                    IpToo.status == "verified",
                )
            )
        ).scalar_one_or_none()
        if ip_too is None:
            raise ApplicationError(
                "Invoice payment requires a verified IP/TOO. Bind and verify your business first."
            )

    amount_kzt = int(order.total_amount)  # total_amount is Decimal, convert for storage

    if method in ("cash", "invoice"):
        payment = Payment(
            order_id=order_id,
            provider=method,
            status="completed",
            amount=amount_kzt,
        )
        db.add(payment)
        order.status = "paid"
        await db.commit()
        await db.refresh(payment)
        return _payment_dict(payment)

    # kaspi
    kaspi_result = await create_kaspi_payment(order_id, amount_kzt)
    payment = Payment(
        order_id=order_id,
        provider="kaspi",
        status="pending",
        provider_payment_id=kaspi_result["payment_id"],
        amount=amount_kzt,
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)

    return {
        **_payment_dict(payment),
        "payment_url": kaspi_result["payment_url"],
        "payment_id": kaspi_result["payment_id"],
    }


@PaymentRouter.post("/kaspi-callback")
async def kaspi_callback(
    body: dict,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Kaspi payment webhook. In dev, accepts any payload without signature check."""
    payment_id = body.get("payment_id", "")
    status = body.get("status", "").strip().lower()

    if not payment_id or status not in ("success", "failed"):
        raise ApplicationError("Invalid callback payload.", status_code=400)

    payment = (
        await db.execute(
            select(Payment).where(Payment.provider_payment_id == payment_id)
        )
    ).scalar_one_or_none()
    if payment is None:
        raise ApplicationError("Payment not found.", status_code=404)

    order = (
        await db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.id == payment.order_id)
        )
    ).scalar_one_or_none()

    if status == "success":
        payment.status = "completed"
        if order:
            order.status = "paid"
            # Push notification (imported here to avoid circular imports at module load)
            from app.utils.push import send_push
            await send_push(
                order.user_id,
                "Order confirmed",
                f"Your order #{order.id} payment was received.",
                db,
            )

    elif status == "failed":
        payment.status = "failed"
        if order:
            order.is_cancelled = True
            # Restore stock for each item
            for item in order.items:
                if item.product_id is not None:
                    product = await db.get(Product, item.product_id)
                    if product:
                        product.stock_qty += item.qty
            from app.utils.push import send_push
            await send_push(
                order.user_id,
                "Payment failed",
                f"Payment for order #{order.id} failed. Please try again.",
                db,
            )

    await db.commit()
    return {"received": True}


@PaymentRouter.get("/orders/{order_id}")
async def get_payment_for_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return the payment record for an order belonging to the current user."""
    order = (
        await db.execute(
            select(Order).where(Order.id == order_id, Order.user_id == current_user.id)
        )
    ).scalar_one_or_none()
    if order is None:
        raise ApplicationError("Order not found.", status_code=404)

    payment = (
        await db.execute(select(Payment).where(Payment.order_id == order_id))
    ).scalar_one_or_none()
    if payment is None:
        raise ApplicationError("No payment record found for this order.", status_code=404)

    return _payment_dict(payment)
