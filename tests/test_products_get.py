"""Tests for GET /api/v1/products endpoint (public list)."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from fastapi import status
from fastapi.testclient import TestClient

from app.modules.product.model import Product


class TestGetProducts:
    """Test cases for GET /api/v1/products (public list)."""

    def test_get_products_success(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
    ) -> None:
        """Test successful retrieval of products list."""
        # Create sample products
        product1 = Product(
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
        product2 = Product(
            id=2,
            supplier_id=1,
            name="Product 2",
            description="Description 2",
            price_kzt=Decimal("2000.00"),
            currency="KZT",
            sku="SKU-002",
            stock_qty=20,
            delivery_available=True,
            pickup_available=True,
            is_active=True,
            created_at=datetime.now(UTC),
        )

        # Setup: Mock database queries
        # 1. Count query
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 2

        # 2. Main query
        mock_products_result = MagicMock()
        mock_products_result.scalars.return_value.all.return_value = [
            product1,
            product2,
        ]

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # Count query
                return mock_count_result
            # Main query
            return mock_products_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request (public endpoint, no auth required)
        response = test_client.get("/api/v1/products")

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "page" in data
        assert "size" in data
        assert "total" in data
        assert "pages" in data
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["items"][0]["id"] == 1
        assert data["items"][0]["name"] == "Product 1"
        assert data["items"][1]["id"] == 2
        assert data["items"][1]["name"] == "Product 2"

    def test_get_products_with_supplier_filter(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
    ) -> None:
        """Test filtering products by supplier ID."""
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

        # Setup: Mock database queries
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_products_result = MagicMock()
        mock_products_result.scalars.return_value.all.return_value = [product]

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_count_result
            return mock_products_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request with supplier filter
        response = test_client.get("/api/v1/products", params={"supplier_id": 1})

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["supplier_id"] == 1

    def test_get_products_with_active_filter(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
    ) -> None:
        """Test filtering products by active status."""
        # Create sample active product
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

        # Setup: Mock database queries
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_products_result = MagicMock()
        mock_products_result.scalars.return_value.all.return_value = [product]

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_count_result
            return mock_products_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request with active filter
        response = test_client.get("/api/v1/products", params={"is_active": True})

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["is_active"] is True

    def test_get_products_pagination(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
    ) -> None:
        """Test pagination of products."""
        # Setup: Mock database queries
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 25  # Total 25 products
        mock_products_result = MagicMock()
        mock_products_result.scalars.return_value.all.return_value = []  # Empty page 2

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_count_result
            return mock_products_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request with pagination
        response = test_client.get("/api/v1/products", params={"page": 2, "size": 20})

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 2
        assert data["size"] == 20
        assert data["total"] == 25
        assert data["pages"] == 2

    def test_get_products_empty_list(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
    ) -> None:
        """Test empty products list."""
        # Setup: Mock database queries
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 0
        mock_products_result = MagicMock()
        mock_products_result.scalars.return_value.all.return_value = []

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_count_result
            return mock_products_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request
        response = test_client.get("/api/v1/products")

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0
