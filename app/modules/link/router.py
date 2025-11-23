"""Link management routes."""

from typing import Annotated, Any

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user
from app.core.constants import ErrorMessages
from app.core.roles import Role
from app.db.session import get_db
from app.modules.link.model import Link, LinkStatus
from app.modules.link.schema import LinkRequestCreate, LinkResponse, LinkStatusUpdate
from app.modules.supplier.model import Supplier, SupplierStaff
from app.modules.user.model import User
from app.utils.helpers import (
    get_consumer_by_user_id,
    get_supplier_by_user_id,
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
        LinkStatus.ACCEPTED: {LinkStatus.BLOCKED},
        LinkStatus.DENIED: {LinkStatus.PENDING},
        LinkStatus.BLOCKED: set[Any](),  # Blocked links cannot be changed
    }

    allowed = valid_transitions.get(current_status, set[LinkStatus]())
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from {current_status.value} to {new_status.value}",
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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ErrorMessages.NOT_ENOUGH_PERMISSIONS,
        )

    # Get consumer
    consumer = await get_consumer_by_user_id(current_user.id, db)
    # Debug logging to help diagnose missing consumer profiles during integration
    try:
        logger.info(
            "create_link_request: user_id=%s role=%s consumer_found=%s",
            current_user.id,
            current_user.role,
            bool(consumer),
        )
    except Exception:
        # Avoid failing the request because logging failed
        pass
    if not consumer:
        logger.warning(
            "Consumer profile not found for user_id=%s when creating link request",
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consumer profile not found",
        )

    # Check supplier exists
    result = await db.execute(
        select(Supplier).where(Supplier.id == request.supplier_id)
    )
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier not found",
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
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Link request already exists",
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

    # Reload link with supplier relationship for response convenience
    result = await db.execute(
        select(Link).options(selectinload(Link.supplier), selectinload(Link.consumer)).where(Link.id == link.id)
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
    """Update link status (supplier owner/manager only)."""
    # Check user is supplier owner or manager
    if current_user.role not in (
        Role.SUPPLIER_OWNER.value,
        Role.SUPPLIER_MANAGER.value,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ErrorMessages.NOT_ENOUGH_PERMISSIONS,
        )

    # Get link with supplier
    result = await db.execute(
        select(Link).options(selectinload(Link.supplier)).where(Link.id == link_id)
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found",
        )

    # Check user has permission for this supplier
    has_permission = await is_supplier_owner_or_manager(
        current_user, link.supplier_id, db
    )
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage this supplier's links",
        )

    # Validate state transition
    _validate_status_transition(link.status, status_update.status)

    # Update status
    link.status = status_update.status
    await db.commit()
    await db.refresh(link)

    # Reload link with supplier
    result = await db.execute(
        select(Link).options(selectinload(Link.supplier)).where(Link.id == link_id)
    )
    link = result.scalar_one()

    return LinkResponse.model_validate(link)


@LinkRouter.get(
    "/incoming", response_model=dict
)  # Will be PaginationResponse[LinkResponse]
async def get_incoming_links(
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    status_filter: LinkStatus | None = Query(
        None, description="Filter by status", alias="status"
    ),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get incoming link requests for supplier (owner/manager only)."""
    # Check user is supplier owner or manager
    if current_user.role not in (
        Role.SUPPLIER_OWNER.value,
        Role.SUPPLIER_MANAGER.value,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ErrorMessages.NOT_ENOUGH_PERMISSIONS,
        )

    # Get supplier
    supplier = await get_supplier_by_user_id(current_user.id, db)
    if not supplier:
        # Check if user is manager via SupplierStaff
        result = await db.execute(
            select(SupplierStaff).where(
                SupplierStaff.user_id == current_user.id,
                SupplierStaff.staff_role.in_(["manager", "owner"]),
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

    # Build query
    query = select(Link).where(Link.supplier_id == supplier_id)
    if status_filter:
        query = query.where(Link.status == status_filter)

    # Get total count
    count_query = select(func.count(Link.id)).where(Link.supplier_id == supplier_id)
    if status_filter:
        count_query = count_query.where(Link.status == status_filter)
    count_result = await db.execute(count_query)
    total = count_result.scalar_one() or 0

    # Get paginated results
    query = query.order_by(Link.created_at.desc()).offset((page - 1) * size).limit(size)
    # ensure supplier and consumer relationships are loaded
    query = query.options(selectinload(Link.supplier), selectinload(Link.consumer))
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
    # Get link with relationships
    result = await db.execute(
        select(Link)
        .options(selectinload(Link.consumer), selectinload(Link.supplier))
        .where(Link.id == link_id)
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found",
        )

    # Check access: consumer can see their own links
    if current_user.role == Role.CONSUMER.value:
        consumer = await get_consumer_by_user_id(current_user.id, db)
        if consumer and link.consumer_id == consumer.id:
            return LinkResponse.model_validate(link)

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

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to view this link",
    )


@LinkRouter.get("", response_model=dict)  # Will be PaginationResponse[LinkResponse]
async def get_consumer_links(
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    status_filter: LinkStatus | None = Query(
        None, description="Filter by status", alias="status"
    ),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get consumer's own links with pagination (consumer only)."""
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

    # Build query
    query = select(Link).where(Link.consumer_id == consumer.id)
    if status_filter:
        query = query.where(Link.status == status_filter)

    # Get total count
    count_query = select(func.count(Link.id)).where(Link.consumer_id == consumer.id)
    if status_filter:
        count_query = count_query.where(Link.status == status_filter)
    count_result = await db.execute(count_query)
    total = count_result.scalar_one() or 0

    # Get paginated results
    query = query.order_by(Link.created_at.desc()).offset((page - 1) * size).limit(size)
    query = query.options(selectinload(Link.supplier), selectinload(Link.consumer))
    result = await db.execute(query)
    links = result.scalars().all()

    # Create response
    link_responses = [LinkResponse.model_validate(link) for link in links]
    return create_pagination_response(link_responses, page, size, total).model_dump()
