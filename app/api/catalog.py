"""Catalog routes for consumers."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.constants import ErrorMessages
from app.core.roles import Role
from app.db.session import get_db
from app.modules.link.model import Link, LinkStatus
from app.modules.product.model import Product
from app.modules.product.schema import ProductResponse
from app.modules.supplier.model import Supplier
from app.modules.supplier.schema import SupplierResponse
from app.modules.user.model import User
from app.utils.helpers import get_consumer_by_user_id
from app.utils.pagination import create_pagination_response

CatalogueRouter = APIRouter(prefix="/catalog", tags=["catalog"])


@CatalogueRouter.get(
    "", response_model=dict
)  # Will be PaginationResponse[ProductResponse]
async def get_catalog(
    current_user: Annotated[User, Depends(get_current_user)],
    supplier_id: int = Query(..., description="Supplier ID"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get catalog for a supplier (consumer only, requires accepted link)."""
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
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
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
            Link.supplier_id == supplier_id,
            Link.status == LinkStatus.ACCEPTED,
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have an accepted link with this supplier",
        )

    # Get active products for this supplier
    query = select(Product).where(
        Product.supplier_id == supplier_id,
        Product.is_active == True,  # noqa: E712
    )

    # Get total count
    count_query = select(func.count(Product.id)).where(
        Product.supplier_id == supplier_id,
        Product.is_active == True,  # noqa: E712
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar_one() or 0

    # Get paginated results
    query = (
        query.order_by(Product.created_at.desc()).offset((page - 1) * size).limit(size)
    )
    result = await db.execute(query)
    products = result.scalars().all()

    # Create response
    product_responses = [
        ProductResponse.model_validate(product) for product in products
    ]
    return create_pagination_response(product_responses, page, size, total).model_dump()


@CatalogueRouter.get(
    "/suppliers",
    response_model=dict,
    summary="List suppliers",
    description="List supplier companies (paginated). Supports optional search query 'q'.",
)
async def list_suppliers(
    q: str | None = Query(None, description="Search query for company name"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List suppliers (public). Returns paginated supplier objects."""
    query = select(Supplier)
    if q:
        query = query.where(Supplier.company_name.ilike(f"%{q}%"))

    # total count
    count_query = select(func.count(Supplier.id))
    if q:
        count_query = count_query.where(Supplier.company_name.ilike(f"%{q}%"))
    count_result = await db.execute(count_query)
    total = count_result.scalar_one() or 0

    # paginated
    query = query.order_by(Supplier.company_name.asc()).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    suppliers = result.scalars().all()

    supplier_responses = [SupplierResponse.model_validate(s) for s in suppliers]
    return create_pagination_response(supplier_responses, page, size, total).model_dump()
