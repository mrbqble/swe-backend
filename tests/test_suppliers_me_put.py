"""Tests for PUT /api/v1/suppliers/me endpoint."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from fastapi import status
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.modules.supplier.model import Supplier
from app.modules.user.model import User


class TestUpdateMySupplier:
    """Test cases for PUT /api/v1/suppliers/me."""

    def test_update_my_supplier_success(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_supplier_owner: User,
    ) -> None:
        """Test successful update of supplier profile."""
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
            company_name="Old Company Name",
            is_active=True,
            created_at=datetime.now(UTC),
        )

        # Setup: Mock database queries
        # 1. get_current_user
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_supplier_owner

        # 2. Get supplier
        mock_supplier_result = MagicMock()
        mock_supplier_result.scalar_one_or_none.return_value = supplier

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # get_current_user
                return mock_user_result
            # Get supplier
            return mock_supplier_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        # Test request
        response = test_client.put(
            "/api/v1/suppliers/me",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"company_name": "New Company Name"},
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == 1
        assert data["company_name"] == "New Company Name"
        assert data["is_active"] is True

    def test_update_my_supplier_partial(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_supplier_owner: User,
    ) -> None:
        """Test partial update of supplier profile."""
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
            company_name="Original Name",
            is_active=True,
            created_at=datetime.now(UTC),
        )

        # Setup: Mock database queries
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_supplier_owner
        mock_supplier_result = MagicMock()
        mock_supplier_result.scalar_one_or_none.return_value = supplier

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_user_result
            return mock_supplier_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        # Test request - only update is_active
        response = test_client.put(
            "/api/v1/suppliers/me",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"is_active": False},
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_active"] is False

    def test_update_my_supplier_not_found(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_supplier_owner: User,
    ) -> None:
        """Test update supplier when profile not found."""
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

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_user_result
            return mock_supplier_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request
        response = test_client.put(
            "/api/v1/suppliers/me",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"company_name": "New Name"},
        )

        # Assertions
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Supplier profile not found" in response.json()["detail"]

    def test_update_my_supplier_not_supplier_owner(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
    ) -> None:
        """Test update supplier with non-supplier-owner role."""
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
            "/api/v1/suppliers/me",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"company_name": "New Name"},
        )

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert (
            "Only supplier owners can update supplier profile"
            in response.json()["detail"]
        )

    def test_update_my_supplier_no_token(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
    ) -> None:
        """Test update supplier without authentication token."""
        # Test request without token
        response = test_client.put(
            "/api/v1/suppliers/me",
            json={"company_name": "New Name"},
        )

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
