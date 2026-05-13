"""Seed products table with sample iCare catalog items."""

import asyncio
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.product.model import Product


SAMPLE_PRODUCTS = [
    {
        "name": "Collagen Peptides 300g",
        "sku": "IC-COL-300",
        "description": "Hydrolyzed collagen peptides powder, unflavored. 30 servings.",
        "price": Decimal("8900.00"),
        "currency": "KZT",
        "stock_qty": 200,
        "unit": "jar",
        "min_order_qty": 1,
        "category": "supplements",
    },
    {
        "name": "Omega-3 Fish Oil 1000mg (90 caps)",
        "sku": "IC-OMG-090",
        "description": "High-potency fish oil with EPA and DHA. 90 softgel capsules.",
        "price": Decimal("5400.00"),
        "currency": "KZT",
        "stock_qty": 150,
        "unit": "bottle",
        "min_order_qty": 1,
        "category": "supplements",
    },
    {
        "name": "Vitamin D3 + K2 (60 caps)",
        "sku": "IC-VDK-060",
        "description": "Vitamin D3 2000 IU with K2 MK-7 for calcium absorption. 60 capsules.",
        "price": Decimal("3900.00"),
        "currency": "KZT",
        "stock_qty": 300,
        "unit": "bottle",
        "min_order_qty": 1,
        "category": "vitamins",
    },
    {
        "name": "Magnesium Glycinate 400mg (120 caps)",
        "sku": "IC-MAG-120",
        "description": "Chelated magnesium glycinate for superior absorption. 120 capsules.",
        "price": Decimal("6200.00"),
        "currency": "KZT",
        "stock_qty": 120,
        "unit": "bottle",
        "min_order_qty": 1,
        "category": "minerals",
    },
    {
        "name": "Probiotic Complex 30 Billion CFU (30 caps)",
        "sku": "IC-PRB-030",
        "description": "10-strain probiotic blend, 30 billion CFU per capsule.",
        "price": Decimal("12500.00"),
        "currency": "KZT",
        "stock_qty": 80,
        "unit": "bottle",
        "min_order_qty": 1,
        "category": "probiotics",
    },
    {
        "name": "Starter Pack (3 items)",
        "sku": "IC-STR-PKG",
        "description": "Collagen + Omega-3 + Vitamin D3/K2 bundle. Best-seller combo.",
        "price": Decimal("16500.00"),
        "currency": "KZT",
        "stock_qty": 50,
        "unit": "pack",
        "min_order_qty": 1,
        "category": "bundles",
    },
]


async def seed_products(session: AsyncSession) -> list[Product]:
    seeded: list[Product] = []
    for data in SAMPLE_PRODUCTS:
        result = await session.execute(select(Product).where(Product.sku == data["sku"]))
        existing = result.scalar_one_or_none()
        if existing:
            print(f"  Product already exists: {data['sku']}")
            seeded.append(existing)
            continue

        product = Product(**data)
        session.add(product)
        await session.flush()
        seeded.append(product)
        print(f"  Created product: {data['sku']} — {data['name']}")

    await session.commit()
    return seeded


if __name__ == "__main__":
    from app.db.session import AsyncSessionLocal

    async def main():
        async with AsyncSessionLocal() as session:
            await seed_products(session)

    asyncio.run(main())
