"""API helper functions."""

from typing import Any
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.roles import Role
from app.modules.consumer.model import Consumer
from app.modules.supplier.model import Supplier, SupplierStaff
from app.modules.user.model import User


async def get_user_by_email(email: str, db: AsyncSession) -> User | None:
    """Get user by email address."""
    result = await db.execute(select(User).where(User.email == email))
    print(result)
    return result.scalar_one_or_none()


async def get_user_by_id(user_id: int, db: AsyncSession) -> User | None:
    """Get user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_consumer_by_user_id(user_id: int, db: AsyncSession) -> Consumer | None:
    """Get consumer by user ID."""
    result = await db.execute(select(Consumer).where(Consumer.user_id == user_id))
    return result.scalar_one_or_none()


async def get_supplier_by_user_id(user_id: int, db: AsyncSession) -> Supplier | None:
    """Get supplier by user ID (for supplier owner)."""
    result = await db.execute(select(Supplier).where(Supplier.user_id == user_id))
    return result.scalar_one_or_none()


async def get_supplier_id_for_user(user: User, db: AsyncSession) -> int | None:
    """
    Get supplier ID for any supplier staff member (owner, manager, or sales rep).

    Returns:
        Supplier ID if user is associated with a supplier, None otherwise.
    """
    # Check if user is supplier owner
    supplier = await get_supplier_by_user_id(user.id, db)
    if supplier:
        return supplier.id

    # Check if user is staff (manager or sales) via SupplierStaff
    # Handle both API format ("sales", "manager") and seed format ("Sales Representative", "Operations Manager")
    result = await db.execute(
        select(SupplierStaff).where(
            SupplierStaff.user_id == user.id,
        )
    )
    staff_list = result.scalars().all()

    # Check if any staff record matches (case-insensitive check for role keywords)
    for staff in staff_list:
        staff_role_lower = staff.staff_role.lower()
        # Check for sales (matches "sales", "Sales Representative", "Senior Sales Representative", etc.)
        if "sales" in staff_role_lower:
            return staff.supplier_id
        # Check for manager (matches "manager", "Operations Manager", "Sales Manager", etc.)
        if "manager" in staff_role_lower:
            return staff.supplier_id
        # Check for owner
        if "owner" in staff_role_lower:
            return staff.supplier_id

    return None


async def is_supplier_owner_or_manager(
    user: User, supplier_id: int, db: AsyncSession
) -> bool:
    """Check if user is owner or manager of the supplier."""
    # Check if user is supplier owner
    supplier = await get_supplier_by_user_id(user.id, db)
    if supplier and supplier.id == supplier_id:
        return True

    # Check if user is supplier manager
    if user.role == Role.SUPPLIER_MANAGER.value:
        result = await db.execute(
            select(SupplierStaff).where(
                SupplierStaff.user_id == user.id,
                SupplierStaff.supplier_id == supplier_id,
                SupplierStaff.staff_role.in_(["manager", "owner"]),
            )
        )
        staff = result.scalar_one_or_none()
        if staff:
            return True

    return False


async def assign_sales_representative(
    supplier_id: int, db: AsyncSession
) -> int:
    """
    Assign a sales representative to a supplier with even distribution.

    Strategy:
    1. Get all active sales representatives for this supplier
    2. Count orders assigned to each sales rep
    3. Assign to the sales rep with the least orders
    4. If all have equal orders, assign randomly

    Returns:
        User ID of the assigned sales representative

    Raises:
        ApplicationError: If no sales representative can be found
    """
    import random
    from app.core.exceptions import ApplicationError

    # Get all active sales reps for this supplier
    result = await db.execute(
        select(SupplierStaff)
        .join(User, SupplierStaff.user_id == User.id)
        .where(SupplierStaff.supplier_id == supplier_id)
        .where(SupplierStaff.staff_role.ilike("%sales%"))
        .where(User.is_active)
    )
    sales_reps = result.scalars().all()

    if not sales_reps:
        # If no sales rep found, try to get any active staff member
        result = await db.execute(
            select(SupplierStaff)
            .join(User, SupplierStaff.user_id == User.id)
            .where(SupplierStaff.supplier_id == supplier_id)
            .where(User.is_active)
        )
        sales_reps = result.scalars().all()

    if not sales_reps:
        # Last resort: try to get the supplier owner
        result = await db.execute(
            select(Supplier)
            .join(User, Supplier.user_id == User.id)
            .where(Supplier.id == supplier_id)
            .where(User.is_active)
        )
        supplier = result.scalar_one_or_none()
        if supplier and supplier.user_id:
            return supplier.user_id
        raise ApplicationError(
            "No sales representative found for this supplier. Please contact support."
        )

    # Count assignments for each sales rep (only for this supplier)
    # For consumer assignment: count ChatSessions (consumers assigned to each sales rep)
    # For order assignment: count Orders (orders assigned to each sales rep)
    from app.modules.chat.model import ChatSession
    from app.modules.link.model import Link, LinkStatus

    sales_rep_counts: dict[int, int] = {}
    for sales_rep_staff in sales_reps:
        user_id = sales_rep_staff.user_id

        # Count ChatSessions (consumer assignments) for this sales rep and supplier
        # A ChatSession represents a consumer-sales_rep assignment for a supplier
        # We count distinct consumers (via ChatSession) assigned to this sales rep
        # where the consumer has an accepted link with this supplier
        count_result = await db.execute(
            select(func.count(func.distinct(ChatSession.consumer_id)))
            .select_from(ChatSession)
            .join(Consumer, ChatSession.consumer_id == Consumer.id)
            .join(Link, (Link.consumer_id == Consumer.id) & (Link.supplier_id == supplier_id))
            .where(ChatSession.sales_rep_id == user_id)
            .where(Link.status == LinkStatus.ACCEPTED)
        )
        consumer_count = count_result.scalar_one() or 0
        sales_rep_counts[user_id] = consumer_count

    # Find sales rep with minimum consumer assignment count
    min_count = min(sales_rep_counts.values())
    candidates = [
        user_id
        for user_id, count in sales_rep_counts.items()
        if count == min_count
    ]

    # If all have equal assignments, assign randomly; otherwise assign to the one with least
    selected_user_id = random.choice(candidates)

    return selected_user_id


async def create_notification(
    recipient_id: int,
    notification_type: str,
    message: str,
    db: AsyncSession,
    entity_id: int | None = None,
    entity_type: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """
    Create a notification for a user.

    Args:
        recipient_id: User ID of the notification recipient
        notification_type: Type of notification (e.g., 'link_accepted', 'order_accepted')
        message: Notification message text
        db: Database session
        entity_id: ID of the related entity (order_id, complaint_id, session_id, etc.)
        entity_type: Type of entity ('order', 'complaint', 'chat_session', etc.)
        metadata: Additional metadata dictionary (e.g., {'message_id': 123} for chat notifications)
    """
    from app.modules.notification.model import Notification

    notification = Notification(
        recipient_id=recipient_id,
        type=notification_type,
        message=message,
        entity_id=entity_id,
        entity_type=entity_type,
        notification_metadata=metadata,
        is_read=False,
    )
    db.add(notification)
    # Note: Don't commit here - let the caller commit after their transaction
