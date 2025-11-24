"""Unit tests for GET /catalog/suppliers endpoint."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from fastapi import status
from fastapi.testclient import TestClient

from app.modules.supplier.model import Supplier


class TestListSuppliers:
    """Test cases for GET /api/v1/catalog/suppliers endpoint."""

    def test_list_suppliers_success(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
    ) -> None:
        """Test successful listing of suppliers."""
        # Create sample suppliers
        supplier1 = Supplier(
            id=1,
            user_id=1,
            company_name="Supplier A",
            is_active=True,
            created_at=datetime.now(UTC),
        )
        supplier2 = Supplier(
            id=2,
            user_id=2,
            company_name="Supplier B",
            is_active=True,
            created_at=datetime.now(UTC),
        )

        # Setup: Mock database queries
        # 1. Count query
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 2

        # 2. Main query
        mock_suppliers_result = MagicMock()
        mock_suppliers_result.scalars.return_value.all.return_value = [
            supplier1,
            supplier2,
        ]

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # Count query
                return mock_count_result
            # Main query
            return mock_suppliers_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request
        response = test_client.get("/api/v1/catalog/suppliers")

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
        assert data["items"][0]["company_name"] == "Supplier A"
        assert data["items"][1]["id"] == 2
        assert data["items"][1]["company_name"] == "Supplier B"

    def test_list_suppliers_with_search(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
    ) -> None:
        """Test listing suppliers with search query."""
        # Create sample supplier matching search
        supplier = Supplier(
            id=1,
            user_id=1,
            company_name="ABC Company",
            is_active=True,
            created_at=datetime.now(UTC),
        )

        # Setup: Mock database queries
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_suppliers_result = MagicMock()
        mock_suppliers_result.scalars.return_value.all.return_value = [supplier]

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # Count query
                return mock_count_result
            # Main query
            return mock_suppliers_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request with search
        response = test_client.get("/api/v1/catalog/suppliers?q=ABC")

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["company_name"] == "ABC Company"

    def test_list_suppliers_pagination(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
    ) -> None:
        """Test suppliers pagination."""
        # Setup: Mock database queries
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 30  # Total 30 suppliers
        mock_suppliers_result = MagicMock()
        mock_suppliers_result.scalars.return_value.all.return_value = []  # Empty page 2

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # Count query
                return mock_count_result
            # Main query
            return mock_suppliers_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request with pagination
        response = test_client.get("/api/v1/catalog/suppliers?page=2&size=20")

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 2
        assert data["size"] == 20
        assert data["total"] == 30
        assert data["pages"] == 2

    def test_list_suppliers_empty(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
    ) -> None:
        """Test listing suppliers when no suppliers exist."""
        # Setup: Mock database queries
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 0
        mock_suppliers_result = MagicMock()
        mock_suppliers_result.scalars.return_value.all.return_value = []

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # Count query
                return mock_count_result
            # Main query
            return mock_suppliers_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request
        response = test_client.get("/api/v1/catalog/suppliers")

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0
        assert data["page"] == 1

    def test_list_suppliers_no_auth_required(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
    ) -> None:
        """Test that listing suppliers doesn't require authentication."""
        # Setup: Mock database queries
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 0
        mock_suppliers_result = MagicMock()
        mock_suppliers_result.scalars.return_value.all.return_value = []

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # Count query
                return mock_count_result
            # Main query
            return mock_suppliers_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request without authentication
        response = test_client.get("/api/v1/catalog/suppliers")

        # Assertions - should work without auth (public endpoint)
        assert response.status_code == status.HTTP_200_OK
