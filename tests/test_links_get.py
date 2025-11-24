"""Unit tests for GET /links endpoint."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.modules.consumer.model import Consumer
from app.modules.link.model import Link, LinkStatus
from app.modules.user.model import User


class TestGetConsumerLinks:
    """Test cases for GET /api/v1/links endpoint."""

    @pytest.mark.filterwarnings("ignore::RuntimeWarning:unittest.mock")
    def test_get_consumer_links_success(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
        sample_consumer: Consumer,
    ) -> None:
        """Test successful retrieval of consumer links."""
        # Create a valid access token
        access_token = create_access_token(
            data={
                "sub": sample_user.id,
                "email": sample_user.email,
                "role": sample_user.role,
            }
        )

        # Create sample links
        link1 = Link(
            id=1,
            consumer_id=sample_consumer.id,
            supplier_id=1,
            status=LinkStatus.PENDING,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        link2 = Link(
            id=2,
            consumer_id=sample_consumer.id,
            supplier_id=2,
            status=LinkStatus.ACCEPTED,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Setup: Mock database queries
        # 1. get_current_user
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user

        # 2. get_consumer_by_user_id
        mock_consumer_result = MagicMock()
        mock_consumer_result.scalar_one_or_none.return_value = sample_consumer

        # 3. Count query
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 2

        # 4. Main query
        mock_links_result = MagicMock()
        mock_links_result.scalars.return_value.all.return_value = [link1, link2]

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # get_current_user
                return mock_user_result
            if call_count == 2:  # get_consumer_by_user_id
                return mock_consumer_result
            if call_count == 3:  # Count query
                return mock_count_result
            # Main query
            return mock_links_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request
        response = test_client.get(
            "/api/v1/links",
            headers={"Authorization": f"Bearer {access_token}"},
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

    def test_get_consumer_links_filter_status(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
        sample_consumer: Consumer,
    ) -> None:
        """Test filtering consumer links by status."""
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
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user
        mock_consumer_result = MagicMock()
        mock_consumer_result.scalar_one_or_none.return_value = sample_consumer
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1
        mock_links_result = MagicMock()
        mock_links_result.scalars.return_value.all.return_value = [link]

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # get_current_user
                return mock_user_result
            if call_count == 2:  # get_consumer_by_user_id
                return mock_consumer_result
            if call_count == 3:  # Count query
                return mock_count_result
            # Main query
            return mock_links_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request with status filter
        response = test_client.get(
            "/api/v1/links?status=accepted",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == LinkStatus.ACCEPTED.value

    def test_get_consumer_links_not_consumer(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_supplier_owner: User,
    ) -> None:
        """Test get consumer links with non-consumer role."""
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
            "/api/v1/links",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_consumer_links_consumer_not_found(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
    ) -> None:
        """Test get consumer links when consumer profile not found."""
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
        response = test_client.get(
            "/api/v1/links",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Consumer profile not found" in response.json()["detail"]

    def test_get_consumer_links_pagination(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
        sample_consumer: Consumer,
    ) -> None:
        """Test pagination of consumer links."""
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
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 30  # Total 30 links
        mock_links_result = MagicMock()
        mock_links_result.scalars.return_value.all.return_value = []  # Empty page 2

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # get_current_user
                return mock_user_result
            if call_count == 2:  # get_consumer_by_user_id
                return mock_consumer_result
            if call_count == 3:  # Count query
                return mock_count_result
            # Main query
            return mock_links_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request with pagination
        response = test_client.get(
            "/api/v1/links?page=2&size=20",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 2
        assert data["size"] == 20
        assert data["total"] == 30
        assert data["pages"] == 2
