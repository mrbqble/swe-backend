"""Unit tests for PATCH /links/{id}/status endpoint."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.modules.link.model import Link, LinkStatus
from app.modules.supplier.model import Supplier
from app.modules.user.model import User


class TestUpdateLinkStatus:
    """Test cases for PATCH /api/v1/links/{id}/status endpoint."""

    @pytest.mark.filterwarnings("ignore::RuntimeWarning:unittest.mock")
    def test_update_link_status_success(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_supplier_owner: User,
    ) -> None:
        """Test successful update of link status."""
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

        # Create sample link
        link = Link(
            id=1,
            consumer_id=1,
            supplier_id=1,
            status=LinkStatus.PENDING,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Setup: Mock database queries
        # 1. get_current_user
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_supplier_owner

        # 2. Get link with supplier
        mock_link_result = MagicMock()
        mock_link_result.scalar_one_or_none.return_value = link

        # 3. is_supplier_owner_or_manager - get_supplier_by_user_id
        mock_supplier_result = MagicMock()
        mock_supplier_result.scalar_one_or_none.return_value = supplier

        # 4. Get link with relationships (after update)
        mock_updated_link_result = MagicMock()
        mock_updated_link_result.scalar_one.return_value = link

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # get_current_user
                return mock_user_result
            if call_count == 2:  # Get link with supplier
                return mock_link_result
            if call_count == 3:  # is_supplier_owner_or_manager
                return mock_supplier_result
            # Get link with relationships
            return mock_updated_link_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        # Test request
        response = test_client.patch(
            "/api/v1/links/1/status",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"status": "accepted"},
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == 1
        assert data["status"] == "accepted"
        # Verify commit was called
        mock_db_session.commit.assert_called_once()

    def test_update_link_status_not_authorized(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
    ) -> None:
        """Test update link status with non-supplier role."""
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
        response = test_client.patch(
            "/api/v1/links/1/status",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"status": "accepted"},
        )

        # Assertions
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_link_status_not_found(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_supplier_owner: User,
    ) -> None:
        """Test update link status when link not found."""
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
        mock_link_result = MagicMock()
        mock_link_result.scalar_one_or_none.return_value = None

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # get_current_user
                return mock_user_result
            # Get link
            return mock_link_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request
        response = test_client.patch(
            "/api/v1/links/999/status",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"status": "accepted"},
        )

        # Assertions
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Link not found" in response.json()["detail"]

    def test_update_link_status_invalid_transition(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_supplier_owner: User,
    ) -> None:
        """Test update link status with invalid state transition."""
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

        # Create link with BLOCKED status (cannot transition to ACCEPTED directly per test expectation)
        # Note: According to the code, BLOCKED -> ACCEPTED is actually valid, but test expects invalid
        # Using DENIED status instead which cannot transition to ACCEPTED
        link = Link(
            id=1,
            consumer_id=1,
            supplier_id=1,
            status=LinkStatus.DENIED,  # DENIED cannot transition to ACCEPTED
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        # Prevent lazy loading of relationships
        object.__setattr__(link, "supplier", None)
        object.__setattr__(link, "consumer", None)

        # Setup: Mock database queries
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_supplier_owner
        mock_link_result = MagicMock()
        mock_link_result.scalar_one_or_none.return_value = link
        mock_supplier_result = MagicMock()
        mock_supplier_result.scalar_one_or_none.return_value = supplier

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # get_current_user
                return mock_user_result
            if call_count == 2:  # Get link
                return mock_link_result
            # is_supplier_owner_or_manager
            return mock_supplier_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request - try to change from DENIED to ACCEPTED (invalid transition)
        response = test_client.patch(
            "/api/v1/links/1/status",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"status": "accepted"},
        )

        # Assertions
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot transition" in response.json()["detail"]

    def test_update_link_status_no_permission(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_supplier_owner: User,
    ) -> None:
        """Test update link status when user doesn't have permission for supplier."""
        # Create a valid access token
        access_token = create_access_token(
            data={
                "sub": sample_supplier_owner.id,
                "email": sample_supplier_owner.email,
                "role": sample_supplier_owner.role,
            }
        )

        # Create link for different supplier
        link = Link(
            id=1,
            consumer_id=1,
            supplier_id=999,  # Different supplier
            status=LinkStatus.PENDING,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Setup: Mock database queries
        # is_supplier_owner_or_manager returns False (no permission)
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_supplier_owner
        mock_link_result = MagicMock()
        mock_link_result.scalar_one_or_none.return_value = link
        mock_supplier_result = MagicMock()
        mock_supplier_result.scalar_one_or_none.return_value = None  # Not owner
        mock_staff_result = MagicMock()
        mock_staff_result.scalar_one_or_none.return_value = None  # Not manager

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # get_current_user
                return mock_user_result
            if call_count == 2:  # Get link
                return mock_link_result
            if (
                call_count == 3
            ):  # is_supplier_owner_or_manager - get_supplier_by_user_id
                return mock_supplier_result
            # is_supplier_owner_or_manager - check staff
            return mock_staff_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request
        response = test_client.patch(
            "/api/v1/links/1/status",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"status": "accepted"},
        )

        # Assertions
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "permission" in response.json()["detail"].lower()
