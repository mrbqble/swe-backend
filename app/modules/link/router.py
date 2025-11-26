"""Link management routes."""

import contextlib
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user
from app.core.exceptions import ApplicationError
from app.core.roles import Role
from app.db.session import get_db
from app.modules.chat.model import ChatSession
from app.modules.consumer.model import Consumer
from app.modules.link.model import Link, LinkStatus
from app.modules.link.schema import LinkRequestCreate, LinkResponse, LinkStatusUpdate
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

LinkRouter = APIRouter(prefix="/links", tags=["links"])

logger = logging.getLogger(__name__)


def _validate_status_transition(
    current_status: LinkStatus, new_status: LinkStatus
) -> None:
    """Validate state machine transitions for link status."""
    valid_transitions = {
        LinkStatus.PENDING: {LinkStatus.ACCEPTED, LinkStatus.DENIED},
        LinkStatus.ACCEPTED: {
            LinkStatus.BLOCKED,
            LinkStatus.UNLINKED,
        },  # Allow blocking or unlinking
        # Allow accepting denied requests
        LinkStatus.DENIED: {LinkStatus.PENDING, LinkStatus.ACCEPTED},
        # Allow unblocking back to accepted
        LinkStatus.BLOCKED: {LinkStatus.ACCEPTED},
        # Allow accepting unlinked requests directly
        LinkStatus.UNLINKED: {LinkStatus.PENDING, LinkStatus.ACCEPTED},
    }

    allowed = valid_transitions.get(current_status, set[LinkStatus]())
    if new_status not in allowed:
        raise ApplicationError(f"Cannot transition from {current_status.value} to {new_status.value}",
                               )


@LinkRouter.post(
    "/requests", response_model=LinkResponse, status_code=status.HTTP_201_CREATED
)
async def create_link_request(
    request: LinkRequestCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> LinkResponse:
    """Create a link request (consumer only)."""
    # Check user is consumer
    if current_user.role != Role.CONSUMER.value:
        raise ApplicationError("Not enough permissions",
                               )

    # Get consumer
    consumer = await get_consumer_by_user_id(current_user.id, db)
    # Debug logging to help diagnose missing consumer profiles during integration
    with contextlib.suppress(Exception):
        # Avoid failing the request because logging failed
        logger.info(
            "create_link_request: user_id=%s role=%s consumer_found=%s",
            current_user.id,
            current_user.role,
            bool(consumer),
        )
    if not consumer:
        logger.warning(
            "Consumer profile not found for user_id=%s when creating link request",
            current_user.id,
        )
        raise ApplicationError("Consumer profile not found",
                               )

    # Check supplier exists
    result = await db.execute(
        select(Supplier).where(Supplier.id == request.supplier_id)
    )
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise ApplicationError("Supplier not found",
                               )

    # Check if link already exists
    result = await db.execute(
        select(Link).where(
            Link.consumer_id == consumer.id,
            Link.supplier_id == request.supplier_id,
        )
    )
    existing_link = result.scalar_one_or_none()
    if existing_link:
        raise ApplicationError("Link request already exists",
                               )

    # Create link request
    link = Link(
        consumer_id=consumer.id,
        supplier_id=request.supplier_id,
        status=LinkStatus.PENDING,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)

    # Create notification for consumer when link request is created
    # Get supplier name for the notification message
    result = await db.execute(
        select(Supplier).where(Supplier.id == request.supplier_id)
    )
    supplier = result.scalar_one_or_none()
    supplier_name = supplier.company_name if supplier else "Supplier"
    message = f"Your linking request to {supplier_name} has been submitted and is pending approval."
    await create_notification(consumer.user_id, "link_request_created", message, db, entity_id=link.id, entity_type="link")
    await db.commit()

    # Reload link with supplier and consumer (with user) relationships for response convenience
    result = await db.execute(
        select(Link)
        .options(
            selectinload(Link.supplier),
            selectinload(Link.consumer).selectinload(Consumer.user),
        )
        .where(Link.id == link.id)
    )
    link = result.scalar_one()

    return LinkResponse.model_validate(link)


@LinkRouter.patch("/{link_id}/status", response_model=LinkResponse)
async def update_link_status(
    link_id: int,
    status_update: LinkStatusUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> LinkResponse:
    """Update link status (supplier owner/manager/sales can approve/deny, owner/manager can block)."""
    # Check user is supplier staff
    if current_user.role not in (
        Role.SUPPLIER_OWNER.value,
        Role.SUPPLIER_MANAGER.value,
        Role.SUPPLIER_SALES.value,
    ):
        raise ApplicationError("Not enough permissions",
                               )

    # Sales can only approve/deny pending requests, not block
    if (
        current_user.role == Role.SUPPLIER_SALES.value
        and status_update.status == LinkStatus.BLOCKED
    ):
        raise ApplicationError("Sales representatives cannot block links. Only owners and managers can block links.",
                               )

    # Get link with supplier
    result = await db.execute(
        select(Link).options(selectinload(
            Link.supplier)).where(Link.id == link_id)
    )
    link = result.scalar_one_or_none()
    if not link:
        raise ApplicationError("Link not found",
                               )

    # Check user has permission for this supplier
    # For sales, we need to check if they're staff of this supplier
    if current_user.role == Role.SUPPLIER_SALES.value:
        result = await db.execute(
            select(SupplierStaff).where(
                SupplierStaff.user_id == current_user.id,
                SupplierStaff.supplier_id == link.supplier_id,
                SupplierStaff.staff_role == "sales",
            )
        )
        staff = result.scalar_one_or_none()
        has_permission = staff is not None
    else:
        has_permission = await is_supplier_owner_or_manager(
            current_user, link.supplier_id, db
        )

    if not has_permission:
        raise ApplicationError("You do not have permission to manage this supplier's links",
                               )

    # Validate state transition
    _validate_status_transition(link.status, status_update.status)

    # Get consumer user_id for notification (before updating status)
    result = await db.execute(
        select(Consumer).where(Consumer.id == link.consumer_id)
    )
    consumer = result.scalar_one_or_none()
    consumer_user_id = consumer.user_id if consumer else None

    # Store old status for comparison
    old_status = link.status

    # Update status
    link.status = status_update.status
    await db.commit()
    await db.refresh(link)

    # Create notification for consumer when link status changes
    if consumer_user_id and old_status != status_update.status:
        # Get supplier name for the notification message
        result = await db.execute(
            select(Supplier).where(Supplier.id == link.supplier_id)
        )
        supplier = result.scalar_one_or_none()
        supplier_name = supplier.company_name if supplier else "Supplier"

        # Map status to notification message
        status_messages = {
            LinkStatus.ACCEPTED: f"Your linking request to {supplier_name} has been accepted.",
            LinkStatus.DENIED: f"Your linking request to {supplier_name} has been declined.",
            LinkStatus.BLOCKED: f"Your link with {supplier_name} has been blocked.",
            LinkStatus.PENDING: f"Your linking request to {supplier_name} status has been updated to pending.",
            LinkStatus.UNLINKED: f"Your link with {supplier_name} has been unlinked. You can request to link again.",
        }

        notification_types = {
            LinkStatus.ACCEPTED: "link_accepted",
            LinkStatus.DENIED: "link_denied",
            LinkStatus.BLOCKED: "link_blocked",
            LinkStatus.PENDING: "link_status_updated",
            LinkStatus.UNLINKED: "link_unlinked",
        }

        message = status_messages.get(status_update.status)
        notification_type = notification_types.get(status_update.status)

        if message and notification_type:
            if status_update.status == LinkStatus.ACCEPTED:
                # Automatically create chat session for the Consumer-Supplier pair
                # First, check if a chat session already exists for this consumer-supplier pair
                # (1-to-1 relationship: one consumer = one sales rep per supplier)
                result = await db.execute(
                    select(ChatSession).where(
                        ChatSession.consumer_id == link.consumer_id,
                        ChatSession.supplier_id == link.supplier_id,
                    )
                )
                existing_session = result.scalar_one_or_none()

                if not existing_session:
                    # No existing session, assign a sales rep for this supplier (using even distribution)
                    sales_rep_id = await assign_sales_representative(link.supplier_id, db)
                    # Create the chat session
                    chat_session = ChatSession(
                        consumer_id=link.consumer_id,
                        supplier_id=link.supplier_id,
                        sales_rep_id=sales_rep_id,
                    )
                    db.add(chat_session)
                    await db.commit()

            await create_notification(consumer_user_id, notification_type, message, db, entity_id=link.id, entity_type="link")
            await db.commit()

    # Reload link with supplier and consumer (with user) for response
    result = await db.execute(
        select(Link)
        .options(
            selectinload(Link.supplier),
            selectinload(Link.consumer).selectinload(Consumer.user),
        )
        .where(Link.id == link_id)
    )
    link = result.scalar_one()

    return LinkResponse.model_validate(link)


@LinkRouter.get(
    "/incoming", response_model=dict
)  # Will be PaginationResponse[LinkResponse]
async def get_incoming_links(
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=10000, description="Page size"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get incoming link requests for supplier (owner/manager/sales can view)."""
    # Check user is supplier staff
    if current_user.role not in (
        Role.SUPPLIER_OWNER.value,
        Role.SUPPLIER_MANAGER.value,
        Role.SUPPLIER_SALES.value,
    ):
        raise ApplicationError("Not enough permissions",
                               )

    # Get supplier ID for user (owner, manager, or sales)
    supplier_id = await get_supplier_id_for_user(current_user, db)
    if not supplier_id:
        raise ApplicationError("Supplier profile not found")

    # Build query - no status filtering, all links are returned
    query = select(Link).where(Link.supplier_id == supplier_id)

    # Get total count
    count_query = select(func.count(Link.id)).where(
        Link.supplier_id == supplier_id)
    count_result = await db.execute(count_query)
    total = count_result.scalar_one() or 0

    # Get paginated results
    query = query.order_by(Link.created_at.desc()).offset(
        (page - 1) * size).limit(size)
    # ensure supplier and consumer (with user) relationships are loaded
    query = query.options(
        selectinload(Link.supplier),
        selectinload(Link.consumer).selectinload(Consumer.user),
    )
    result = await db.execute(query)
    links = result.scalars().all()

    # Create response
    link_responses = [LinkResponse.model_validate(link) for link in links]
    return create_pagination_response(link_responses, page, size, total).model_dump()


@LinkRouter.get("/{link_id}", response_model=LinkResponse)
async def get_link(
    link_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> LinkResponse:
    """Get a single link (owner/manager or owning consumer)."""
    # Get link with relationships (including consumer.user)
    result = await db.execute(
        select(Link)
        .options(
            selectinload(Link.consumer).selectinload(Consumer.user),
            selectinload(Link.supplier),
        )
        .where(Link.id == link_id)
    )
    link = result.scalar_one_or_none()
    if not link:
        raise ApplicationError("Link not found",
                               )

    # Check access: consumer can only see their own links (by consumer_id, not organization)
    # Each consumer is treated as a unique organization (1 consumer = 1 organization)
    if current_user.role == Role.CONSUMER.value:
        consumer = await get_consumer_by_user_id(current_user.id, db)
        if not consumer:
            raise ApplicationError("Consumer profile not found")
        # Verify the link belongs to this specific consumer (not just same organization)
        if link.consumer_id == consumer.id:
            return LinkResponse.model_validate(link)
        else:
            raise ApplicationError(
                "You do not have permission to view this link")

    # Check access: supplier owner/manager can see their supplier's links
    if current_user.role in (
        Role.SUPPLIER_OWNER.value,
        Role.SUPPLIER_MANAGER.value,
    ):
        has_permission = await is_supplier_owner_or_manager(
            current_user, link.supplier_id, db
        )
        if has_permission:
            return LinkResponse.model_validate(link)

    raise ApplicationError("You do not have permission to view this link")


# Will be PaginationResponse[LinkResponse]
@LinkRouter.get("", response_model=dict)
async def get_consumer_links(
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    status_filter: LinkStatus | None = Query(
        None, description="Filter by status", alias="status"
    ),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get consumer's own links with pagination (consumer only).

    Filters by specific consumer_id (not by organization).
    Each consumer is treated as a unique organization (1 consumer = 1 organization).
    """
    # Check user is consumer
    if current_user.role != Role.CONSUMER.value:
        raise ApplicationError("Not enough permissions",
                               )

    # Get consumer
    consumer = await get_consumer_by_user_id(current_user.id, db)
    if not consumer:
        raise ApplicationError("Consumer profile not found",
                               )

    # Build query - filter by specific consumer_id (each consumer is a unique organization)
    query = select(Link).where(Link.consumer_id == consumer.id)
    if status_filter:
        query = query.where(Link.status == status_filter)

    # Get total count
    count_query = select(func.count(Link.id)).where(
        Link.consumer_id == consumer.id)
    if status_filter:
        count_query = count_query.where(Link.status == status_filter)
    count_result = await db.execute(count_query)
    total = count_result.scalar_one() or 0

    # Get paginated results
    query = query.order_by(Link.created_at.desc()).offset(
        (page - 1) * size).limit(size)
    query = query.options(
        selectinload(Link.supplier),
        selectinload(Link.consumer).selectinload(Consumer.user),
    )
    result = await db.execute(query)
    links = result.scalars().all()

    # Create response
    link_responses = [LinkResponse.model_validate(link) for link in links]
    return create_pagination_response(link_responses, page, size, total).model_dump()
