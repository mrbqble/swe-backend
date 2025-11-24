"""Unit tests for POST /links/requests endpoint."""

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


class TestCreateLinkRequest:
    """Test cases for POST /api/v1/links/requests endpoint."""

    @pytest.mark.filterwarnings("ignore::RuntimeWarning:unittest.mock")
    def test_create_link_request_success(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
        sample_consumer: Consumer,
    ) -> None:
        """Test successful creation of link request."""
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

        # Create sample link (after creation)
        link = Link(
            id=1,
            consumer_id=sample_consumer.id,
            supplier_id=1,
            status=LinkStatus.PENDING,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Setup: Mock database queries in order
        # 1. get_current_user
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user

        # 2. get_consumer_by_user_id
        mock_consumer_result = MagicMock()
        mock_consumer_result.scalar_one_or_none.return_value = sample_consumer

        # 3. Get supplier
        mock_supplier_result = MagicMock()
        mock_supplier_result.scalar_one_or_none.return_value = supplier

        # 4. Check existing link (returns None)
        mock_existing_link_result = MagicMock()
        mock_existing_link_result.scalar_one_or_none.return_value = None

        # 5. Get link with relationships (after creation)
        mock_link_result = MagicMock()
        mock_link_result.scalar_one.return_value = link

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
            if call_count == 4:  # Check existing link
                return mock_existing_link_result
            # Get link with relationships
            return mock_link_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        # Test request
        response = test_client.post(
            "/api/v1/links/requests",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"supplier_id": 1},
        )

        # Assertions
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] == 1
        assert data["consumer_id"] == sample_consumer.id
        assert data["supplier_id"] == 1
        assert data["status"] == LinkStatus.PENDING.value
        # Verify commit was called
        mock_db_session.commit.assert_called_once()

    def test_create_link_request_not_consumer(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_supplier_owner: User,
    ) -> None:
        """Test create link request with non-consumer role."""
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
        response = test_client.post(
            "/api/v1/links/requests",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"supplier_id": 1},
        )

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_link_request_consumer_not_found(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
    ) -> None:
        """Test create link request when consumer profile not found."""
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
        response = test_client.post(
            "/api/v1/links/requests",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"supplier_id": 1},
        )

        # Assertions
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Consumer profile not found" in response.json()["detail"]

    def test_create_link_request_supplier_not_found(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
        sample_consumer: Consumer,
    ) -> None:
        """Test create link request when supplier not found."""
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
        mock_consumer_result = MagicMock()
        mock_consumer_result.scalar_one_or_none.return_value = sample_consumer
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
        response = test_client.post(
            "/api/v1/links/requests",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"supplier_id": 999},
        )

        # Assertions
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Supplier not found" in response.json()["detail"]

    def test_create_link_request_already_exists(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
        sample_consumer: Consumer,
    ) -> None:
        """Test create link request when link already exists."""
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

        # Create existing link
        existing_link = Link(
            id=1,
            consumer_id=sample_consumer.id,
            supplier_id=1,
            status=LinkStatus.PENDING,
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
        mock_existing_link_result = MagicMock()
        mock_existing_link_result.scalar_one_or_none.return_value = existing_link

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
            # Check existing link
            return mock_existing_link_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request
        response = test_client.post(
            "/api/v1/links/requests",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"supplier_id": 1},
        )

        # Assertions
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in response.json()["detail"].lower()

    def test_create_link_request_no_token(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
    ) -> None:
        """Test create link request without authentication token."""
        # Test request without token
        response = test_client.post(
            "/api/v1/links/requests",
            json={"supplier_id": 1},
        )

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
