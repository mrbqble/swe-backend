"""Tests for POST /api/v1/products endpoint."""

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


class TestCreateProduct:
    """Test cases for POST /api/v1/products."""

    def test_create_product_success(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_supplier_owner: User,
    ) -> None:
        """Test successful creation of a product."""
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

        # Create product that will be returned after creation
        created_product = Product(
            id=1,
            supplier_id=1,
            name="New Product",
            description="Product description",
            price_kzt=Decimal("5000.00"),
            currency="KZT",
            sku="SKU-001",
            stock_qty=100,
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

        # 3. Check SKU uniqueness (returns None - no existing product)
        mock_sku_check_result = MagicMock()
        mock_sku_check_result.scalar_one_or_none.return_value = None

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # get_current_user
                return mock_user_result
            if call_count == 2:  # get_supplier_by_user_id
                return mock_supplier_result
            # Check SKU uniqueness
            return mock_sku_check_result

        async def refresh_side_effect(obj):
            """Mock refresh to set id and created_at on the product."""
            if isinstance(obj, Product):
                obj.id = created_product.id
                obj.created_at = created_product.created_at

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock(side_effect=refresh_side_effect)

        # Test request
        response = test_client.post(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "name": "New Product",
                "description": "Product description",
                "price_kzt": "5000.00",
                "currency": "KZT",
                "sku": "SKU-001",
                "stock_qty": 100,
                "delivery_available": True,
                "pickup_available": True,
                "is_active": True,
            },
        )

        # Assertions
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "New Product"
        assert data["sku"] == "SKU-001"
        assert data["price_kzt"] == "5000.00"

    def test_create_product_sku_already_exists(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_supplier_owner: User,
    ) -> None:
        """Test create product when SKU already exists."""
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

        # Create existing product with same SKU
        existing_product = Product(
            id=1,
            supplier_id=1,
            name="Existing Product",
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
        mock_supplier_result = MagicMock()
        mock_supplier_result.scalar_one_or_none.return_value = supplier
        mock_sku_check_result = MagicMock()
        mock_sku_check_result.scalar_one_or_none.return_value = existing_product

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_user_result
            if call_count == 2:
                return mock_supplier_result
            return mock_sku_check_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request
        response = test_client.post(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "name": "New Product",
                "price_kzt": "5000.00",
                "currency": "KZT",
                "sku": "SKU-001",
                "stock_qty": 100,
                "delivery_available": True,
                "pickup_available": True,
            },
        )

        # Assertions
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "Product with this SKU already exists" in response.json()["detail"]

    def test_create_product_supplier_not_found(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_supplier_owner: User,
    ) -> None:
        """Test create product when supplier profile not found."""
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
        response = test_client.post(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "name": "New Product",
                "price_kzt": "5000.00",
                "currency": "KZT",
                "sku": "SKU-001",
                "stock_qty": 100,
                "delivery_available": True,
                "pickup_available": True,
            },
        )

        # Assertions
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Supplier profile not found" in response.json()["detail"]

    def test_create_product_not_authorized(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
    ) -> None:
        """Test create product with non-authorized role."""
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
        response = test_client.post(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "name": "New Product",
                "price_kzt": "5000.00",
                "currency": "KZT",
                "sku": "SKU-001",
                "stock_qty": 100,
                "delivery_available": True,
                "pickup_available": True,
            },
        )

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_product_no_token(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
    ) -> None:
        """Test create product without authentication token."""
        # Test request without token
        response = test_client.post(
            "/api/v1/products",
            json={
                "name": "New Product",
                "price_kzt": "5000.00",
                "currency": "KZT",
                "sku": "SKU-001",
                "stock_qty": 100,
                "delivery_available": True,
                "pickup_available": True,
            },
        )

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
