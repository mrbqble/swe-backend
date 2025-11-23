"""Seed products table."""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.product.model import Product
from app.modules.supplier.model import Supplier


async def seed_products(
    session: AsyncSession, suppliers: dict[str, Supplier]
) -> dict[str, Product]:
    """
    Seed products table.

    Args:
        session: Database session
        suppliers: Dictionary of suppliers keyed by company name

    Returns:
        Dictionary mapping product name to Product object for use in other seed scripts.
    """
    # Get existing products
    result = await session.execute(select(Product))
    existing_products = {product.name: product for product in result.scalars().all()}

    # Validate required suppliers exist
    required_supplier_names = [
        "Tech Supplies Co.",
        "Global Merchandise Ltd.",
        "Premium Products Inc.",
    ]
    for name in required_supplier_names:
        if name not in suppliers:
            raise ValueError(
                f"Required supplier {name} not found. Please run seed_suppliers first."
            )

    products_data = [
        # Products for Tech Supplies Co.
        {
            "supplier": suppliers["Tech Supplies Co."],
            "name": "Laptop Computer",
            "description": "High-performance laptop with 16GB RAM and 512GB SSD",
            "price_kzt": Decimal("450000.00"),
            "currency": "KZT",
            "sku": "TSC-LAP-001",
            "stock_qty": 50,
            "is_active": True,
        },
        {
            "supplier": suppliers["Tech Supplies Co."],
            "name": "Wireless Mouse",
            "description": "Ergonomic wireless mouse with long battery life",
            "price_kzt": Decimal("15000.00"),
            "currency": "KZT",
            "sku": "TSC-MOU-001",
            "stock_qty": 200,
            "is_active": True,
        },
        {
            "supplier": suppliers["Tech Supplies Co."],
            "name": "Mechanical Keyboard",
            "description": "RGB backlit mechanical keyboard with blue switches",
            "price_kzt": Decimal("35000.00"),
            "currency": "KZT",
            "sku": "TSC-KEY-001",
            "stock_qty": 100,
            "is_active": True,
        },
        {
            "supplier": suppliers["Tech Supplies Co."],
            "name": "USB-C Hub",
            "description": "Multi-port USB-C hub with HDMI, USB 3.0, and card reader",
            "price_kzt": Decimal("25000.00"),
            "currency": "KZT",
            "sku": "TSC-HUB-001",
            "stock_qty": 150,
            "is_active": True,
        },
        # Products for Global Merchandise Ltd.
        {
            "supplier": suppliers["Global Merchandise Ltd."],
            "name": "Office Chair",
            "description": "Ergonomic office chair with lumbar support",
            "price_kzt": Decimal("75000.00"),
            "currency": "KZT",
            "sku": "GML-CHA-001",
            "stock_qty": 80,
            "is_active": True,
        },
        {
            "supplier": suppliers["Global Merchandise Ltd."],
            "name": "Desk Lamp",
            "description": "LED desk lamp with adjustable brightness",
            "price_kzt": Decimal("12000.00"),
            "currency": "KZT",
            "sku": "GML-LAM-001",
            "stock_qty": 300,
            "is_active": True,
        },
        {
            "supplier": suppliers["Global Merchandise Ltd."],
            "name": "File Organizer",
            "description": "Desktop file organizer with multiple compartments",
            "price_kzt": Decimal("8000.00"),
            "currency": "KZT",
            "sku": "GML-FIL-001",
            "stock_qty": 250,
            "is_active": True,
        },
        # Products for Premium Products Inc.
        {
            "supplier": suppliers["Premium Products Inc."],
            "name": "Standing Desk",
            "description": "Electric height-adjustable standing desk",
            "price_kzt": Decimal("250000.00"),
            "currency": "KZT",
            "sku": "PPI-DES-001",
            "stock_qty": 30,
            "is_active": True,
        },
        {
            "supplier": suppliers["Premium Products Inc."],
            "name": "Monitor Stand",
            "description": "Dual monitor stand with cable management",
            "price_kzt": Decimal("45000.00"),
            "currency": "KZT",
            "sku": "PPI-MON-001",
            "stock_qty": 60,
            "is_active": True,
        },
        {
            "supplier": suppliers["Premium Products Inc."],
            "name": "Noise-Cancelling Headphones",
            "description": "Wireless noise-cancelling headphones with 30h battery",
            "price_kzt": Decimal("95000.00"),
            "currency": "KZT",
            "sku": "PPI-HEA-001",
            "stock_qty": 40,
            "is_active": True,
        },
        # Inactive product for testing
        {
            "supplier": suppliers["Tech Supplies Co."],
            "name": "Discontinued Product",
            "description": "This product is no longer available",
            "price_kzt": Decimal("10000.00"),
            "currency": "KZT",
            "sku": "TSC-DIS-001",
            "stock_qty": 0,
            "is_active": False,
        },
    ]

    products = []
    created_count = 0
    for product_data in products_data:
        product_name = product_data["name"]
        if product_name in existing_products:
            # Product already exists, use it
            products.append(existing_products[product_name])
        else:
            # Create new product
            supplier = product_data["supplier"]
            assert isinstance(supplier, Supplier), (
                f"Expected Supplier, got {type(supplier)}"
            )
            product = Product(
                supplier_id=supplier.id,
                name=product_name,
                description=product_data["description"],
                price_kzt=product_data["price_kzt"],
                currency=product_data["currency"],
                sku=product_data["sku"],
                stock_qty=product_data["stock_qty"],
                is_active=product_data["is_active"],
                created_at=datetime.now(UTC),
            )
            session.add(product)
            products.append(product)
            created_count += 1

    if created_count > 0:
        await session.flush()
        await session.commit()
        print(
            f"✅ Created {created_count} new products (total: {len(products)} products available)"
        )
    else:
        print(
            f"✅ All required products already exist ({len(products)} products available)"
        )

    return {product.name: product for product in products}


if __name__ == "__main__":
    from app.db.session import AsyncSessionLocal
    from scripts.seed.seed_suppliers import seed_suppliers
    from scripts.seed.seed_users import seed_users

    async def main():
        async with AsyncSessionLocal() as session:
            users = await seed_users(session)
            suppliers = await seed_suppliers(session, users)
            await seed_products(session, suppliers)

    asyncio.run(main())
