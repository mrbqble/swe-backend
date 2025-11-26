"""Order management routes."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.api.dependencies import get_current_user
from app.core.exceptions import ApplicationError
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
    assign_sales_representative,
    create_notification,
    get_consumer_by_user_id,
    get_supplier_id_for_user,
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
        # Completed orders cannot be changed
        OrderStatus.COMPLETED: set[Any](),
    }

    allowed = valid_transitions.get(current_status, set[OrderStatus]())
    if new_status not in allowed:
        raise ApplicationError(f"Cannot transition from {current_status.value} to {new_status.value}",
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
        raise ApplicationError("Not enough permissions",
                               )

    # Get consumer
    consumer = await get_consumer_by_user_id(current_user.id, db)
    if not consumer:
        raise ApplicationError("Consumer profile not found",
                               )

    # Check if supplier exists
    result = await db.execute(
        select(Supplier).where(Supplier.id == order_data.supplier_id)
    )
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise ApplicationError("Supplier not found",
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
        raise ApplicationError("You do not have an accepted link with this supplier",
                               )

    # Validate items and calculate total
    total = 0
    order_items: list[OrderItem] = []
    products_info: list[dict] = []  # Store product info for chat message

    for item_data in order_data.items:
        # Validate quantity
        if item_data.qty <= 0:
            raise ApplicationError(
                f"Quantity must be positive for product {item_data.product_id}")

        # Get product
        result = await db.execute(
            select(Product).where(Product.id == item_data.product_id)
        )
        product = result.scalar_one_or_none()
        if not product:
            raise ApplicationError(f"Product {item_data.product_id} not found")

        # Check product belongs to supplier
        if product.supplier_id != order_data.supplier_id:
            raise ApplicationError(
                f"Product {item_data.product_id} does not belong to supplier {order_data.supplier_id}")

        # Check product is active
        if not product.is_active:
            raise ApplicationError(
                f"Product {item_data.product_id} is not active")

        # Calculate item total
        item_total = product.price_kzt * item_data.qty
        total += item_total

        # Store product info for chat message
        products_info.append({
            "name": product.name,
            "qty": item_data.qty
        })

        # Create order item
        order_item = OrderItem(
            product_id=item_data.product_id,
            qty=item_data.qty,
            unit_price_kzt=product.price_kzt,
        )
        order_items.append(order_item)

    # Assign sales representative automatically
    # Check if consumer is already assigned to a sales rep for this supplier (via ChatSession)
    # There should be exactly one chat session per consumer-supplier pair (1-to-1 relationship)
    from app.modules.chat.model import ChatSession
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.consumer_id == consumer.id,
            ChatSession.supplier_id == order_data.supplier_id,
        )
    )
    existing_chat_session = result.scalar_one_or_none()

    if existing_chat_session:
        # Use the sales rep already assigned to this consumer for this supplier
        sales_rep_id = existing_chat_session.sales_rep_id
    else:
        # No existing assignment - this should not happen if link is accepted
        # But handle gracefully: assign a new sales rep (counts ChatSessions for even distribution)
        sales_rep_id = await assign_sales_representative(order_data.supplier_id, db)

    # Create order
    order = Order(
        supplier_id=order_data.supplier_id,
        consumer_id=consumer.id,
        sales_rep_id=sales_rep_id,
        status=OrderStatus.PENDING,
        total_kzt=total,
    )
    db.add(order)
    await db.flush()  # Flush to get order.id

    # Set order_id for items
    for item in order_items:
        item.order_id = order.id
        db.add(item)

    # Post system message in the chat thread about the order
    # Do this before committing so we can rollback everything if chat session creation fails
    # Find or create the chat session for this consumer-supplier pair
    # According to SRS: orders are posted in the same 1-1 chat thread
    from app.modules.chat.model import ChatSession, ChatMessage
    from datetime import UTC, datetime

    # Verify there's an accepted link between consumer and supplier
    result = await db.execute(
        select(Link).where(
            Link.consumer_id == consumer.id,
            Link.supplier_id == order.supplier_id,
            Link.status == LinkStatus.ACCEPTED,
        )
    )
    link = result.scalar_one_or_none()

    if link:
        # Use the chat session we already found earlier, or find/create it
        # Re-check in case it was created between the earlier check and now
        if not existing_chat_session:
            result = await db.execute(
                select(ChatSession).where(
                    ChatSession.consumer_id == consumer.id,
                    ChatSession.supplier_id == order.supplier_id,
                )
            )
            existing_chat_session = result.scalar_one_or_none()

        if not existing_chat_session:
            # Create chat session if it doesn't exist (should exist from link acceptance, but create as fallback)
            # Handle potential race condition: session might be created by another request
            try:
                chat_session = ChatSession(
                    consumer_id=consumer.id,
                    supplier_id=order.supplier_id,
                    sales_rep_id=sales_rep_id,
                    created_at=datetime.now(UTC),
                )
                db.add(chat_session)
                await db.flush()  # Flush to get session.id
                existing_chat_session = chat_session
            except IntegrityError:
                # Session was created by another request (unique constraint violation)
                # Rollback only the flush (order is not committed yet)
                await db.rollback()
                # Fetch the existing session
                result = await db.execute(
                    select(ChatSession).where(
                        ChatSession.consumer_id == consumer.id,
                        ChatSession.supplier_id == order.supplier_id,
                    )
                )
                existing_chat_session = result.scalar_one_or_none()
                if not existing_chat_session:
                    # If still not found, something else went wrong
                    raise ApplicationError("Failed to create or find chat session")

        # Post structured order message in the chat thread
        # Format: Clear order notification with order details
        items_summary = ", ".join([f"{info['qty']}x {info['name']}" for info in products_info[:3]])
        if len(products_info) > 3:
            items_summary += f" and {len(products_info) - 3} more item(s)"

        order_message_text = (
            f"📦 Order #{order.id} created\n\n"
            f"Items: {items_summary}\n"
            f"Total: {total:.2f} KZT\n"
            f"Status: Pending approval"
        )

        order_message = ChatMessage(
            session_id=existing_chat_session.id,
            sender_id=consumer.user_id,  # Consumer who created the order
            text=order_message_text,
            created_at=datetime.now(UTC),
        )
        db.add(order_message)

    # Create notification for consumer when order is created
    if consumer.user_id:
        supplier_result = await db.execute(
            select(Supplier).where(Supplier.id == order.supplier_id)
        )
        supplier = supplier_result.scalar_one_or_none()
        supplier_name = supplier.company_name if supplier and supplier.company_name else "Supplier"
        message = f"Your order #{order.id} has been created and is pending approval from {supplier_name}."
        await create_notification(consumer.user_id, "order_created", message, db, entity_id=order.id, entity_type="order")

    # Commit everything together (order, items, chat message, notification)
        await db.commit()
    await db.refresh(order)

    # Load items, supplier, consumer, and sales_rep for response
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.items),
            joinedload(Order.supplier).joinedload(Supplier.user),
            joinedload(Order.consumer).joinedload(Consumer.user),
            joinedload(Order.sales_rep),
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
    """Get a single order (consumer or supplier staff).

    For consumers: Only allows access to orders where order.consumer_id matches
    the current user's consumer_id (not by organization).
    """
    # Get order with items, supplier, consumer, and sales_rep
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.items),
            joinedload(Order.supplier).joinedload(Supplier.user),
            joinedload(Order.consumer).joinedload(Consumer.user),
            joinedload(Order.sales_rep),
        )
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise ApplicationError("Order not found",
                               )

    # Check access: consumer can only see their own orders (by consumer_id, not organization)
    # This ensures that multiple consumers from the same organization cannot see each other's orders
    if current_user.role == Role.CONSUMER.value:
        consumer = await get_consumer_by_user_id(current_user.id, db)
        if not consumer:
            raise ApplicationError("Consumer profile not found")
        # Verify the order belongs to this specific consumer (not just same organization)
        if order.consumer_id == consumer.id:
            return OrderResponse.model_validate(order)
        else:
            raise ApplicationError(
                "You do not have permission to view this order")

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

    # Check access: sales rep can only see orders assigned to them
    if current_user.role == Role.SUPPLIER_SALES.value:
        if order.sales_rep_id == current_user.id:
            return OrderResponse.model_validate(order)

    raise ApplicationError("You do not have permission to view this order")


# Will be PaginationResponse[OrderResponse]
@OrderRouter.get("", response_model=dict)
async def get_orders(
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    status_filter: OrderStatus | None = Query(
        None, description="Filter by status", alias="status"
    ),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get orders (consumer: own orders only, supplier staff: their supplier's orders).

    For consumers: Filters by the specific consumer_id (not by organization).
    Multiple consumers from the same organization will only see their own orders.
    """
    query = select(Order).options(
        selectinload(Order.items),
        joinedload(Order.supplier).joinedload(Supplier.user),
        joinedload(Order.consumer).joinedload(Consumer.user),
        joinedload(Order.sales_rep),
    )
    consumer_id: int | None = None
    supplier_id: int | None = None

    # Consumer: get only their own orders (filtered by specific consumer_id, not organization)
    # This ensures that multiple consumers from the same organization only see their own orders
    if current_user.role == Role.CONSUMER.value:
        consumer = await get_consumer_by_user_id(current_user.id, db)
        if not consumer:
            raise ApplicationError("Consumer profile not found")
        consumer_id = consumer.id
        # Filter by the specific consumer's ID, not by organization
        query = query.where(Order.consumer_id == consumer_id)

    # Supplier staff (owner/manager/sales): get their supplier's orders
    elif current_user.role in (
        Role.SUPPLIER_OWNER.value,
        Role.SUPPLIER_MANAGER.value,
        Role.SUPPLIER_SALES.value,
    ):
        supplier_id = await get_supplier_id_for_user(current_user, db)
        if not supplier_id:
            raise ApplicationError("Supplier profile not found")
        query = query.where(Order.supplier_id == supplier_id)

        # Sales reps can only see orders assigned to them
        if current_user.role == Role.SUPPLIER_SALES.value:
            query = query.where(Order.sales_rep_id == current_user.id)
    else:
        raise ApplicationError("Not enough permissions",
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
        # Sales reps can only see orders assigned to them
        if current_user.role == Role.SUPPLIER_SALES.value:
            count_query = count_query.where(
                Order.sales_rep_id == current_user.id)
    if status_filter:
        count_query = count_query.where(Order.status == status_filter)

    count_result = await db.execute(count_query)
    total = count_result.scalar_one() or 0

    # Get paginated results
    query = (
        query.order_by(Order.created_at.desc()).offset(
            (page - 1) * size).limit(size)
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
        raise ApplicationError("Not enough permissions",
                               )

    # Get order with items and products (for stock updates)
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise ApplicationError("Order not found",
                               )

    # Check user has permission for this supplier
    has_permission = await is_supplier_owner_or_manager(
        current_user, order.supplier_id, db
    )
    if not has_permission:
        raise ApplicationError("You do not have permission to manage this supplier's orders",
                               )

    # Validate state transition
    _validate_status_transition(order.status, status_update.status)

    # Get consumer user_id for notification (before updating status)
    result = await db.execute(
        select(Consumer).where(Consumer.id == order.consumer_id)
    )
    consumer = result.scalar_one_or_none()
    consumer_user_id = consumer.user_id if consumer else None

    # Get supplier name for notification message
    result = await db.execute(
        select(Supplier).where(Supplier.id == order.supplier_id)
    )
    supplier = result.scalar_one_or_none()
    supplier_name = supplier.company_name if supplier else "Supplier"

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
                    raise ApplicationError(
                        f"Insufficient stock for product {product.name}. Available: {product.stock_qty}, Required: {item.qty}")
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
    old_status = order.status
    order.status = status_update.status
    await db.commit()
    await db.refresh(order)

    # Create notification for consumer when order status changes
    if consumer_user_id and old_status != status_update.status:
        # Map order status to notification message
        status_messages = {
            OrderStatus.ACCEPTED: f"Your order #{order.id} from {supplier_name} has been accepted.",
            OrderStatus.REJECTED: f"Your order #{order.id} from {supplier_name} has been rejected.",
            OrderStatus.IN_PROGRESS: f"Your order #{order.id} from {supplier_name} is now in progress.",
            OrderStatus.COMPLETED: f"Your order #{order.id} from {supplier_name} has been completed.",
        }

        message = status_messages.get(status_update.status)
        if message:
            notification_type = f"order_{status_update.status.value}"
            await create_notification(consumer_user_id, notification_type, message, db, entity_id=order.id, entity_type="order")
            await db.commit()

    # Reload with items, supplier, consumer, and sales_rep
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.items),
            joinedload(Order.supplier).joinedload(Supplier.user),
            joinedload(Order.consumer).joinedload(Consumer.user),
            joinedload(Order.sales_rep),
        )
        .where(Order.id == order.id)
    )
    order = result.scalar_one()

    return OrderResponse.model_validate(order)
