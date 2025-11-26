"""Complaint management routes."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user
from app.core.exceptions import ApplicationError
from app.core.roles import Role
from app.db.session import get_db
from app.modules.complaint.model import Complaint, ComplaintStatus
from app.modules.complaint.schema import (
    ComplaintCreate,
    ComplaintFeedbackUpdate,
    ComplaintResponse,
    ComplaintStatusUpdate,
)
from app.modules.consumer.model import Consumer
from app.modules.order.model import Order
from app.modules.supplier.model import Supplier, SupplierStaff
from app.modules.user.model import User
from app.utils.helpers import create_notification, get_consumer_by_user_id
from app.utils.pagination import create_pagination_response

ComplaintRouter = APIRouter(prefix="/complaints", tags=["complaints"])


def _validate_status_transition(
    current_status: ComplaintStatus,
    new_status: ComplaintStatus,
    allow_reopen: bool = False,
) -> None:
    """Validate state machine transitions for complaint status."""
    valid_transitions = {
        ComplaintStatus.OPEN: {ComplaintStatus.ESCALATED, ComplaintStatus.RESOLVED},
        ComplaintStatus.ESCALATED: {ComplaintStatus.RESOLVED},
        ComplaintStatus.RESOLVED: {ComplaintStatus.OPEN}
        if allow_reopen
        # Resolved complaints can be reopened by consumer if not satisfied
        else set[ComplaintStatus](),
    }

    # Use a plain empty set() as default; type checkers know it's a set[ComplaintStatus]
    allowed = valid_transitions.get(current_status, set[ComplaintStatus]())
    if new_status not in allowed:
        raise ApplicationError(f"Cannot transition from {current_status.value} to {new_status.value}",
                               )


async def _can_access_complaint(
    user: User, complaint: Complaint, db: AsyncSession
) -> bool:
    """Check if user can access the complaint.

    For consumers: Checks by specific consumer_id (not by organization).
    Each consumer is treated as a unique organization (1 consumer = 1 organization).
    """
    # Consumer can only access their own complaints (by consumer_id, not organization)
    consumer = await get_consumer_by_user_id(user.id, db)
    if consumer and complaint.consumer_id == consumer.id:
        return True

    # Sales rep can access complaints where they are the sales rep
    if complaint.sales_rep_id == user.id:
        return True

    # Manager can access complaints where they are the manager
    return complaint.manager_id == user.id


@ComplaintRouter.post(
    "", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED
)
async def create_complaint(
    complaint_data: ComplaintCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ComplaintResponse:
    """Create a complaint (consumer only)."""
    # Check user is consumer
    if current_user.role != Role.CONSUMER.value:
        raise ApplicationError("Not enough permissions",
                               )

    # Get consumer
    consumer = await get_consumer_by_user_id(current_user.id, db)
    if not consumer:
        raise ApplicationError("Consumer profile not found",
                               )

    # Verify order exists and belongs to consumer
    result = await db.execute(select(Order).where(Order.id == complaint_data.order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise ApplicationError("Order not found",
                               )
    if order.consumer_id != consumer.id:
        raise ApplicationError("Order does not belong to you",
                               )

    # Auto-assign sales rep and manager if not provided or if provided values are invalid
    sales_rep_id = complaint_data.sales_rep_id
    manager_id = complaint_data.manager_id

    # Use order's sales_rep_id if not provided
    if not sales_rep_id and order.sales_rep_id:
        sales_rep_id = order.sales_rep_id

    # Validate provided sales_rep_id if given
    if sales_rep_id:
        result = await db.execute(
            select(User).where(User.id == sales_rep_id, User.is_active)
        )
        sales_rep_user = result.scalar_one_or_none()
        if not sales_rep_user:
            sales_rep_id = None  # Invalid user, will auto-assign
        else:
            # Check if user is associated with supplier
            result = await db.execute(
                select(SupplierStaff).where(
                    SupplierStaff.user_id == sales_rep_id,
                    SupplierStaff.supplier_id == order.supplier_id,
                )
            )
            if not result.scalar_one_or_none():
                # Also check if it's the supplier owner
                result = await db.execute(
                    select(Supplier).where(
                        Supplier.id == order.supplier_id,
                        Supplier.user_id == sales_rep_id,
                    )
                )
                if not result.scalar_one_or_none():
                    sales_rep_id = None  # Not associated with supplier, will auto-assign

    # Validate provided manager_id if given
    if manager_id:
        result = await db.execute(
            select(User).where(User.id == manager_id, User.is_active)
        )
        manager_user = result.scalar_one_or_none()
        if not manager_user:
            manager_id = None  # Invalid user, will auto-assign
        else:
            # Check if user is associated with supplier (as staff or owner)
            result = await db.execute(
                select(SupplierStaff).where(
                    SupplierStaff.user_id == manager_id,
                    SupplierStaff.supplier_id == order.supplier_id,
                )
            )
            if not result.scalar_one_or_none():
                # Check if it's the supplier owner
                result = await db.execute(
                    select(Supplier).where(
                        Supplier.id == order.supplier_id,
                        Supplier.user_id == manager_id,
                    )
                )
                if not result.scalar_one_or_none():
                    manager_id = None  # Not associated with supplier, will auto-assign

    if not sales_rep_id or not manager_id:
        # Get supplier staff for auto-assignment
        # First, try to get a sales rep (with active user)
        if not sales_rep_id:
            # Use helper function to assign sales rep
            from app.utils.helpers import assign_sales_representative
            sales_rep_id = await assign_sales_representative(order.supplier_id, db)

        # Get a manager or owner
        if not manager_id:
            # Try to find staff with "manager" in their role (case-insensitive) with active user
            result = await db.execute(
                select(SupplierStaff)
                .join(User, SupplierStaff.user_id == User.id)
                .where(SupplierStaff.supplier_id == order.supplier_id)
                .where(SupplierStaff.staff_role.ilike("%manager%"))
                .where(User.is_active)
                .limit(1)
            )
            manager_staff = result.scalar_one_or_none()
            if manager_staff:
                manager_id = manager_staff.user_id
            else:
                # If no manager found, try to get the supplier owner (with active user)
                result = await db.execute(
                    select(Supplier)
                    .join(User, Supplier.user_id == User.id)
                    .where(Supplier.id == order.supplier_id)
                    .where(User.is_active)
                )
                supplier = result.scalar_one_or_none()
                if supplier and supplier.user_id:
                    manager_id = supplier.user_id

    # Verify sales rep exists and is associated with supplier
    if sales_rep_id:
        result = await db.execute(select(User).where(User.id == sales_rep_id))
        sales_rep = result.scalar_one_or_none()
        if not sales_rep:
            raise ApplicationError("Sales representative not found")

        result = await db.execute(
            select(SupplierStaff).where(
                SupplierStaff.user_id == sales_rep_id,
                SupplierStaff.supplier_id == order.supplier_id,
            )
        )
        sales_rep_staff = result.scalar_one_or_none()
        if not sales_rep_staff:
            raise ApplicationError(
                "Sales representative is not associated with the order's supplier")
    else:
        raise ApplicationError("No sales representative found for this supplier. Please contact support.",
                               )

    # Verify manager exists and is associated with supplier
    if manager_id:
        result = await db.execute(select(User).where(User.id == manager_id))
        manager = result.scalar_one_or_none()
        if not manager:
            raise ApplicationError("Manager not found")

        result = await db.execute(
            select(SupplierStaff).where(
                SupplierStaff.user_id == manager_id,
                SupplierStaff.supplier_id == order.supplier_id,
            )
        )
        manager_staff = result.scalar_one_or_none()
        if not manager_staff:
            # Check if it's the supplier owner
            result = await db.execute(
                select(Supplier).where(
                    Supplier.id == order.supplier_id,
                    Supplier.user_id == manager_id,
                )
            )
            supplier = result.scalar_one_or_none()
            if not supplier:
                raise ApplicationError(
                    "Manager is not associated with the order's supplier")
    else:
        raise ApplicationError("No manager found for this supplier. Please contact support.",
                               )

    # Create complaint
    complaint = Complaint(
        order_id=complaint_data.order_id,
        consumer_id=consumer.id,
        sales_rep_id=sales_rep_id,
        manager_id=manager_id,
        status=ComplaintStatus.OPEN,
        description=complaint_data.description,
    )
    db.add(complaint)
    await db.commit()
    await db.refresh(complaint)

    # Post system message in the chat thread about the complaint
    # Find or create the chat session for this consumer-sales_rep pair
    # According to SRS: complaints are posted in the same 1-1 chat thread
    from app.modules.chat.model import ChatSession, ChatMessage
    from app.modules.link.model import Link, LinkStatus
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

    if not link:
        # Link should exist if order exists, but handle gracefully
        # Don't create chat session if link is not accepted
        pass
    else:
        # Find or create chat session
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.consumer_id == consumer.id,
                ChatSession.supplier_id == order.supplier_id,
            )
        )
        chat_session = result.scalar_one_or_none()

        if not chat_session:
            # Create chat session if it doesn't exist (should exist from link acceptance, but create as fallback)
            chat_session = ChatSession(
                consumer_id=consumer.id,
                supplier_id=order.supplier_id,
                sales_rep_id=sales_rep_id,
                created_at=datetime.now(UTC),
            )
            db.add(chat_session)
            await db.flush()  # Flush to get session.id

        # Post structured complaint message in the chat thread
        # Format: Clear complaint notification with order reference
        complaint_message_text = (
            f"🚨 Complaint #{complaint.id} opened for Order #{order.id}\n\n"
            f"Description: {complaint_data.description[:300]}{'...' if len(complaint_data.description) > 300 else ''}"
        )
        complaint_message = ChatMessage(
            session_id=chat_session.id,
            sender_id=current_user.id,  # Consumer who created the complaint
            text=complaint_message_text,
        )
        db.add(complaint_message)
        await db.commit()

    # Create notification for consumer when complaint is created
    # Note: Consumer created the complaint, so we notify the sales rep
    # But the requirement says "consumer should receive notifications" -
    # Since consumer created it, they already know. However, we can notify them for confirmation.
    # Actually, re-reading: "when complaint is created" - consumer should receive notification
    # This might be for confirmation, or the system might want to notify them.
    # Let's notify the consumer for confirmation that their complaint was submitted.
    if consumer.user_id:
        supplier_result = await db.execute(
            select(Supplier).where(Supplier.id == order.supplier_id)
        )
        supplier = supplier_result.scalar_one_or_none()
        supplier_name = supplier.company_name if supplier else "Supplier"
        message = f"Your complaint #{complaint.id} for Order #{order.id} has been submitted to {supplier_name}."
        await create_notification(
            consumer.user_id,
            "complaint_created",
            message,
            db,
            entity_id=complaint.id,
            entity_type="complaint",
            # Store order_id in metadata for navigation
            metadata={"order_id": complaint.order_id}
        )
        await db.commit()

    # Reload complaint with all necessary relationships for response
    result = await db.execute(
        select(Complaint)
        .options(
            selectinload(Complaint.order).selectinload(Order.items),
            selectinload(Complaint.order).selectinload(Order.supplier),
            selectinload(Complaint.order).selectinload(Order.sales_rep),
            selectinload(Complaint.order).selectinload(
                Order.consumer).selectinload(Consumer.user),
            selectinload(Complaint.consumer).selectinload(Consumer.user),
        )
        .where(Complaint.id == complaint.id)
    )
    complaint = result.scalar_one()

    return ComplaintResponse.model_validate(complaint)


@ComplaintRouter.get("/{complaint_id}", response_model=ComplaintResponse)
async def get_complaint(
    complaint_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ComplaintResponse:
    """Get a single complaint (consumer, sales rep, or manager only)."""
    # Get complaint with relationships loaded
    result = await db.execute(
        select(Complaint)
        .options(
            selectinload(Complaint.order).selectinload(Order.items),
            selectinload(Complaint.order).selectinload(Order.supplier),
            selectinload(Complaint.order).selectinload(Order.sales_rep),
            selectinload(Complaint.order).selectinload(
                Order.consumer).selectinload(Consumer.user),
            selectinload(Complaint.consumer).selectinload(Consumer.user),
        )
        .where(Complaint.id == complaint_id)
    )
    complaint = result.scalar_one_or_none()
    if not complaint:
        raise ApplicationError("Complaint not found",
                               )

    # Check access
    can_access = await _can_access_complaint(current_user, complaint, db)
    if not can_access:
        raise ApplicationError("You do not have permission to view this complaint",
                               )

    return ComplaintResponse.model_validate(complaint)


@ComplaintRouter.get(
    "", response_model=dict
)  # Will be PaginationResponse[ComplaintResponse]
async def get_complaints(
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get complaints (filtered by role: consumer sees own, sales rep sees assigned, manager sees assigned).

    For consumers: Filters by specific consumer_id (not by organization).
    Each consumer is treated as a unique organization (1 consumer = 1 organization).
    """
    query = select(Complaint)

    # Consumer: get only their own complaints (filtered by specific consumer_id, not organization)
    # Each consumer is treated as a unique organization (1 consumer = 1 organization)
    if current_user.role == Role.CONSUMER.value:
        consumer = await get_consumer_by_user_id(current_user.id, db)
        if not consumer:
            raise ApplicationError("Consumer profile not found")
        query = query.where(Complaint.consumer_id == consumer.id)

    # Sales rep: get complaints where they are the sales rep
    elif current_user.role in (
        Role.SUPPLIER_OWNER.value,
        Role.SUPPLIER_MANAGER.value,
        Role.SUPPLIER_SALES.value,
    ):
        # Sales rep sees complaints where they are sales_rep_id AND where the order is assigned to them
        # Manager sees complaints where they are manager_id
        # Owner/Manager can see both
        if current_user.role == Role.SUPPLIER_SALES.value:
            # Filter by complaint's sales_rep_id AND ensure the order is also assigned to this sales rep
            # Use a subquery to check order's sales_rep_id without interfering with eager loading
            order_subquery = select(Order.id).where(
                Order.sales_rep_id == current_user.id).scalar_subquery()
            query = query.where(
                (Complaint.sales_rep_id == current_user.id)
                & (Complaint.order_id.in_(order_subquery))
            )
        else:
            # Owner/Manager can see complaints where they are manager or sales rep
            query = query.where(
                (Complaint.manager_id == current_user.id)
                | (Complaint.sales_rep_id == current_user.id)
            )
    else:
        raise ApplicationError("Not enough permissions",
                               )

    # Get total count
    count_query = select(func.count(Complaint.id))
    if current_user.role == Role.CONSUMER.value:
        consumer = await get_consumer_by_user_id(current_user.id, db)
        if consumer:
            count_query = count_query.where(
                Complaint.consumer_id == consumer.id)
    elif current_user.role in (
        Role.SUPPLIER_OWNER.value,
        Role.SUPPLIER_MANAGER.value,
        Role.SUPPLIER_SALES.value,
    ):
        if current_user.role == Role.SUPPLIER_SALES.value:
            # Filter by complaint's sales_rep_id AND ensure the order is also assigned to this sales rep
            # Use a subquery to check order's sales_rep_id
            order_subquery = select(Order.id).where(
                Order.sales_rep_id == current_user.id).scalar_subquery()
            count_query = count_query.where(
                (Complaint.sales_rep_id == current_user.id)
                & (Complaint.order_id.in_(order_subquery))
            )
        else:
            count_query = count_query.where(
                (Complaint.manager_id == current_user.id)
                | (Complaint.sales_rep_id == current_user.id)
            )

    count_result = await db.execute(count_query)
    total = count_result.scalar_one() or 0

    # Get paginated results with relationships loaded
    query = (
        query.options(
            selectinload(Complaint.order).selectinload(Order.items),
            selectinload(Complaint.order).selectinload(Order.supplier),
            selectinload(Complaint.order).selectinload(Order.sales_rep),
            selectinload(Complaint.order).selectinload(
                Order.consumer).selectinload(Consumer.user),
            selectinload(Complaint.consumer).selectinload(Consumer.user),
        )
        .order_by(Complaint.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await db.execute(query)
    complaints = result.scalars().all()

    # Create response
    complaint_responses = [
        ComplaintResponse.model_validate(complaint) for complaint in complaints
    ]
    return create_pagination_response(
        complaint_responses, page, size, total
    ).model_dump()


@ComplaintRouter.patch("/{complaint_id}/status", response_model=ComplaintResponse)
async def update_complaint_status(
    complaint_id: int,
    status_update: ComplaintStatusUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ComplaintResponse:
    """Update complaint status (sales rep or manager only)."""

    # Check user is sales rep or manager
    if current_user.role not in (
        Role.SUPPLIER_OWNER.value,
        Role.SUPPLIER_MANAGER.value,
        Role.SUPPLIER_SALES.value,
    ):
        raise ApplicationError("Not enough permissions",
                               )

    # Get complaint
    result = await db.execute(select(Complaint).where(Complaint.id == complaint_id))
    complaint = result.scalar_one_or_none()
    if not complaint:
        raise ApplicationError("Complaint not found",
                               )

    # Check user is the sales rep or manager for this complaint
    is_sales_rep = complaint.sales_rep_id == current_user.id
    is_manager = complaint.manager_id == current_user.id

    if not (is_sales_rep or is_manager):
        raise ApplicationError("You are not the sales representative or manager for this complaint",
                               )

    # Validate state transition
    _validate_status_transition(
        complaint.status, status_update.status, allow_reopen=False
    )

    # If resolving, require resolution text
    if (
        status_update.status == ComplaintStatus.RESOLVED
        and not status_update.resolution
    ):
        raise ApplicationError("Resolution text is required when resolving a complaint",
                               )

    # Update status
    old_status = complaint.status
    complaint.status = status_update.status
    if status_update.resolution:
        complaint.resolution = status_update.resolution
    await db.commit()

    # Post system message in chat thread about status change
    # Find or create the chat session for this consumer-sales_rep pair
    # According to SRS: complaint status changes are posted in the same 1-1 chat thread
    from app.modules.chat.model import ChatSession, ChatMessage
    from datetime import UTC, datetime

    # Get supplier_id from complaint's order
    from app.modules.order.model import Order
    result = await db.execute(
        select(Order).where(Order.id == complaint.order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise ApplicationError("Order not found for complaint")

    result = await db.execute(
        select(ChatSession).where(
            ChatSession.consumer_id == complaint.consumer_id,
            ChatSession.supplier_id == order.supplier_id,
        )
    )
    chat_session = result.scalar_one_or_none()

    # Create chat session if it doesn't exist (should exist, but create as fallback)
    if not chat_session:
        chat_session = ChatSession(
            consumer_id=complaint.consumer_id,
            supplier_id=order.supplier_id,
            sales_rep_id=complaint.sales_rep_id,
            created_at=datetime.now(UTC),
        )
        db.add(chat_session)
        await db.flush()  # Flush to get session.id

    if old_status != status_update.status:
        # Post structured system message about complaint status change in the chat thread
        status_messages = {
            ComplaintStatus.ESCALATED: (
                f"📤 Complaint #{complaint.id} has been escalated to management for review.\n\n"
                f"Order: #{complaint.order_id}"
            ),
            ComplaintStatus.RESOLVED: (
                f"✅ Complaint #{complaint.id} has been resolved.\n\n"
                f"Order: #{complaint.order_id}\n"
                + (f"Resolution: {status_update.resolution[:300]}{'...' if len(status_update.resolution or '') > 300 else ''}" if status_update.resolution else "")
            ),
        }
        message_text = status_messages.get(status_update.status)
        if message_text:
            # Determine sender: if escalated/resolved by manager, use manager_id; otherwise use sales_rep_id
            # This ensures the message appears from the person who took the action
            sender_id = current_user.id  # Use the current user who is performing the action
            complaint_status_message = ChatMessage(
                session_id=chat_session.id,
                sender_id=sender_id,
                text=message_text,
            )
            db.add(complaint_status_message)
            await db.commit()

    # Create notification for consumer when complaint status changes
    if old_status != status_update.status:
        # Get consumer user_id
        consumer_result = await db.execute(
            select(Consumer).where(Consumer.id == complaint.consumer_id)
        )
        consumer = consumer_result.scalar_one_or_none()
        if consumer and consumer.user_id:
            # Map complaint status to notification message
            status_messages = {
                ComplaintStatus.ESCALATED: f"Your complaint #{complaint.id} has been escalated and is being reviewed by management.",
                ComplaintStatus.RESOLVED: f"Your complaint #{complaint.id} has been resolved." + (f" Resolution: {status_update.resolution[:100]}" if status_update.resolution else ""),
            }

            message = status_messages.get(status_update.status)
            if message:
                notification_type = f"complaint_{status_update.status.value}"
                # For complaints, use order_id as entity_id so navigation goes to order details
                await create_notification(consumer.user_id, notification_type, message, db, entity_id=complaint.order_id, entity_type="order")
                await db.commit()

    # Reload complaint with relationships
    result = await db.execute(
        select(Complaint)
        .options(
            selectinload(Complaint.order).selectinload(Order.items),
            selectinload(Complaint.order).selectinload(Order.supplier),
            selectinload(Complaint.order).selectinload(Order.sales_rep),
            selectinload(Complaint.order).selectinload(
                Order.consumer).selectinload(Consumer.user),
            selectinload(Complaint.consumer).selectinload(Consumer.user),
        )
        .where(Complaint.id == complaint_id)
    )
    complaint = result.scalar_one()

    return ComplaintResponse.model_validate(complaint)


@ComplaintRouter.patch("/{complaint_id}/feedback", response_model=ComplaintResponse)
async def submit_consumer_feedback(
    complaint_id: int,
    feedback: ComplaintFeedbackUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ComplaintResponse:
    """Submit consumer feedback on a resolved complaint (consumer only)."""
    # Check user is consumer
    if current_user.role != Role.CONSUMER.value:
        raise ApplicationError("Not enough permissions",
                               )

    # Get consumer
    consumer = await get_consumer_by_user_id(current_user.id, db)
    if not consumer:
        raise ApplicationError("Consumer profile not found",
                               )

    # Get complaint
    result = await db.execute(select(Complaint).where(Complaint.id == complaint_id))
    complaint = result.scalar_one_or_none()
    if not complaint:
        raise ApplicationError("Complaint not found",
                               )

    # Check complaint belongs to consumer
    if complaint.consumer_id != consumer.id:
        raise ApplicationError("This complaint does not belong to you",
                               )

    # Check complaint is resolved
    if complaint.status != ComplaintStatus.RESOLVED:
        raise ApplicationError("Feedback can only be submitted for resolved complaints",
                               )

    # Check feedback hasn't been submitted already
    if complaint.consumer_feedback is not None:
        raise ApplicationError("Feedback has already been submitted for this complaint",
                               )

    # Update feedback
    complaint.consumer_feedback = feedback.satisfied
    await db.commit()
    await db.refresh(complaint)

    # Post system message in chat thread about feedback
    # Find or create the chat session for this consumer-supplier pair
    from app.modules.chat.model import ChatSession, ChatMessage
    from app.modules.link.model import Link, LinkStatus
    from app.modules.order.model import Order
    from datetime import UTC, datetime

    # Get order to find supplier_id
    result = await db.execute(
        select(Order).where(Order.id == complaint.order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise ApplicationError("Order not found for complaint")

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
        # Find or create chat session
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.consumer_id == consumer.id,
                ChatSession.supplier_id == order.supplier_id,
            )
        )
        chat_session = result.scalar_one_or_none()

        if not chat_session:
            # Create chat session if it doesn't exist (should exist from link acceptance, but create as fallback)
            chat_session = ChatSession(
                consumer_id=consumer.id,
                supplier_id=order.supplier_id,
                sales_rep_id=complaint.sales_rep_id,
                created_at=datetime.now(UTC),
            )
            db.add(chat_session)
            await db.flush()  # Flush to get session.id

        # Post structured feedback message in the chat thread
        feedback_text = "satisfied" if feedback.satisfied else "not satisfied"
        feedback_emoji = "✅" if feedback.satisfied else "❌"
        feedback_message_text = (
            f"{feedback_emoji} Feedback on Complaint #{complaint.id}:\n\n"
            f"Consumer is {feedback_text} with the resolution."
        )
        feedback_message = ChatMessage(
            session_id=chat_session.id,
            sender_id=current_user.id,  # Consumer who provided feedback
            text=feedback_message_text,
            created_at=datetime.now(UTC),
        )
        db.add(feedback_message)
        await db.commit()

    # Create notification for sales rep/manager when feedback is submitted
    # Notify the sales rep assigned to this complaint
    if complaint.sales_rep_id:
        feedback_text = "satisfied" if feedback.satisfied else "not satisfied"
        message = f"Consumer has provided feedback on Complaint #{complaint.id}: {feedback_text} with the resolution."
        await create_notification(complaint.sales_rep_id, "complaint_feedback", message, db, entity_id=complaint.order_id, entity_type="order")
        await db.commit()

    # Also notify manager if different from sales rep
    if complaint.manager_id and complaint.manager_id != complaint.sales_rep_id:
        feedback_text = "satisfied" if feedback.satisfied else "not satisfied"
        message = f"Consumer has provided feedback on Complaint #{complaint.id}: {feedback_text} with the resolution."
        await create_notification(complaint.manager_id, "complaint_feedback", message, db, entity_id=complaint.order_id, entity_type="order")
        await db.commit()

    # Reload complaint with relationships
    result = await db.execute(
        select(Complaint)
        .options(
            selectinload(Complaint.order).selectinload(Order.items),
            selectinload(Complaint.order).selectinload(Order.supplier),
            selectinload(Complaint.order).selectinload(Order.sales_rep),
            selectinload(Complaint.order).selectinload(
                Order.consumer).selectinload(Consumer.user),
            selectinload(Complaint.consumer).selectinload(Consumer.user),
        )
        .where(Complaint.id == complaint_id)
    )
    complaint = result.scalar_one()

    return ComplaintResponse.model_validate(complaint)


@ComplaintRouter.patch("/{complaint_id}/reopen", response_model=ComplaintResponse)
async def reopen_complaint(
    complaint_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ComplaintResponse:
    """Reopen a resolved complaint (consumer only, if not satisfied)."""
    # Check user is consumer
    if current_user.role != Role.CONSUMER.value:
        raise ApplicationError("Not enough permissions",
                               )

    # Get consumer
    consumer = await get_consumer_by_user_id(current_user.id, db)
    if not consumer:
        raise ApplicationError("Consumer profile not found",
                               )

    # Get complaint
    result = await db.execute(select(Complaint).where(Complaint.id == complaint_id))
    complaint = result.scalar_one_or_none()
    if not complaint:
        raise ApplicationError("Complaint not found",
                               )

    # Check complaint belongs to consumer
    if complaint.consumer_id != consumer.id:
        raise ApplicationError("This complaint does not belong to you",
                               )

    # Check complaint is resolved
    if complaint.status != ComplaintStatus.RESOLVED:
        raise ApplicationError("Only resolved complaints can be reopened",
                               )

    # Check feedback: can only reopen if feedback is False (not satisfied) or None (no feedback yet)
    if complaint.consumer_feedback is True:
        raise ApplicationError("Cannot reopen complaint: you indicated you were satisfied with the resolution",
                               )

    # Validate state transition (allow reopen)
    _validate_status_transition(
        complaint.status, ComplaintStatus.OPEN, allow_reopen=True
    )

    # Reopen complaint
    complaint.status = ComplaintStatus.OPEN
    # Clear feedback if it was False, so consumer can provide feedback again after new resolution
    if complaint.consumer_feedback is False:
        complaint.consumer_feedback = None
    await db.commit()
    await db.refresh(complaint)

    # Post system message in chat thread about reopening
    # Find or create the chat session for this consumer-supplier pair
    from app.modules.chat.model import ChatSession, ChatMessage
    from app.modules.link.model import Link, LinkStatus
    from app.modules.order.model import Order
    from datetime import UTC, datetime

    # Get order to find supplier_id
    result = await db.execute(
        select(Order).where(Order.id == complaint.order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise ApplicationError("Order not found for complaint")

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
        # Find or create chat session
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.consumer_id == consumer.id,
                ChatSession.supplier_id == order.supplier_id,
            )
        )
        chat_session = result.scalar_one_or_none()

        if not chat_session:
            # Create chat session if it doesn't exist (should exist from link acceptance, but create as fallback)
            chat_session = ChatSession(
                consumer_id=consumer.id,
                supplier_id=order.supplier_id,
                sales_rep_id=complaint.sales_rep_id,
                created_at=datetime.now(UTC),
            )
            db.add(chat_session)
            await db.flush()  # Flush to get session.id

        # Post structured reopen message in the chat thread
        reopen_message_text = (
            f"🔄 Complaint #{complaint.id} has been reopened by the consumer.\n\n"
            f"Order: #{complaint.order_id}\n"
            f"The consumer was not satisfied with the previous resolution."
        )
        reopen_message = ChatMessage(
            session_id=chat_session.id,
            sender_id=current_user.id,  # Consumer who reopened the complaint
            text=reopen_message_text,
            created_at=datetime.now(UTC),
        )
        db.add(reopen_message)
        await db.commit()

    # Create notifications for sales rep and manager when complaint is reopened
    if complaint.sales_rep_id:
        message = f"Complaint #{complaint.id} for Order #{complaint.order_id} has been reopened by the consumer."
        await create_notification(complaint.sales_rep_id, "complaint_reopened", message, db, entity_id=complaint.order_id, entity_type="order")
        await db.commit()

    if complaint.manager_id and complaint.manager_id != complaint.sales_rep_id:
        message = f"Complaint #{complaint.id} for Order #{complaint.order_id} has been reopened by the consumer."
        await create_notification(complaint.manager_id, "complaint_reopened", message, db, entity_id=complaint.order_id, entity_type="order")
        await db.commit()

    # Reload complaint with relationships
    result = await db.execute(
        select(Complaint)
        .options(
            selectinload(Complaint.order).selectinload(Order.items),
            selectinload(Complaint.order).selectinload(Order.supplier),
            selectinload(Complaint.order).selectinload(Order.sales_rep),
            selectinload(Complaint.order).selectinload(
                Order.consumer).selectinload(Consumer.user),
            selectinload(Complaint.consumer).selectinload(Consumer.user),
        )
        .where(Complaint.id == complaint_id)
    )
    complaint = result.scalar_one()

    return ComplaintResponse.model_validate(complaint)
