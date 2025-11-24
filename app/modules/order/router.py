"""Order management routes."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.api.dependencies import get_current_user
from app.core.constants import ErrorMessages
from app.core.roles import Role
from app.db.session import get_db
from app.modules.consumer.model import Consumer
from app.modules.link.model import Link, LinkStatus
from app.modules.order.model import Order, OrderItem, OrderStatus
from app.modules.order.schema import OrderCreate, OrderResponse, OrderStatusUpdate
from app.modules.product.model import Product
from app.modules.supplier.model import Supplier, SupplierStaff
from app.modules.user.model import User
from app.utils.helpers import (
    get_consumer_by_user_id,
    get_supplier_by_user_id,
    is_supplier_owner_or_manager,
)
from app.utils.pagination import create_pagination_response

OrderRouter = APIRouter(prefix="/orders", tags=["orders"])


def _validate_status_transition(
    current_status: OrderStatus, new_status: OrderStatus
) -> None:
    """Validate state machine transitions for order status."""
    valid_transitions = {
        OrderStatus.PENDING: {OrderStatus.ACCEPTED, OrderStatus.REJECTED},
        OrderStatus.ACCEPTED: {OrderStatus.IN_PROGRESS},
        OrderStatus.IN_PROGRESS: {OrderStatus.COMPLETED},
        OrderStatus.REJECTED: set[Any](),  # Rejected orders cannot be changed
        OrderStatus.COMPLETED: set[Any](),  # Completed orders cannot be changed
    }

    allowed = valid_transitions.get(current_status, set[OrderStatus]())
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from {current_status.value} to {new_status.value}",
        )


@OrderRouter.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Create an order (consumer only)."""
    # Check user is consumer
    if current_user.role != Role.CONSUMER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ErrorMessages.NOT_ENOUGH_PERMISSIONS,
        )

    # Get consumer
    consumer = await get_consumer_by_user_id(current_user.id, db)
    if not consumer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consumer profile not found",
        )

    # Check if supplier exists
    result = await db.execute(
        select(Supplier).where(Supplier.id == order_data.supplier_id)
    )
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found",
        )

    # Check if link exists and is accepted
    result = await db.execute(
        select(Link).where(
            Link.consumer_id == consumer.id,
            Link.supplier_id == order_data.supplier_id,
            Link.status == LinkStatus.ACCEPTED,
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have an accepted link with this supplier",
        )

    # Validate items and calculate total
    total = 0
    order_items: list[OrderItem] = []

    for item_data in order_data.items:
        # Validate quantity
        if item_data.qty <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Quantity must be positive for product {item_data.product_id}",
            )

        # Get product
        result = await db.execute(
            select(Product).where(Product.id == item_data.product_id)
        )
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {item_data.product_id} not found",
            )

        # Check product belongs to supplier
        if product.supplier_id != order_data.supplier_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product {item_data.product_id} does not belong to supplier {order_data.supplier_id}",
            )

        # Check product is active
        if not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product {item_data.product_id} is not active",
            )

        # Calculate item total
        item_total = product.price_kzt * item_data.qty
        total += item_total

        # Create order item
        order_item = OrderItem(
            product_id=item_data.product_id,
            qty=item_data.qty,
            unit_price_kzt=product.price_kzt,
        )
        order_items.append(order_item)

    # Create order
    order = Order(
        supplier_id=order_data.supplier_id,
        consumer_id=consumer.id,
        status=OrderStatus.PENDING,
        total_kzt=total,
    )
    db.add(order)
    await db.flush()  # Flush to get order.id

    # Set order_id for items
    for item in order_items:
        item.order_id = order.id
        db.add(item)

    await db.commit()
    await db.refresh(order)

    # Load items, supplier, and consumer for response
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.items),
            joinedload(Order.supplier).joinedload(Supplier.user),
            joinedload(Order.consumer).joinedload(Consumer.user),
        )
        .where(Order.id == order.id)
    )
    order = result.scalar_one()

    return OrderResponse.model_validate(order)


@OrderRouter.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Get a single order (consumer or supplier staff)."""
    # Get order with items, supplier, and consumer
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.items),
            joinedload(Order.supplier).joinedload(Supplier.user),
            joinedload(Order.consumer).joinedload(Consumer.user),
        )
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Check access: consumer can see their own orders
    if current_user.role == Role.CONSUMER.value:
        consumer = await get_consumer_by_user_id(current_user.id, db)
        if consumer and order.consumer_id == consumer.id:
            return OrderResponse.model_validate(order)

    # Check access: supplier owner/manager can see their supplier's orders
    if current_user.role in (
        Role.SUPPLIER_OWNER.value,
        Role.SUPPLIER_MANAGER.value,
    ):
        has_permission = await is_supplier_owner_or_manager(
            current_user, order.supplier_id, db
        )
        if has_permission:
            return OrderResponse.model_validate(order)

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to view this order",
    )


@OrderRouter.get("", response_model=dict)  # Will be PaginationResponse[OrderResponse]
async def get_orders(
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    status_filter: OrderStatus | None = Query(
        None, description="Filter by status", alias="status"
    ),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get orders (consumer: own orders, supplier staff: their supplier's orders)."""
    query = select(Order).options(
        selectinload(Order.items),
        joinedload(Order.supplier).joinedload(Supplier.user),
        joinedload(Order.consumer).joinedload(Consumer.user),
    )
    consumer_id: int | None = None
    supplier_id: int | None = None

    # Consumer: get their own orders
    if current_user.role == Role.CONSUMER.value:
        consumer = await get_consumer_by_user_id(current_user.id, db)
        if not consumer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Consumer profile not found",
            )
        consumer_id = consumer.id
        query = query.where(Order.consumer_id == consumer_id)

    # Supplier staff (owner/manager/sales): get their supplier's orders
    elif current_user.role in (
        Role.SUPPLIER_OWNER.value,
        Role.SUPPLIER_MANAGER.value,
        Role.SUPPLIER_SALES.value,
    ):
        supplier = await get_supplier_by_user_id(current_user.id, db)
        if not supplier:
            # Check if user is staff (owner/manager/sales) via SupplierStaff
            result = await db.execute(
                select(SupplierStaff).where(
                    SupplierStaff.user_id == current_user.id,
                    SupplierStaff.staff_role.in_(["manager", "owner", "sales"]),
                )
            )
            staff = result.scalar_one_or_none()
            if not staff:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Supplier profile not found",
                )
            supplier_id = staff.supplier_id
        else:
            supplier_id = supplier.id

        query = query.where(Order.supplier_id == supplier_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ErrorMessages.NOT_ENOUGH_PERMISSIONS,
        )

    # Apply status filter
    if status_filter:
        query = query.where(Order.status == status_filter)

    # Get total count
    count_query = select(func.count(Order.id))
    if consumer_id is not None:
        count_query = count_query.where(Order.consumer_id == consumer_id)
    elif supplier_id is not None:
        count_query = count_query.where(Order.supplier_id == supplier_id)
    if status_filter:
        count_query = count_query.where(Order.status == status_filter)

    count_result = await db.execute(count_query)
    total = count_result.scalar_one() or 0

    # Get paginated results
    query = (
        query.order_by(Order.created_at.desc()).offset((page - 1) * size).limit(size)
    )
    result = await db.execute(query)
    orders = result.scalars().all()

    # Create response
    order_responses = [OrderResponse.model_validate(order) for order in orders]
    return create_pagination_response(order_responses, page, size, total).model_dump()


@OrderRouter.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    status_update: OrderStatusUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """Update order status (supplier owner/manager only)."""
    # Check user is supplier owner or manager
    if current_user.role not in (
        Role.SUPPLIER_OWNER.value,
        Role.SUPPLIER_MANAGER.value,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ErrorMessages.NOT_ENOUGH_PERMISSIONS,
        )

    # Get order with items and products (for stock updates)
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    # Check user has permission for this supplier
    has_permission = await is_supplier_owner_or_manager(
        current_user, order.supplier_id, db
    )
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage this supplier's orders",
        )

    # Validate state transition
    _validate_status_transition(order.status, status_update.status)

    # Handle stock updates on accept/reject
    if status_update.status == OrderStatus.ACCEPTED:
        # Decrease stock when order is accepted
        for item in order.items:
            result = await db.execute(
                select(Product).where(Product.id == item.product_id)
            )
            product = result.scalar_one_or_none()
            if product:
                if product.stock_qty < item.qty:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Insufficient stock for product {product.name}. Available: {product.stock_qty}, Required: {item.qty}",
                    )
                product.stock_qty -= item.qty
    elif (
        status_update.status == OrderStatus.REJECTED
        and order.status == OrderStatus.ACCEPTED
    ):
        # Restore stock if rejecting an already accepted order
        for item in order.items:
            result = await db.execute(
                select(Product).where(Product.id == item.product_id)
            )
            product = result.scalar_one_or_none()
            if product:
                product.stock_qty += item.qty

    # Update status
    order.status = status_update.status
    await db.commit()
    await db.refresh(order)

    # Reload with items, supplier, and consumer
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.items),
            joinedload(Order.supplier).joinedload(Supplier.user),
            joinedload(Order.consumer).joinedload(Consumer.user),
        )
        .where(Order.id == order.id)
    )
    order = result.scalar_one()

    return OrderResponse.model_validate(order)
