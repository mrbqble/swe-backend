"""Tests for PUT /api/v1/products/{product_id} endpoint."""

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


class TestUpdateProduct:
    """Test cases for PUT /api/v1/products/{product_id}."""

    def test_update_product_success(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_supplier_owner: User,
    ) -> None:
        """Test successful update of a product."""
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

        # Create sample product
        product = Product(
            id=1,
            supplier_id=1,
            name="Old Product Name",
            description="Old description",
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
        # 1. get_current_user
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_supplier_owner

        # 2. Get product
        mock_product_result = MagicMock()
        mock_product_result.scalar_one_or_none.return_value = product

        # 3. is_supplier_owner_or_manager - get_supplier_by_user_id
        mock_supplier_check_result = MagicMock()
        mock_supplier_check_result.scalar_one_or_none.return_value = supplier

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # get_current_user
                return mock_user_result
            if call_count == 2:  # Get product
                return mock_product_result
            # is_supplier_owner_or_manager check
            return mock_supplier_check_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        # Test request
        response = test_client.put(
            "/api/v1/products/1",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"name": "Updated Product Name", "price_kzt": "2000.00"},
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Product Name"
        assert data["price_kzt"] == "2000.00"

    def test_update_product_sku_conflict(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_supplier_owner: User,
    ) -> None:
        """Test update product when new SKU already exists."""
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

        # Create sample product
        product = Product(
            id=1,
            supplier_id=1,
            name="Product 1",
            description="Description",
            price_kzt=Decimal("1000.00"),
            currency="KZT",
            sku="SKU-001",
            stock_qty=10,
            delivery_available=True,
            pickup_available=True,
            is_active=True,
            created_at=datetime.now(UTC),
        )

        # Create existing product with SKU-002
        existing_product = Product(
            id=2,
            supplier_id=1,
            name="Product 2",
            description="Description",
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
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_supplier_owner
        mock_product_result = MagicMock()
        mock_product_result.scalar_one_or_none.return_value = product
        mock_supplier_check_result = MagicMock()
        mock_supplier_check_result.scalar_one_or_none.return_value = supplier
        mock_sku_check_result = MagicMock()
        mock_sku_check_result.scalar_one_or_none.return_value = existing_product

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_user_result
            if call_count == 2:
                return mock_product_result
            if call_count == 3:
                return mock_supplier_check_result
            return mock_sku_check_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request - try to change SKU to one that already exists
        response = test_client.put(
            "/api/v1/products/1",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"sku": "SKU-002"},
        )

        # Assertions
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "Product with this SKU already exists" in response.json()["detail"]

    def test_update_product_not_found(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_supplier_owner: User,
    ) -> None:
        """Test update product when product not found."""
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
        mock_product_result = MagicMock()
        mock_product_result.scalar_one_or_none.return_value = None

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_user_result
            return mock_product_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request
        response = test_client.put(
            "/api/v1/products/999",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"name": "Updated Name"},
        )

        # Assertions
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Product not found" in response.json()["detail"]

    def test_update_product_no_permission(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_supplier_owner: User,
    ) -> None:
        """Test update product when user doesn't have permission."""
        # Create a valid access token
        access_token = create_access_token(
            data={
                "sub": sample_supplier_owner.id,
                "email": sample_supplier_owner.email,
                "role": sample_supplier_owner.role,
            }
        )

        # Create product from different supplier
        product = Product(
            id=1,
            supplier_id=999,  # Different supplier
            name="Product 1",
            description="Description",
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
        mock_product_result = MagicMock()
        mock_product_result.scalar_one_or_none.return_value = product
        # is_supplier_owner_or_manager returns False (supplier not found, staff not found)
        mock_supplier_check_result = MagicMock()
        mock_supplier_check_result.scalar_one_or_none.return_value = None
        mock_staff_check_result = MagicMock()
        mock_staff_check_result.scalar_one_or_none.return_value = None

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_user_result
            if call_count == 2:
                return mock_product_result
            if call_count == 3:
                return mock_supplier_check_result
            return mock_staff_check_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request
        response = test_client.put(
            "/api/v1/products/1",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"name": "Updated Name"},
        )

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert (
            "permission to manage this supplier's products" in response.json()["detail"]
        )

    def test_update_product_not_authorized(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
    ) -> None:
        """Test update product with non-authorized role."""
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
        response = test_client.put(
            "/api/v1/products/1",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"name": "Updated Name"},
        )

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_product_no_token(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
    ) -> None:
        """Test update product without authentication token."""
        # Test request without token
        response = test_client.put(
            "/api/v1/products/1",
            json={"name": "Updated Name"},
        )

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
