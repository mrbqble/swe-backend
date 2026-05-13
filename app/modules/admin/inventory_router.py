"""Admin: inventory management routes."""

import csv
import io
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_admin
from app.core.exceptions import ApplicationError
from app.db.session import get_db
from app.modules.admin.model import AdminAction, AdminUser
from app.modules.cart.model import CartItem
from app.modules.product.model import Product

AdminInventoryRouter = APIRouter(tags=["admin"])


@AdminInventoryRouter.get("/inventory")
async def list_inventory(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all products with current stock and active reservation count."""
    now = datetime.now(UTC)

    products = (await db.execute(select(Product).order_by(Product.name))).scalars().all()

    # Batch reservation counts
    reservation_result = await db.execute(
        select(CartItem.product_id, func.coalesce(func.sum(CartItem.qty), 0))
        .where(CartItem.reserved_until > now)
        .group_by(CartItem.product_id)
    )
    reservation_map: dict[int, int] = {pid: qty for pid, qty in reservation_result.all()}

    return [
        {
            "id": p.id,
            "sku": p.sku,
            "name": p.name,
            "category": p.category,
            "stock_qty": p.stock_qty,
            "active_reservations": reservation_map.get(p.id, 0),
            "available_qty": max(0, p.stock_qty - reservation_map.get(p.id, 0)),
            "is_active": p.is_active,
            "price": str(p.price),
        }
        for p in products
    ]


@AdminInventoryRouter.patch("/inventory/{product_id}")
async def update_inventory(
    product_id: int,
    body: dict,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Directly adjust stock_qty and/or is_active for a product."""
    product = await db.get(Product, product_id)
    if product is None:
        raise ApplicationError("Product not found.", status_code=404)

    before = {"stock_qty": product.stock_qty, "is_active": product.is_active}
    updated = False

    if "stock_qty" in body:
        try:
            qty = int(body["stock_qty"])
        except (ValueError, TypeError):
            raise ApplicationError("stock_qty must be a non-negative integer.")
        if qty < 0:
            raise ApplicationError("stock_qty cannot be negative.")
        product.stock_qty = qty
        updated = True

    if "is_active" in body:
        product.is_active = bool(body["is_active"])
        updated = True

    if not updated:
        raise ApplicationError("No valid fields provided (stock_qty, is_active).")

    after = {"stock_qty": product.stock_qty, "is_active": product.is_active}

    action = AdminAction(
        admin_id=admin.id,
        action_type="update_inventory",
        target_type="product",
        target_id=product_id,
        before_data=before,
        after_data=after,
        ip=request.client.host if request.client else None,
    )
    db.add(action)
    await db.commit()
    await db.refresh(product)

    return {
        "id": product.id,
        "sku": product.sku,
        "name": product.name,
        "stock_qty": product.stock_qty,
        "is_active": product.is_active,
    }


@AdminInventoryRouter.post("/inventory/import")
async def import_inventory_csv(
    file: UploadFile,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Import stock quantities from CSV (columns: sku, stock_qty). First row is header."""
    if not file.filename or not file.filename.endswith(".csv"):
        raise ApplicationError("File must be a .csv file.")

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")  # handle BOM from Excel
    except UnicodeDecodeError:
        raise ApplicationError("CSV must be UTF-8 encoded.")

    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None or "sku" not in reader.fieldnames or "stock_qty" not in reader.fieldnames:
        raise ApplicationError("CSV must have columns: sku, stock_qty")

    updated = 0
    not_found: list[str] = []
    errors: list[str] = []

    for row_num, row in enumerate(reader, start=2):
        sku = (row.get("sku") or "").strip()
        qty_str = (row.get("stock_qty") or "").strip()

        if not sku:
            errors.append(f"Row {row_num}: empty sku")
            continue

        try:
            qty = int(qty_str)
            if qty < 0:
                raise ValueError
        except (ValueError, TypeError):
            errors.append(f"Row {row_num}: invalid stock_qty '{qty_str}' for sku '{sku}'")
            continue

        result = await db.execute(select(Product).where(Product.sku == sku))
        product = result.scalar_one_or_none()

        if product is None:
            not_found.append(sku)
            continue

        product.stock_qty = qty
        updated += 1

    action = AdminAction(
        admin_id=admin.id,
        action_type="csv_import_inventory",
        target_type="product",
        target_id=None,
        after_data={"updated": updated, "not_found": not_found, "errors": errors},
        ip=request.client.host if request.client else None,
    )
    db.add(action)
    await db.commit()

    return {"updated": updated, "not_found": not_found, "errors": errors}
