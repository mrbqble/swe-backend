"""Tests for DELETE /api/v1/suppliers/staff/{staff_id} endpoint."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from fastapi import status
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.modules.supplier.model import Supplier, SupplierStaff
from app.modules.user.model import User


class TestDeleteSupplierStaff:
    """Test cases for DELETE /api/v1/suppliers/staff/{staff_id}."""

    def test_delete_supplier_staff_success(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_supplier_owner: User,
    ) -> None:
        """Test successful deletion of staff member."""
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

        # Create sample staff member
        staff = SupplierStaff(
            id=1,
            user_id=2,
            supplier_id=1,
            staff_role="sales",
            created_at=datetime.now(UTC),
        )

        # Setup: Mock database queries
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_supplier_owner
        mock_supplier_result = MagicMock()
        mock_supplier_result.scalar_one_or_none.return_value = supplier
        mock_staff_result = MagicMock()
        mock_staff_result.scalar_one_or_none.return_value = staff

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # get_current_user
                return mock_user_result
            if call_count == 2:  # Get supplier
                return mock_supplier_result
            # Get staff
            return mock_staff_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)
        mock_db_session.delete = AsyncMock()
        mock_db_session.commit = AsyncMock()

        # Test request
        response = test_client.delete(
            "/api/v1/suppliers/staff/1",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Staff member deleted successfully"

    def test_delete_supplier_staff_not_found(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_supplier_owner: User,
    ) -> None:
        """Test delete staff when staff member not found."""
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
        response = test_client.delete(
            "/api/v1/suppliers/staff/999",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Staff member not found" in response.json()["detail"]

    def test_delete_supplier_staff_supplier_not_found(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_supplier_owner: User,
    ) -> None:
        """Test delete staff when supplier profile not found."""
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
        response = test_client.delete(
            "/api/v1/suppliers/staff/1",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Supplier profile not found" in response.json()["detail"]

    def test_delete_supplier_staff_not_owner(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
    ) -> None:
        """Test delete staff with non-owner role."""
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
        response = test_client.delete(
            "/api/v1/suppliers/staff/1",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert (
            "Only supplier owners can delete staff members" in response.json()["detail"]
        )

    def test_delete_supplier_staff_no_token(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
    ) -> None:
        """Test delete staff without authentication token."""
        # Test request without token
        response = test_client.delete("/api/v1/suppliers/staff/1")

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
