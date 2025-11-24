"""Tests for GET /api/v1/products/{product_id} endpoint (public get)."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from fastapi import status
from fastapi.testclient import TestClient

from app.modules.product.model import Product
from app.modules.supplier.model import Supplier


class TestGetProduct:
    """Test cases for GET /api/v1/products/{product_id}."""

    def test_get_product_success(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
    ) -> None:
        """Test successful retrieval of a single product."""
        # Create sample supplier
        supplier = Supplier(
            id=1,
            user_id=1,
            company_name="Test Supplier",
            is_active=True,
            created_at=datetime.now(UTC),
        )

        # Create sample product
        product = Product(
            id=1,
            supplier_id=1,
            name="Product 1",
            description="Description 1",
            price_kzt=Decimal("1000.00"),
            currency="KZT",
            sku="SKU-001",
            stock_qty=10,
            delivery_available=True,
            pickup_available=True,
            is_active=True,
            created_at=datetime.now(UTC),
        )
        product.supplier = supplier

        # Setup: Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = product
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Test request (public endpoint, no auth required)
        response = test_client.get("/api/v1/products/1")

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "Product 1"
        assert data["supplier_id"] == 1
        assert "supplier" in data
        assert data["supplier"]["id"] == 1
        assert data["supplier"]["company_name"] == "Test Supplier"

    def test_get_product_not_found(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
    ) -> None:
        """Test get product when product not found."""
        # Setup: Mock database query returns None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Test request
        response = test_client.get("/api/v1/products/999")

        # Assertions
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Product not found" in response.json()["detail"]

    def test_get_product_without_supplier(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
    ) -> None:
        """Test get product when supplier relationship is not loaded."""
        # Create sample product without supplier
        product = Product(
            id=1,
            supplier_id=1,
            name="Product 1",
            description="Description 1",
            price_kzt=Decimal("1000.00"),
            currency="KZT",
            sku="SKU-001",
            stock_qty=10,
            delivery_available=True,
            pickup_available=True,
            is_active=True,
            created_at=datetime.now(UTC),
        )

        # Setup: Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = product
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Test request
        response = test_client.get("/api/v1/products/1")

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == 1
        # Supplier info should not be included if supplier is None
        if "supplier" in data:
            # If supplier is included, it should be valid
            assert data["supplier"]["id"] is not None
