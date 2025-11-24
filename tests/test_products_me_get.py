"""Tests for GET /api/v1/products/me endpoint."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from fastapi import status
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.modules.product.model import Product
from app.modules.supplier.model import Supplier
from app.modules.user.model import User


class TestGetMyProducts:
    """Test cases for GET /api/v1/products/me."""

    def test_get_my_products_success(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_supplier_owner: User,
    ) -> None:
        """Test successful retrieval of my products."""
        # Create a valid access token
        access_token = create_access_token(
            data={
                "sub": sample_supplier_owner.id,
                "email": sample_supplier_owner.email,
                "role": sample_supplier_owner.role,
            }
        )

        # Create sample supplier
        supplier = Supplier(
            id=1,
            user_id=sample_supplier_owner.id,
            company_name="Test Supplier",
            is_active=True,
            created_at=datetime.now(UTC),
        )

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
        # 1. get_current_user
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_supplier_owner

        # 2. get_supplier_by_user_id (in _get_supplier_id_for_user)
        mock_supplier_result = MagicMock()
        mock_supplier_result.scalar_one_or_none.return_value = supplier

        # 3. Count products
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 2

        # 4. Get products
        mock_products_result = MagicMock()
        mock_products_result.scalars.return_value.all.return_value = [
            product1,
            product2,
        ]

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # get_current_user
                return mock_user_result
            if call_count == 2:  # get_supplier_by_user_id
                return mock_supplier_result
            if call_count == 3:  # Count products
                return mock_count_result
            # Get products
            return mock_products_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request
        response = test_client.get(
            "/api/v1/products/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

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
        assert data["items"][1]["id"] == 2

    def test_get_my_products_with_active_filter(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_supplier_owner: User,
    ) -> None:
        """Test filtering my products by active status."""
        # Create a valid access token
        access_token = create_access_token(
            data={
                "sub": sample_supplier_owner.id,
                "email": sample_supplier_owner.email,
                "role": sample_supplier_owner.role,
            }
        )

        # Create sample supplier
        supplier = Supplier(
            id=1,
            user_id=sample_supplier_owner.id,
            company_name="Test Supplier",
            is_active=True,
            created_at=datetime.now(UTC),
        )

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
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_supplier_owner
        mock_supplier_result = MagicMock()
        mock_supplier_result.scalar_one_or_none.return_value = supplier
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_products_result = MagicMock()
        mock_products_result.scalars.return_value.all.return_value = [product]

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_user_result
            if call_count == 2:
                return mock_supplier_result
            if call_count == 3:
                return mock_count_result
            return mock_products_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request with active filter
        response = test_client.get(
            "/api/v1/products/me",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"is_active": True},
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["is_active"] is True

    def test_get_my_products_supplier_not_found(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_supplier_owner: User,
    ) -> None:
        """Test get my products when supplier profile not found."""
        # Create a valid access token
        access_token = create_access_token(
            data={
                "sub": sample_supplier_owner.id,
                "email": sample_supplier_owner.email,
                "role": sample_supplier_owner.role,
            }
        )

        # Setup: Mock database queries
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_supplier_owner
        mock_supplier_result = MagicMock()
        mock_supplier_result.scalar_one_or_none.return_value = None
        # Also need to mock SupplierStaff check (returns None)
        mock_staff_result = MagicMock()
        mock_staff_result.scalar_one_or_none.return_value = None

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_user_result
            if call_count == 2:
                return mock_supplier_result
            return mock_staff_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request
        response = test_client.get(
            "/api/v1/products/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Supplier profile not found" in response.json()["detail"]

    def test_get_my_products_not_authorized(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
    ) -> None:
        """Test get my products with non-authorized role."""
        # Create a valid access token for consumer
        access_token = create_access_token(
            data={
                "sub": sample_user.id,
                "email": sample_user.email,
                "role": sample_user.role,
            }
        )

        # Setup: Mock get_current_user
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute = AsyncMock(return_value=mock_user_result)

        # Test request
        response = test_client.get(
            "/api/v1/products/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_my_products_no_token(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
    ) -> None:
        """Test get my products without authentication token."""
        # Test request without token
        response = test_client.get("/api/v1/products/me")

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
