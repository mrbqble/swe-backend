"""Unit tests for GET /catalog endpoint."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from fastapi import status
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.modules.consumer.model import Consumer
from app.modules.link.model import Link, LinkStatus
from app.modules.product.model import Product
from app.modules.supplier.model import Supplier
from app.modules.user.model import User


class TestGetCatalog:
    """Test cases for GET /api/v1/catalog endpoint."""

    def test_get_catalog_success(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
        sample_consumer: Consumer,
    ) -> None:
        """Test successful retrieval of catalog."""
        # Create a valid access token
        access_token = create_access_token(
            data={
                "sub": sample_user.id,
                "email": sample_user.email,
                "role": sample_user.role,
            }
        )

        # Create sample supplier
        supplier = Supplier(
            id=1,
            user_id=2,
            company_name="Test Supplier",
            is_active=True,
            created_at=datetime.now(UTC),
        )

        # Create sample link
        link = Link(
            id=1,
            consumer_id=sample_consumer.id,
            supplier_id=1,
            status=LinkStatus.ACCEPTED,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
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

        # Setup: Mock database queries in order
        # 1. get_current_user (get_user_by_id)
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user

        # 2. get_consumer_by_user_id
        mock_consumer_result = MagicMock()
        mock_consumer_result.scalar_one_or_none.return_value = sample_consumer

        # 3. Get supplier
        mock_supplier_result = MagicMock()
        mock_supplier_result.scalar_one_or_none.return_value = supplier

        # 4. Get link
        mock_link_result = MagicMock()
        mock_link_result.scalar_one_or_none.return_value = link

        # 5. Count products
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 2

        # 6. Get products
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
            if call_count == 2:  # get_consumer_by_user_id
                return mock_consumer_result
            if call_count == 3:  # Get supplier
                return mock_supplier_result
            if call_count == 4:  # Get link
                return mock_link_result
            if call_count == 5:  # Count products
                return mock_count_result
            # Get products
            return mock_products_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request
        response = test_client.get(
            "/api/v1/catalog",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"supplier_id": 1},
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
        assert data["items"][0]["name"] == "Product 1"
        assert data["items"][1]["id"] == 2
        assert data["items"][1]["name"] == "Product 2"

    def test_get_catalog_not_consumer(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_supplier_owner: User,
    ) -> None:
        """Test get catalog with non-consumer role."""
        # Create a valid access token for supplier owner
        access_token = create_access_token(
            data={
                "sub": sample_supplier_owner.id,
                "email": sample_supplier_owner.email,
                "role": sample_supplier_owner.role,
            }
        )

        # Setup: Mock get_current_user
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_supplier_owner
        mock_db_session.execute = AsyncMock(return_value=mock_user_result)

        # Test request
        response = test_client.get(
            "/api/v1/catalog",
            params={"supplier_id": 1},
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_catalog_consumer_not_found(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
    ) -> None:
        """Test get catalog when consumer profile not found."""
        # Create a valid access token
        access_token = create_access_token(
            data={
                "sub": sample_user.id,
                "email": sample_user.email,
                "role": sample_user.role,
            }
        )

        # Setup: Mock database queries
        # 1. get_current_user
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user

        # 2. get_consumer_by_user_id returns None
        mock_consumer_result = MagicMock()
        mock_consumer_result.scalar_one_or_none.return_value = None

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # get_current_user
                return mock_user_result
            # get_consumer_by_user_id
            return mock_consumer_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request
        response = test_client.get(
            "/api/v1/catalog",
            params={"supplier_id": 1},
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Consumer profile not found" in response.json()["detail"]

    def test_get_catalog_supplier_not_found(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
        sample_consumer: Consumer,
    ) -> None:
        """Test get catalog when supplier not found."""
        # Create a valid access token
        access_token = create_access_token(
            data={
                "sub": sample_user.id,
                "email": sample_user.email,
                "role": sample_user.role,
            }
        )

        # Setup: Mock database queries
        # 1. get_current_user
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user

        # 2. get_consumer_by_user_id
        mock_consumer_result = MagicMock()
        mock_consumer_result.scalar_one_or_none.return_value = sample_consumer

        # 3. Get supplier returns None
        mock_supplier_result = MagicMock()
        mock_supplier_result.scalar_one_or_none.return_value = None

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # get_current_user
                return mock_user_result
            if call_count == 2:  # get_consumer_by_user_id
                return mock_consumer_result
            # Get supplier
            return mock_supplier_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request
        response = test_client.get(
            "/api/v1/catalog",
            params={"supplier_id": 999},
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Supplier not found" in response.json()["detail"]

    def test_get_catalog_no_link(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
        sample_consumer: Consumer,
    ) -> None:
        """Test get catalog when no accepted link exists."""
        # Create a valid access token
        access_token = create_access_token(
            data={
                "sub": sample_user.id,
                "email": sample_user.email,
                "role": sample_user.role,
            }
        )

        # Create sample supplier
        supplier = Supplier(
            id=1,
            user_id=2,
            company_name="Test Supplier",
            is_active=True,
            created_at=datetime.now(UTC),
        )

        # Setup: Mock database queries
        # 1. get_current_user
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user

        # 2. get_consumer_by_user_id
        mock_consumer_result = MagicMock()
        mock_consumer_result.scalar_one_or_none.return_value = sample_consumer

        # 3. Get supplier
        mock_supplier_result = MagicMock()
        mock_supplier_result.scalar_one_or_none.return_value = supplier

        # 4. Get link returns None
        mock_link_result = MagicMock()
        mock_link_result.scalar_one_or_none.return_value = None

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # get_current_user
                return mock_user_result
            if call_count == 2:  # get_consumer_by_user_id
                return mock_consumer_result
            if call_count == 3:  # Get supplier
                return mock_supplier_result
            # Get link
            return mock_link_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request
        response = test_client.get(
            "/api/v1/catalog",
            params={"supplier_id": 1},
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "accepted link" in response.json()["detail"].lower()

    def test_get_catalog_pagination(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
        sample_consumer: Consumer,
    ) -> None:
        """Test catalog pagination."""
        # Create a valid access token
        access_token = create_access_token(
            data={
                "sub": sample_user.id,
                "email": sample_user.email,
                "role": sample_user.role,
            }
        )

        # Create sample supplier and link
        supplier = Supplier(
            id=1,
            user_id=2,
            company_name="Test Supplier",
            is_active=True,
            created_at=datetime.now(UTC),
        )
        link = Link(
            id=1,
            consumer_id=sample_consumer.id,
            supplier_id=1,
            status=LinkStatus.ACCEPTED,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Setup: Mock database queries
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user
        mock_consumer_result = MagicMock()
        mock_consumer_result.scalar_one_or_none.return_value = sample_consumer
        mock_supplier_result = MagicMock()
        mock_supplier_result.scalar_one_or_none.return_value = supplier
        mock_link_result = MagicMock()
        mock_link_result.scalar_one_or_none.return_value = link
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 25  # Total 25 products
        mock_products_result = MagicMock()
        mock_products_result.scalars.return_value.all.return_value = []  # Empty page 2

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_user_result
            if call_count == 2:
                return mock_consumer_result
            if call_count == 3:
                return mock_supplier_result
            if call_count == 4:
                return mock_link_result
            if call_count == 5:
                return mock_count_result
            return mock_products_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request with pagination
        response = test_client.get(
            "/api/v1/catalog",
            params={"supplier_id": 1, "page": 2, "size": 20},
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 2
        assert data["size"] == 20
        assert data["total"] == 25
        assert data["pages"] == 2

    def test_get_catalog_no_token(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
    ) -> None:
        """Test get catalog without authentication token."""
        # Test request without token
        response = test_client.get("/api/v1/catalog", params={"supplier_id": 1})

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
