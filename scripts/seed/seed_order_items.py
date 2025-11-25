"""Seed order_items table."""

import asyncio
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.order.model import Order, OrderItem
from app.modules.product.model import Product


async def seed_order_items(
    session: AsyncSession,
    orders: list[Order],
    products: dict[str, Product],
) -> list[OrderItem]:
    """
    Seed order_items table.

    Args:
        session: Database session
        orders: List of Order objects
        products: Dictionary of products keyed by product name

    Returns:
        List of OrderItem objects.
    """
    # Get existing order items
    result = await session.execute(select(OrderItem))
    existing_items = result.scalars().all()

    # Validate we have enough orders and products
    if len(orders) < 10:
        raise ValueError(
            f"Need at least 10 orders, but only {len(orders)} found. Please run seed_orders first."
        )

    required_product_names = [
        "Laptop Computer",
        "Wireless Mouse",
        "Mechanical Keyboard",
        "USB-C Hub",
        "Office Chair",
        "Desk Lamp",
        "File Organizer",
        "Standing Desk",
        "Monitor Stand",
        "Noise-Cancelling Headphones",
    ]
    for name in required_product_names:
        if name not in products:
            raise ValueError(
                f"Required product {name} not found. Please run seed_products first."
            )

    # If we already have many order items, assume seeding is done
    if len(existing_items) >= 24:  # We create 24 order items
        print(
            f"⚠️  Order items already exist ({len(existing_items)} items), skipping seed_order_items"
        )
        return existing_items

    # Map orders by index for easier reference
    # Order 0: Pending order from Retail Chain ABC to Tech Supplies Co.
    # Order 1: Accepted order from Retail Chain ABC to Tech Supplies Co.
    # Order 2: In Progress order from Wholesale Distributor XYZ to Tech Supplies Co.
    # Order 3: Completed order from Retail Chain ABC to Global Merchandise Ltd.
    # Order 4: Accepted order from Supermarket Network 123 to Global Merchandise Ltd.
    # Order 5: Completed order from Wholesale Distributor XYZ to Premium Products Inc.
    # Order 6: Rejected order from Wholesale Distributor XYZ to Premium Products Inc.
    # Order 7: Accepted order from Corporate Buyers Alliance to Industrial Equipment Solutions
    # Order 8: In Progress order from Retail Outlet Network to Office Essentials Pro
    # Order 9: Completed order from Bulk Purchase Consortium to Digital Devices Direct

    order_items_data = [
        # Order 0: Pending order
        {
            "order": orders[0],
            "product": products["Laptop Computer"],
            "qty": 1,
            "unit_price_kzt": Decimal("450000.00"),
        },
        {
            "order": orders[0],
            "product": products["Wireless Mouse"],
            "qty": 2,
            "unit_price_kzt": Decimal("15000.00"),
        },
        # Order 1: Accepted order
        {
            "order": orders[1],
            "product": products["Laptop Computer"],
            "qty": 1,
            "unit_price_kzt": Decimal("450000.00"),
        },
        {
            "order": orders[1],
            "product": products["Mechanical Keyboard"],
            "qty": 2,
            "unit_price_kzt": Decimal("35000.00"),
        },
        {
            "order": orders[1],
            "product": products["USB-C Hub"],
            "qty": 3,
            "unit_price_kzt": Decimal("25000.00"),
        },
        # Order 2: In Progress order
        {
            "order": orders[2],
            "product": products["Laptop Computer"],
            "qty": 2,
            "unit_price_kzt": Decimal("450000.00"),
        },
        {
            "order": orders[2],
            "product": products["Mechanical Keyboard"],
            "qty": 5,
            "unit_price_kzt": Decimal("35000.00"),
        },
        {
            "order": orders[2],
            "product": products["USB-C Hub"],
            "qty": 4,
            "unit_price_kzt": Decimal("25000.00"),
        },
        # Order 3: Completed order
        {
            "order": orders[3],
            "product": products["Office Chair"],
            "qty": 1,
            "unit_price_kzt": Decimal("75000.00"),
        },
        {
            "order": orders[3],
            "product": products["Desk Lamp"],
            "qty": 1,
            "unit_price_kzt": Decimal("12000.00"),
        },
        {
            "order": orders[3],
            "product": products["File Organizer"],
            "qty": 1,
            "unit_price_kzt": Decimal("8000.00"),
        },
        # Order 4: Accepted order
        {
            "order": orders[4],
            "product": products["Office Chair"],
            "qty": 1,
            "unit_price_kzt": Decimal("75000.00"),
        },
        {
            "order": orders[4],
            "product": products["Desk Lamp"],
            "qty": 2,
            "unit_price_kzt": Decimal("12000.00"),
        },
        {
            "order": orders[4],
            "product": products["File Organizer"],
            "qty": 1,
            "unit_price_kzt": Decimal("8000.00"),
        },
        # Order 5: Completed order
        {
            "order": orders[5],
            "product": products["Monitor Stand"],
            "qty": 2,
            "unit_price_kzt": Decimal("45000.00"),
        },
        {
            "order": orders[5],
            "product": products["Noise-Cancelling Headphones"],
            "qty": 3,
            "unit_price_kzt": Decimal("95000.00"),
        },
        {
            "order": orders[5],
            "product": products["Standing Desk"],
            "qty": 1,
            "unit_price_kzt": Decimal("250000.00"),
        },
        # Order 6: Rejected order
        {
            "order": orders[6],
            "product": products["Standing Desk"],
            "qty": 1,
            "unit_price_kzt": Decimal("250000.00"),
        },
        # Order 7: Accepted order
        {
            "order": orders[7],
            "product": products["Laptop Computer"],
            "qty": 1,
            "unit_price_kzt": Decimal("450000.00"),
        },
        {
            "order": orders[7],
            "product": products["Mechanical Keyboard"],
            "qty": 3,
            "unit_price_kzt": Decimal("35000.00"),
        },
        {
            "order": orders[7],
            "product": products["USB-C Hub"],
            "qty": 2,
            "unit_price_kzt": Decimal("25000.00"),
        },
        # Order 8: In Progress order
        {
            "order": orders[8],
            "product": products["Office Chair"],
            "qty": 2,
            "unit_price_kzt": Decimal("75000.00"),
        },
        {
            "order": orders[8],
            "product": products["Desk Lamp"],
            "qty": 4,
            "unit_price_kzt": Decimal("12000.00"),
        },
        # Order 9: Completed order
        {
            "order": orders[9],
            "product": products["Monitor Stand"],
            "qty": 3,
            "unit_price_kzt": Decimal("45000.00"),
        },
        {
            "order": orders[9],
            "product": products["Noise-Cancelling Headphones"],
            "qty": 5,
            "unit_price_kzt": Decimal("95000.00"),
        },
    ]

    # If we have existing items, use them (up to 24)
    order_items = (
        existing_items[:24] if len(existing_items) >= 24 else existing_items.copy()
    )
    created_count = 0

    # Create missing order items
    for item_data in order_items_data:
        if len(order_items) >= 24:
            break  # We have enough items

        order = item_data["order"]
        product = item_data["product"]
        assert isinstance(order, Order), f"Expected Order, got {type(order)}"
        assert isinstance(product, Product), f"Expected Product, got {type(product)}"
        order_item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            qty=item_data["qty"],
            unit_price_kzt=item_data["unit_price_kzt"],
        )
        session.add(order_item)
        order_items.append(order_item)
        created_count += 1

    if created_count > 0:
        await session.flush()
        await session.commit()
        print(
            f"✅ Created {created_count} new order items (total: {len(order_items)} items)"
        )
    else:
        print(f"✅ All required order items already exist ({len(order_items)} items)")

    return order_items[:24]  # Return exactly 24 items for compatibility


if __name__ == "__main__":
    from app.db.session import AsyncSessionLocal
    from scripts.seed.seed_consumers import seed_consumers
    from scripts.seed.seed_orders import seed_orders
    from scripts.seed.seed_products import seed_products
    from scripts.seed.seed_suppliers import seed_suppliers
    from scripts.seed.seed_users import seed_users

    async def main():
        async with AsyncSessionLocal() as session:
            users = await seed_users(session)
            suppliers = await seed_suppliers(session, users)
            consumers = await seed_consumers(session, users)
            products = await seed_products(session, suppliers)
            orders = await seed_orders(session, suppliers, consumers)
            await seed_order_items(session, orders, products)

    asyncio.run(main())
