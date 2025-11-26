"""Product management routes."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user
from app.core.exceptions import ApplicationError
from app.core.roles import Role
from app.db.session import get_db
from app.modules.product.model import Product
from app.modules.product.schema import ProductCreate, ProductResponse, ProductUpdate
from app.modules.supplier.model import SupplierStaff
from app.modules.user.model import User
from app.utils.helpers import (
    get_supplier_by_user_id,
    get_supplier_id_for_user,
    is_supplier_owner_or_manager,
)
from app.utils.pagination import create_pagination_response

ProductRouter = APIRouter(prefix="/products", tags=["products"])


# Use the helper function from utils instead of local function


@ProductRouter.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product",
    description="Create a new product for the authenticated supplier. SKU must be unique per supplier.",
    responses={
        201: {"description": "Product created successfully"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Supplier profile not found"},
        409: {"description": "Product with this SKU already exists"},
    },
)
async def create_product(
    product_data: ProductCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """
    Create a product (supplier owner/manager only).

    **Role Requirements:** supplier_owner, supplier_manager

    **Required Scopes:** write:own_products
    """
    # Check user is supplier owner or manager
    if current_user.role not in (
        Role.SUPPLIER_OWNER.value,
        Role.SUPPLIER_MANAGER.value,
    ):
        raise ApplicationError("Not enough permissions")

    # Get supplier ID for user
    supplier_id = await get_supplier_id_for_user(current_user, db)
    if not supplier_id:
        raise ApplicationError("Supplier profile not found")

    # Check if SKU already exists for this supplier
    result = await db.execute(
        select(Product).where(
            Product.supplier_id == supplier_id,
            Product.sku == product_data.sku,
        )
    )
    existing_product = result.scalar_one_or_none()
    if existing_product:
        raise ApplicationError("Product with this SKU already exists")

    # Create product
    product = Product(
        supplier_id=supplier_id,
        name=product_data.name,
        description=product_data.description,
        price_kzt=product_data.price_kzt,
        currency=product_data.currency,
        sku=product_data.sku,
        stock_qty=product_data.stock_qty,
        unit=product_data.unit,
        min_order_qty=product_data.min_order_qty,
        discount_percent=product_data.discount_percent,
        delivery_available=product_data.delivery_available,
        pickup_available=product_data.pickup_available,
        lead_time_days=product_data.lead_time_days,
        is_active=product_data.is_active,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    return ProductResponse.model_validate(product)


@ProductRouter.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Update a product (supplier owner/manager only)."""
    # Check user is supplier owner or manager
    if current_user.role not in (
        Role.SUPPLIER_OWNER.value,
        Role.SUPPLIER_MANAGER.value,
    ):
        raise ApplicationError("Not enough permissions")

    # Get product
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise ApplicationError("Product not found")

    # Check user has permission for this supplier
    has_permission = await is_supplier_owner_or_manager(
        current_user, product.supplier_id, db
    )
    if not has_permission:
        raise ApplicationError("You do not have permission to manage this supplier's products")

    # Check SKU uniqueness if SKU is being updated
    if product_data.sku and product_data.sku != product.sku:
        result = await db.execute(
            select(Product).where(
                Product.supplier_id == product.supplier_id,
                Product.sku == product_data.sku,
                Product.id != product_id,
            )
        )
        existing_product = result.scalar_one_or_none()
        if existing_product:
            raise ApplicationError("Product with this SKU already exists")

    # Update product fields
    update_data = product_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)

    return ProductResponse.model_validate(product)


@ProductRouter.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a product (supplier owner/manager only)."""
    # Check user is supplier owner or manager
    if current_user.role not in (
        Role.SUPPLIER_OWNER.value,
        Role.SUPPLIER_MANAGER.value,
    ):
        raise ApplicationError("Not enough permissions")

    # Get product
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise ApplicationError("Product not found")

    # Check user has permission for this supplier
    has_permission = await is_supplier_owner_or_manager(
        current_user, product.supplier_id, db
    )
    if not has_permission:
        raise ApplicationError("You do not have permission to manage this supplier's products")

    # Delete product
    await db.delete(product)
    await db.commit()


@ProductRouter.get(
    "",
    response_model=dict,  # PaginationResponse[ProductResponse]
    summary="List products",
    description="Get paginated list of products with optional filters. Public endpoint (no authentication required).",
    responses={
        200: {"description": "Products retrieved successfully"},
    },
)
async def get_products(
    supplier_id: int | None = Query(None, description="Filter by supplier ID"),
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    size: int = Query(20, ge=1, le=100, description="Page size (max 100)"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get products with optional supplier filter.

    **Role Requirements:** None (public endpoint)

    **Pagination:** Results are paginated with max page size of 100.
    """
    # Build query
    query = select(Product)
    if supplier_id:
        query = query.where(Product.supplier_id == supplier_id)
    if is_active is not None:
        query = query.where(Product.is_active == is_active)

    # Get total count
    count_query = select(func.count(Product.id))
    if supplier_id:
        count_query = count_query.where(Product.supplier_id == supplier_id)
    if is_active is not None:
        count_query = count_query.where(Product.is_active == is_active)
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


@ProductRouter.get(
    "/me",
    response_model=dict,  # PaginationResponse[ProductResponse]
    summary="Get my products",
    description="Get paginated list of products for the authenticated supplier (owner/manager only).",
    responses={
        200: {"description": "Products retrieved successfully"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Supplier profile not found"},
    },
)
async def get_my_products(
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    size: int = Query(20, ge=1, le=100, description="Page size (max 100)"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get products for the authenticated supplier.

    **Role Requirements:** supplier_owner, supplier_manager

    **Pagination:** Results are paginated with max page size of 100.
    """
    # Check user is supplier owner or manager
    if current_user.role not in (
        Role.SUPPLIER_OWNER.value,
        Role.SUPPLIER_MANAGER.value,
    ):
        raise ApplicationError("Not enough permissions")

    # Get supplier ID for user
    supplier_id = await get_supplier_id_for_user(current_user, db)
    if not supplier_id:
        raise ApplicationError("Supplier profile not found")

    # Build query for this supplier's products
    query = select(Product).where(Product.supplier_id == supplier_id)
    if is_active is not None:
        query = query.where(Product.is_active == is_active)

    # Get total count
    count_query = select(func.count(Product.id)).where(
        Product.supplier_id == supplier_id
    )
    if is_active is not None:
        count_query = count_query.where(Product.is_active == is_active)
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


@ProductRouter.get(
    "/{product_id}",
    response_model=dict,
    summary="Get product by ID",
    description="Get a single product by its ID. Public endpoint (no authentication required).",
    responses={
        200: {"description": "Product retrieved successfully"},
        404: {"description": "Product not found"},
    },
)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get a single product by ID.

    **Role Requirements:** None (public endpoint)
    """
    # Get product with supplier relationship loaded
    result = await db.execute(
        select(Product)
        .options(selectinload(Product.supplier))
        .where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise ApplicationError("Product not found")

    # Convert to response and include supplier info if available
    product_dict = ProductResponse.model_validate(product).model_dump()
    if product.supplier:
        product_dict["supplier"] = {
            "id": product.supplier.id,
            "company_name": product.supplier.company_name,
            "name": product.supplier.company_name,
        }

    return product_dict
