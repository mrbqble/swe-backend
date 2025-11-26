"""Chat management routes."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user
from app.core.exceptions import ApplicationError
from app.core.roles import Role
from app.db.session import get_db
from app.modules.chat.model import ChatMessage, ChatSession
from app.modules.chat.schema import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionResponse,
)
from app.modules.consumer.model import Consumer
from app.modules.order.model import Order
from app.modules.supplier.model import Supplier, SupplierStaff
from app.modules.user.model import User
from app.utils.helpers import get_consumer_by_user_id, get_supplier_by_user_id
from app.utils.pagination import create_pagination_response

ChatRouter = APIRouter(prefix="/chats", tags=["chats"])


async def _is_session_participant(
    user: User, session: ChatSession, db: AsyncSession
) -> bool:
    """Check if user is a participant in the chat session."""
    # Check if user is the consumer
    consumer = await get_consumer_by_user_id(user.id, db)
    if consumer and session.consumer_id == consumer.id:
        return True

    # Check if user is the exact sales rep
    if session.sales_rep_id == user.id:
        return True

    # Check if user is supplier staff from the same supplier as the sales rep
    # Get the supplier_id for the sales rep
    result = await db.execute(
        select(SupplierStaff).where(SupplierStaff.user_id == session.sales_rep_id)
    )
    sales_rep_staff = result.scalar_one_or_none()

    if sales_rep_staff:
        supplier_id = sales_rep_staff.supplier_id
    else:
        # Check if sales rep is the supplier owner
        result = await db.execute(
            select(Supplier).where(Supplier.user_id == session.sales_rep_id)
)
        supplier = result.scalar_one_or_none()
        if supplier:
            supplier_id = supplier.id
        else:
            return False

    # Check if current user is staff from the same supplier
    result = await db.execute(
        select(SupplierStaff).where(
            SupplierStaff.user_id == user.id,
            SupplierStaff.supplier_id == supplier_id,
)
    )
    if result.scalar_one_or_none():
        return True

    # Check if current user is the supplier owner
    result = await db.execute(
        select(Supplier).where(
            Supplier.id == supplier_id,
            Supplier.user_id == user.id,
)
    )
    return result.scalar_one_or_none() is not None


@ChatRouter.post(
    "/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED
)
async def create_chat_session(
    session_data: ChatSessionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ChatSessionResponse:
    """Create a chat session (consumer only)."""
    # Check user is consumer
    if current_user.role != Role.CONSUMER.value:
        raise ApplicationError("Not enough permissions",
)

    # Get consumer
    consumer = await get_consumer_by_user_id(current_user.id, db)
    if not consumer:
        raise ApplicationError("Consumer profile not found",
)

    sales_rep_id = session_data.sales_rep_id
    order = None

    # If order_id is provided, verify it exists and belongs to the consumer
    if session_data.order_id:
        result = await db.execute(
            select(Order).where(Order.id == session_data.order_id)
)
        order = result.scalar_one_or_none()
        if not order:
            raise ApplicationError("Order not found")
        if order.consumer_id != consumer.id:
            raise ApplicationError("Order does not belong to you")

    # Auto-assign sales rep if not provided and order_id is given
    if not sales_rep_id:
        if not order:
            raise ApplicationError("Either sales_rep_id or order_id must be provided")

        # Get supplier from order
        supplier_id = order.supplier_id

        # Try to find a sales rep for this supplier
        result = await db.execute(
            select(SupplierStaff)
            .join(User, SupplierStaff.user_id == User.id)
            .where(SupplierStaff.supplier_id == supplier_id)
            .where(SupplierStaff.staff_role.ilike("%sales%"))
            .where(User.is_active)
            .limit(1)
)
        sales_rep_staff = result.scalar_one_or_none()
        if sales_rep_staff:
            sales_rep_id = sales_rep_staff.user_id
        else:
            # If no sales rep found, try to get any active staff member
            result = await db.execute(
                select(SupplierStaff)
                .join(User, SupplierStaff.user_id == User.id)
                .where(SupplierStaff.supplier_id == supplier_id)
                .where(User.is_active)
                .limit(1)
    )
            sales_rep_staff = result.scalar_one_or_none()
            if sales_rep_staff:
                sales_rep_id = sales_rep_staff.user_id
            else:
                # Last resort: try to get the supplier owner
                result = await db.execute(
                    select(Supplier)
                    .join(User, Supplier.user_id == User.id)
                    .where(Supplier.id == supplier_id)
                    .where(User.is_active)
        )
                supplier = result.scalar_one_or_none()
                if supplier and supplier.user_id:
                    sales_rep_id = supplier.user_id
                else:
                    raise ApplicationError("No sales representative found for this supplier. Please contact support.")

    # Verify sales rep exists and is a valid user
    result = await db.execute(select(User).where(User.id == sales_rep_id))
    sales_rep = result.scalar_one_or_none()
    if not sales_rep:
        raise ApplicationError("Sales representative not found",
)

    # If order_id is provided, verify sales rep is associated with the order's supplier
    if order:
        result = await db.execute(
            select(SupplierStaff).where(
                SupplierStaff.user_id == sales_rep_id,
                SupplierStaff.supplier_id == order.supplier_id,
    )
)
        staff = result.scalar_one_or_none()
        if not staff:
            # Check if it's the supplier owner
            result = await db.execute(
                select(Supplier).where(
                    Supplier.id == order.supplier_id,
                    Supplier.user_id == sales_rep_id,
        )
    )
            if not result.scalar_one_or_none():
                raise ApplicationError("Sales representative is not associated with the order's supplier")
    else:
        # If no order_id, just verify the user is a sales rep
        result = await db.execute(
            select(SupplierStaff).where(SupplierStaff.user_id == sales_rep_id)
)
        staff = result.scalar_one_or_none()
        if not staff:
            raise ApplicationError("User is not a sales representative")

    # Create chat session
    chat_session = ChatSession(
        consumer_id=consumer.id,
        sales_rep_id=sales_rep_id,
        order_id=session_data.order_id,
    )
    db.add(chat_session)
    await db.commit()
    await db.refresh(chat_session)

    # Reload chat session with relationships for response
    result = await db.execute(
        select(ChatSession)
        .options(
            selectinload(ChatSession.consumer).selectinload(Consumer.user),
            selectinload(ChatSession.sales_rep),
)
        .where(ChatSession.id == chat_session.id)
    )
    chat_session = result.scalar_one()

    return ChatSessionResponse.model_validate(chat_session)


@ChatRouter.get(
    "/sessions", response_model=dict
)  # Will be PaginationResponse[ChatSessionResponse]
async def get_chat_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get chat sessions (consumer: own sessions, supplier staff: all sessions for their supplier)."""
    from sqlalchemy import func

    query = select(ChatSession)
    supplier_user_ids = None

    # Consumer: get their own sessions
    if current_user.role == Role.CONSUMER.value:
        consumer = await get_consumer_by_user_id(current_user.id, db)
        if not consumer:
            raise ApplicationError("Consumer profile not found")
        query = query.where(ChatSession.consumer_id == consumer.id)

    # Supplier staff (owner, manager, sales rep): get all sessions for their supplier
    elif current_user.role in (
        Role.SUPPLIER_OWNER.value,
        Role.SUPPLIER_MANAGER.value,
        Role.SUPPLIER_SALES.value,
    ):
        # Get supplier_id for the current user
        supplier = await get_supplier_by_user_id(current_user.id, db)
        supplier_id = None

        if supplier:
            supplier_id = supplier.id
        else:
            # If not supplier owner, check if they're staff
            result = await db.execute(
                select(SupplierStaff).where(SupplierStaff.user_id == current_user.id)
    )
            staff = result.scalar_one_or_none()
            if staff:
                supplier_id = staff.supplier_id

        if not supplier_id:
            raise ApplicationError("Supplier profile not found for this user")

        # Get all staff user IDs for this supplier (including owner)
        # First, get the supplier owner
        result = await db.execute(
            select(Supplier.user_id).where(Supplier.id == supplier_id)
)
        owner_user_id = result.scalar_one_or_none()

        # Get all staff user IDs
        result = await db.execute(
            select(SupplierStaff.user_id).where(
                SupplierStaff.supplier_id == supplier_id
    )
)
        staff_user_ids = [row[0] for row in result.all()]

        # Combine owner and staff user IDs
        supplier_user_ids = set(staff_user_ids)
        if owner_user_id:
            supplier_user_ids.add(owner_user_id)

        # Filter sessions where sales_rep_id is one of the supplier's staff
        if supplier_user_ids:
            query = query.where(ChatSession.sales_rep_id.in_(supplier_user_ids))
        else:
            # No staff found, return empty result
            query = query.where(ChatSession.id == -1)  # Impossible condition
    else:
        raise ApplicationError("Not enough permissions",
)

    # Get total count using the same filtering logic
    count_query = select(func.count(ChatSession.id))
    if current_user.role == Role.CONSUMER.value:
        consumer = await get_consumer_by_user_id(current_user.id, db)
        if consumer:
            count_query = count_query.where(ChatSession.consumer_id == consumer.id)
    elif current_user.role in (
        Role.SUPPLIER_OWNER.value,
        Role.SUPPLIER_MANAGER.value,
        Role.SUPPLIER_SALES.value,
    ):
        # Use the supplier_user_ids we already computed
        if supplier_user_ids:
            count_query = count_query.where(
                ChatSession.sales_rep_id.in_(supplier_user_ids)
    )
        else:
            count_query = count_query.where(
                ChatSession.id == -1
    )  # Impossible condition

    count_result = await db.execute(count_query)
    total = count_result.scalar_one() or 0

    # Get paginated results with relationships loaded
    query = (
        query.options(
            selectinload(ChatSession.consumer).selectinload(Consumer.user),
            selectinload(ChatSession.sales_rep),
)
        .order_by(ChatSession.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await db.execute(query)
    sessions = result.scalars().all()

    # Get last message for each session and build response
    session_responses = []
    for session in sessions:
        # Get the last message for this session
        last_msg_query = (
            select(ChatMessage.text)
            .where(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.created_at.desc())
            .limit(1)
)
        last_msg_result = await db.execute(last_msg_query)
        last_message = last_msg_result.scalar_one_or_none()

        # Create response from session model, then add last_message
        session_response = ChatSessionResponse.model_validate(session)
        # Use model_copy to create a new instance with last_message
        session_response = session_response.model_copy(
            update={"last_message": last_message}
)
        session_responses.append(session_response)

    return create_pagination_response(session_responses, page, size, total).model_dump()


@ChatRouter.post(
    "/sessions/{session_id}/messages",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_chat_message(
    session_id: int,
    message_data: ChatMessageCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ChatMessageResponse:
    """Create a chat message (only session participants)."""
    # Get chat session
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise ApplicationError("Chat session not found",
)

    # Check if user is a participant
    is_participant = await _is_session_participant(current_user, session, db)
    if not is_participant:
        raise ApplicationError("You are not a participant in this chat session",
)

    # Create message
    message = ChatMessage(
        session_id=session_id,
        sender_id=current_user.id,
        text=message_data.text,
        file_url=message_data.file_url,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    return ChatMessageResponse.model_validate(message)


@ChatRouter.get(
    "/sessions/{session_id}/messages", response_model=dict
)  # Will be PaginationResponse[ChatMessageResponse]
async def get_chat_messages(
    session_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get chat messages (only session participants)."""
    # Get chat session
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise ApplicationError("Chat session not found",
)

    # Check if user is a participant
    is_participant = await _is_session_participant(current_user, session, db)
    if not is_participant:
        raise ApplicationError("You are not a participant in this chat session",
)

    # Get messages
    query = select(ChatMessage).where(ChatMessage.session_id == session_id)

    # Get total count
    count_query = select(func.count(ChatMessage.id)).where(
        ChatMessage.session_id == session_id
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar_one() or 0

    # Get paginated results with sender relationship loaded
    query = (
        query.options(selectinload(ChatMessage.sender))
        .order_by(ChatMessage.created_at.asc())
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await db.execute(query)
    messages = result.scalars().all()

    # Create response
    message_responses = [ChatMessageResponse.model_validate(msg) for msg in messages]
    return create_pagination_response(message_responses, page, size, total).model_dump()
