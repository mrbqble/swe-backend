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
from app.modules.chat.model import ChatMessage, ChatMessageAttachment, ChatSession
from app.modules.chat.schema import (
    ChatAttachmentCreate,
    ChatMessageCreate,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionResponse,
)
from app.modules.consumer.model import Consumer
from app.modules.link.model import Link, LinkStatus
from app.modules.supplier.model import Supplier, SupplierStaff
from app.modules.user.model import User
from app.utils.helpers import (
    create_notification,
    get_consumer_by_user_id,
    get_supplier_by_user_id,
    get_supplier_id_for_user,
)
from app.utils.pagination import create_pagination_response

ChatRouter = APIRouter(prefix="/chats", tags=["chats"])


async def _is_session_participant(
    user: User, session: ChatSession, db: AsyncSession
) -> bool:
    """Check if user is a participant in the chat session.

    For consumers: Checks by specific consumer_id (not by organization).
    Each consumer is treated as a unique organization (1 consumer = 1 organization).
    """
    # Check if user is the consumer (by consumer_id, not organization)
    consumer = await get_consumer_by_user_id(user.id, db)
    if consumer and session.consumer_id == consumer.id:
        return True

    # Check if user is the exact sales rep
    if session.sales_rep_id == user.id:
        return True

    # Check if user is supplier staff from the same supplier as the sales rep
    # Get the supplier_id for the sales rep
    result = await db.execute(
        select(SupplierStaff).where(
            SupplierStaff.user_id == session.sales_rep_id)
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
    """
    Get or create a chat session for a Consumer-Supplier pair.

    According to specs: There is a single 1-1 chat thread per linked Consumer-Supplier pair
    once the link is approved. This thread is reused for all conversations about any order.
    """
    from app.modules.link.model import Link, LinkStatus

    # Check user is consumer
    if current_user.role != Role.CONSUMER.value:
        raise ApplicationError("Not enough permissions")

    # Get consumer
    consumer = await get_consumer_by_user_id(current_user.id, db)
    if not consumer:
        raise ApplicationError("Consumer profile not found")

    supplier_id = session_data.supplier_id
    sales_rep_id = session_data.sales_rep_id

    # If supplier_id is not set yet, get it from sales_rep_id
    if not supplier_id:
        if sales_rep_id:
            # Get supplier_id from sales rep
            result = await db.execute(
                select(SupplierStaff).where(
                    SupplierStaff.user_id == sales_rep_id)
            )
            staff = result.scalar_one_or_none()
            if staff:
                supplier_id = staff.supplier_id
            else:
                # Check if it's the supplier owner
                result = await db.execute(
                    select(Supplier).where(Supplier.user_id == sales_rep_id)
                )
                supplier = result.scalar_one_or_none()
                if supplier:
                    supplier_id = supplier.id
        else:
            raise ApplicationError(
                "Either supplier_id or sales_rep_id must be provided")

    if not supplier_id:
        raise ApplicationError("Could not determine supplier")

    # Verify there's an accepted link between consumer and supplier
    result = await db.execute(
        select(Link).where(
            Link.consumer_id == consumer.id,
            Link.supplier_id == supplier_id,
            Link.status == LinkStatus.ACCEPTED,
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise ApplicationError(
            "You do not have an accepted link with this supplier")

    # Auto-assign sales rep if not provided
    if not sales_rep_id:
        # Get any active sales rep for this supplier
        from app.utils.helpers import assign_sales_representative
        sales_rep_id = await assign_sales_representative(supplier_id, db)

    # Verify sales rep exists and is associated with the supplier
    result = await db.execute(select(User).where(User.id == sales_rep_id))
    sales_rep = result.scalar_one_or_none()
    if not sales_rep:
        raise ApplicationError("Sales representative not found")

    # Verify sales rep is associated with the supplier
    result = await db.execute(
        select(SupplierStaff).where(
            SupplierStaff.user_id == sales_rep_id,
            SupplierStaff.supplier_id == supplier_id,
        )
    )
    staff = result.scalar_one_or_none()
    if not staff:
        # Check if it's the supplier owner
        result = await db.execute(
            select(Supplier).where(
                Supplier.id == supplier_id,
                Supplier.user_id == sales_rep_id,
            )
        )
        if not result.scalar_one_or_none():
            raise ApplicationError(
                "Sales representative is not associated with this supplier")

    # Check if a session already exists for this consumer-supplier pair
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.consumer_id == consumer.id,
            ChatSession.supplier_id == supplier_id,
        )
    )
    existing_session = result.scalar_one_or_none()

    if existing_session:
        # Session already exists - return it (same thread reused for all orders)
        chat_session = existing_session
    else:
        # Create new chat session
        chat_session = ChatSession(
            consumer_id=consumer.id,
            supplier_id=supplier_id,
            sales_rep_id=sales_rep_id,
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
    """Get chat sessions (consumer: own sessions, supplier staff: all sessions for their supplier).

    For consumers: Filters by specific consumer_id (not by organization).
    Each consumer is treated as a unique organization (1 consumer = 1 organization).
    """
    from sqlalchemy import func

    query = select(ChatSession)
    supplier_user_ids = None

    # Consumer: get only their own sessions (filtered by specific consumer_id, not organization)
    # Each consumer is treated as a unique organization (1 consumer = 1 organization)
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
        # Get supplier_id for the current user (owner, manager, or sales)
        supplier_id = await get_supplier_id_for_user(current_user, db)
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
            query = query.where(
                ChatSession.sales_rep_id.in_(supplier_user_ids))
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
            count_query = count_query.where(
                ChatSession.consumer_id == consumer.id)
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
    session_responses: list[ChatSessionResponse] = []
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

    # Validate attachments
    if message_data.attachments:
        # Limit total attachment size (e.g., 10MB total)
        max_total_size = 10 * 1024 * 1024  # 10MB
        total_size = sum(
            (att.file_size or 0) for att in message_data.attachments
        )
        if total_size > max_total_size:
            raise ApplicationError(
                f"Total attachment size exceeds {max_total_size / (1024 * 1024):.1f}MB limit"
            )

        # Limit number of attachments per message
        if len(message_data.attachments) > 10:
            raise ApplicationError(
                "Maximum 10 attachments per message allowed")

    # Create message
    message = ChatMessage(
        session_id=session_id,
        sender_id=current_user.id,
        text=message_data.text,
        file_url=message_data.file_url,
    )
    db.add(message)
    await db.flush()  # Flush to get message.id

    # Create attachments if provided
    if message_data.attachments:
        for att_data in message_data.attachments:
            attachment = ChatMessageAttachment(
                message_id=message.id,
                file_type=att_data.file_type,
                file_name=att_data.file_name,
                mime_type=att_data.mime_type,
                file_data=att_data.file_data,
                file_size=att_data.file_size,
            )
            db.add(attachment)

    await db.commit()
    await db.refresh(message)

    # Create notification for the recipient (the other party in the chat)
    # Determine recipient: if sender is consumer, notify supplier side; if sender is supplier side, notify consumer
    recipient_id = None

    # Check if sender is the consumer
    consumer = await get_consumer_by_user_id(current_user.id, db)
    is_consumer_sender = consumer and consumer.id == session.consumer_id

    if is_consumer_sender:
        # Sender is consumer, notify sales rep (supplier side)
        recipient_id = session.sales_rep_id
    else:
        # Sender is supplier side (sales rep, manager, or owner), notify consumer
        consumer_result = await db.execute(
            select(Consumer).where(Consumer.id == session.consumer_id)
        )
        consumer_result_obj = consumer_result.scalar_one_or_none()
        if consumer_result_obj:
            recipient_id = consumer_result_obj.user_id

    if recipient_id:
        # Get sender name for notification
        sender_name = f"{current_user.first_name} {current_user.last_name}".strip(
        ) or current_user.email
        has_attachments = bool(message_data.attachments and len(
            message_data.attachments) > 0)
        attachment_text = ""
        if has_attachments:
            attachment_count = len(message_data.attachments)
            attachment_types = set(
                att.file_type for att in message_data.attachments if att.file_type)
            if "image" in attachment_types:
                attachment_text = f" with {attachment_count} image{'s' if attachment_count > 1 else ''}"
            elif "audio" in attachment_types:
                attachment_text = f" with {attachment_count} audio file{'s' if attachment_count > 1 else ''}"
            else:
                attachment_text = f" with {attachment_count} attachment{'s' if attachment_count > 1 else ''}"

        message_text = message_data.text or ""
        if message_text and has_attachments:
            notification_message = f"{sender_name} sent you a message{attachment_text}: {message_text[:50]}{'...' if len(message_text) > 50 else ''}"
        elif message_text:
            notification_message = f"{sender_name} sent you a message: {message_text[:100]}{'...' if len(message_text) > 100 else ''}"
        elif has_attachments:
            notification_message = f"{sender_name} sent you {attachment_count} attachment{'s' if attachment_count > 1 else ''}{attachment_text}"
        else:
            notification_message = f"{sender_name} sent you a message"

        await create_notification(
            recipient_id,
            "chat_message",
            notification_message,
            db,
            entity_id=session_id,
            entity_type="chat_session",
            metadata={"message_id": message.id}  # Store message_id in metadata for scrolling
        )
        await db.commit()

    # Reload message with attachments for response
    result = await db.execute(
        select(ChatMessage)
        .options(selectinload(ChatMessage.attachments), selectinload(ChatMessage.sender))
        .where(ChatMessage.id == message.id)
    )
    message = result.scalar_one()

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

    # Get paginated results with sender and attachments relationships loaded
    query = (
        query.options(
            selectinload(ChatMessage.sender),
            selectinload(ChatMessage.attachments),
        )
        .order_by(ChatMessage.created_at.asc())
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await db.execute(query)
    messages = result.scalars().all()

    # Create response
    message_responses = [
        ChatMessageResponse.model_validate(msg) for msg in messages]
    return create_pagination_response(message_responses, page, size, total).model_dump()
