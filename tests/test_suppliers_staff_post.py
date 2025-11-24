"""Tests for POST /api/v1/suppliers/staff endpoint."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from fastapi import status
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.modules.supplier.model import Supplier
from app.modules.user.model import User


class TestCreateSupplierStaff:
    """Test cases for POST /api/v1/suppliers/staff."""

    def test_create_supplier_staff_success(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_supplier_owner: User,
    ) -> None:
        """Test successful creation of staff member (returns message)."""
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

        # Setup: Mock database queries
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_supplier_owner
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

        # Test request
        response = test_client.post(
            "/api/v1/suppliers/staff",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"user_id": 2, "staff_role": "sales"},
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert (
            data["message"]
            == "Staff member creation should be done via user registration"
        )

    def test_create_supplier_staff_not_found(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_supplier_owner: User,
    ) -> None:
        """Test create staff when supplier profile not found."""
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
        response = test_client.post(
            "/api/v1/suppliers/staff",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"user_id": 2, "staff_role": "sales"},
        )

        # Assertions
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Supplier profile not found" in response.json()["detail"]

    def test_create_supplier_staff_not_owner(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
    ) -> None:
        """Test create staff with non-owner role."""
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
            "/api/v1/suppliers/staff",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"user_id": 2, "staff_role": "sales"},
        )

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert (
            "Only supplier owners can create staff members" in response.json()["detail"]
        )

    def test_create_supplier_staff_no_token(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
    ) -> None:
        """Test create staff without authentication token."""
        # Test request without token
        response = test_client.post(
            "/api/v1/suppliers/staff",
            json={"user_id": 2, "staff_role": "sales"},
        )

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
