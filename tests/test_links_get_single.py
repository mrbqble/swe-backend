"""Unit tests for GET /links/{id} endpoint."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.modules.consumer.model import Consumer
from app.modules.link.model import Link, LinkStatus
from app.modules.supplier.model import Supplier
from app.modules.user.model import User


class TestGetLink:
    """Test cases for GET /api/v1/links/{id} endpoint."""

    @pytest.mark.filterwarnings("ignore::RuntimeWarning:unittest.mock")
    def test_get_link_success_consumer(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
        sample_consumer: Consumer,
    ) -> None:
        """Test successful retrieval of link by consumer."""
        # Create a valid access token
        access_token = create_access_token(
            data={
                "sub": sample_user.id,
                "email": sample_user.email,
                "role": sample_user.role,
            }
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

        # Setup: Mock database queries
        # 1. get_current_user
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user

        # 2. Get link with relationships
        mock_link_result = MagicMock()
        mock_link_result.scalar_one_or_none.return_value = link

        # 3. get_consumer_by_user_id
        mock_consumer_result = MagicMock()
        mock_consumer_result.scalar_one_or_none.return_value = sample_consumer

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # get_current_user
                return mock_user_result
            if call_count == 2:  # Get link
                return mock_link_result
            # get_consumer_by_user_id
            return mock_consumer_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request
        response = test_client.get(
            "/api/v1/links/1",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == 1
        assert data["consumer_id"] == sample_consumer.id
        assert data["status"] == LinkStatus.ACCEPTED.value

    @pytest.mark.filterwarnings("ignore::RuntimeWarning:unittest.mock")
    def test_get_link_success_supplier(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_supplier_owner: User,
    ) -> None:
        """Test successful retrieval of link by supplier owner."""
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

        # Test request
        response = test_client.get(
            "/api/v1/links/1",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == 1
        assert data["supplier_id"] == 1

    def test_get_link_not_found(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
    ) -> None:
        """Test get link when link not found."""
        # Create a valid access token
        access_token = create_access_token(
            data={
                "sub": sample_user.id,
                "email": sample_user.email,
                "role": sample_user.role,
            }
        )

        # Setup: Mock database queries
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user
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
        response = test_client.get(
            "/api/v1/links/999",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Link not found" in response.json()["detail"]

    def test_get_link_no_permission(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
        sample_consumer: Consumer,
    ) -> None:
        """Test get link when user doesn't have permission."""
        # Create a valid access token
        access_token = create_access_token(
            data={
                "sub": sample_user.id,
                "email": sample_user.email,
                "role": sample_user.role,
            }
        )

        # Create link for different consumer
        link = Link(
            id=1,
            consumer_id=999,  # Different consumer
            supplier_id=1,
            status=LinkStatus.ACCEPTED,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Setup: Mock database queries
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user
        mock_link_result = MagicMock()
        mock_link_result.scalar_one_or_none.return_value = link
        mock_consumer_result = MagicMock()
        mock_consumer_result.scalar_one_or_none.return_value = sample_consumer

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # get_current_user
                return mock_user_result
            if call_count == 2:  # Get link
                return mock_link_result
            # get_consumer_by_user_id
            return mock_consumer_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request
        response = test_client.get(
            "/api/v1/links/1",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "permission" in response.json()["detail"].lower()
