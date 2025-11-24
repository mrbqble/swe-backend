"""Tests for GET /api/v1/suppliers/staff endpoint."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from fastapi import status
from fastapi.testclient import TestClient

from app.core.roles import Role
from app.core.security import create_access_token
from app.modules.supplier.model import Supplier, SupplierStaff
from app.modules.user.model import User


class TestGetSupplierStaff:
    """Test cases for GET /api/v1/suppliers/staff."""

    def test_get_supplier_staff_success_as_owner(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_supplier_owner: User,
    ) -> None:
        """Test successful retrieval of staff list as supplier owner."""
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
        staff_user = User(
            id=2,
            email="staff@example.com",
            password_hash="hashed",
            first_name="Staff",
            last_name="Member",
            role=Role.SUPPLIER_SALES.value,
            is_active=True,
            created_at=datetime.now(UTC),
        )
        staff = SupplierStaff(
            id=1,
            user_id=2,
            supplier_id=1,
            staff_role="sales",
            created_at=datetime.now(UTC),
        )
        staff.user = staff_user

        # Setup: Mock database queries
        # 1. get_current_user
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_supplier_owner

        # 2. Get supplier
        mock_supplier_result = MagicMock()
        mock_supplier_result.scalar_one_or_none.return_value = supplier

        # 3. Get staff list
        mock_staff_result = MagicMock()
        mock_staff_result.scalars.return_value.all.return_value = [staff]

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

        # Test request
        response = test_client.get(
            "/api/v1/suppliers/staff",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["user_id"] == 2
        assert data[0]["email"] == "staff@example.com"
        assert data[0]["role"] == "sales"

    def test_get_supplier_staff_success_as_manager(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
    ) -> None:
        """Test successful retrieval of staff list as supplier manager."""
        # Create a manager user
        manager_user = User(
            id=3,
            email="manager@example.com",
            password_hash="hashed",
            first_name="Manager",
            last_name="User",
            role=Role.SUPPLIER_MANAGER.value,
            is_active=True,
            created_at=datetime.now(UTC),
        )

        # Create access token
        access_token = create_access_token(
            data={
                "sub": manager_user.id,
                "email": manager_user.email,
                "role": manager_user.role,
            }
        )

        # Create sample supplier
        supplier = Supplier(
            id=1,
            user_id=1,  # Different owner
            company_name="Test Supplier",
            is_active=True,
            created_at=datetime.now(UTC),
        )

        # Create staff record for manager
        staff_record = SupplierStaff(
            id=1,
            user_id=manager_user.id,
            supplier_id=1,
            staff_role="manager",
            created_at=datetime.now(UTC),
        )
        staff_record.supplier = supplier

        # Setup: Mock database queries
        # 1. get_current_user
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = manager_user

        # 2. Get supplier (returns None for owner)
        mock_supplier_result = MagicMock()
        mock_supplier_result.scalar_one_or_none.return_value = None

        # 3. Get staff record
        mock_staff_record_result = MagicMock()
        mock_staff_record_result.scalar_one_or_none.return_value = staff_record

        # 4. Get staff list
        mock_staff_list_result = MagicMock()
        mock_staff_list_result.scalars.return_value.all.return_value = []

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # get_current_user
                return mock_user_result
            if call_count == 2:  # Get supplier (owner check)
                return mock_supplier_result
            if call_count == 3:  # Get staff record
                return mock_staff_record_result
            # Get staff list
            return mock_staff_list_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request
        response = test_client.get(
            "/api/v1/suppliers/staff",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_get_supplier_staff_not_authorized(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
    ) -> None:
        """Test get staff with non-authorized role."""
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
            "/api/v1/suppliers/staff",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert (
            "Only supplier owners and managers can view staff"
            in response.json()["detail"]
        )

    def test_get_supplier_staff_supplier_not_found(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
    ) -> None:
        """Test get staff when supplier not found."""
        # Create a manager user
        manager_user = User(
            id=3,
            email="manager@example.com",
            password_hash="hashed",
            first_name="Manager",
            last_name="User",
            role=Role.SUPPLIER_MANAGER.value,
            is_active=True,
            created_at=datetime.now(UTC),
        )

        # Create access token
        access_token = create_access_token(
            data={
                "sub": manager_user.id,
                "email": manager_user.email,
                "role": manager_user.role,
            }
        )

        # Setup: Mock database queries
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = manager_user
        mock_supplier_result = MagicMock()
        mock_supplier_result.scalar_one_or_none.return_value = None
        mock_staff_record_result = MagicMock()
        mock_staff_record_result.scalar_one_or_none.return_value = None

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_user_result
            if call_count == 2:
                return mock_supplier_result
            return mock_staff_record_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request
        response = test_client.get(
            "/api/v1/suppliers/staff",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Supplier not found" in response.json()["detail"]

    def test_get_supplier_staff_no_token(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
    ) -> None:
        """Test get staff without authentication token."""
        # Test request without token
        response = test_client.get("/api/v1/suppliers/staff")

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
