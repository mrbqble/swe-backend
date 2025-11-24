"""Unit tests for GET /notifications endpoint."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.modules.notification.model import Notification
from app.modules.user.model import User


class TestGetNotifications:
    """Test cases for GET /api/v1/notifications endpoint."""

    @pytest.mark.filterwarnings("ignore::RuntimeWarning:unittest.mock")
    def test_get_notifications_success(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
    ) -> None:
        """Test successful retrieval of notifications."""
        # Create a valid access token
        access_token = create_access_token(
            data={
                "sub": sample_user.id,
                "email": sample_user.email,
                "role": sample_user.role,
            }
        )

        # Create sample notifications
        notification1 = Notification(
            id=1,
            recipient_id=sample_user.id,
            type="order_created",
            message="Your order has been created",
            is_read=False,
            created_at=datetime.now(UTC),
        )
        notification2 = Notification(
            id=2,
            recipient_id=sample_user.id,
            type="order_updated",
            message="Your order has been updated",
            is_read=True,
            created_at=datetime.now(UTC),
        )

        # Setup: Mock database queries
        # First call: get_current_user (get_user_by_id)
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user

        # Second call: Count query
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 2

        # Third call: Main query
        mock_main_result = MagicMock()
        mock_main_result.scalars.return_value.all.return_value = [
            notification1,
            notification2,
        ]

        # Set up execute to return different results based on call order
        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # get_current_user
                return mock_user_result
            if call_count == 2:  # Count query
                return mock_count_result
            # Main query
            return mock_main_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request
        response = test_client.get(
            "/api/v1/notifications",
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
        assert data["page"] == 1
        assert len(data["items"]) == 2
        assert data["items"][0]["id"] == 1
        assert data["items"][0]["message"] == "Your order has been created"
        assert data["items"][0]["is_read"] is False

    def test_get_notifications_filter_read(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
    ) -> None:
        """Test filtering notifications by read status."""
        # Create a valid access token
        access_token = create_access_token(
            data={
                "sub": sample_user.id,
                "email": sample_user.email,
                "role": sample_user.role,
            }
        )

        # Create sample unread notification
        notification = Notification(
            id=1,
            recipient_id=sample_user.id,
            type="order_created",
            message="Your order has been created",
            is_read=False,
            created_at=datetime.now(UTC),
        )

        # Setup: Mock database queries
        # First call: get_current_user
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user

        # Second call: Count query
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 1

        # Third call: Main query
        mock_main_result = MagicMock()
        mock_main_result.scalars.return_value.all.return_value = [notification]

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # get_current_user
                return mock_user_result
            if call_count == 2:  # Count query
                return mock_count_result
            # Main query
            return mock_main_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request with filter
        response = test_client.get(
            "/api/v1/notifications?is_read=false",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["is_read"] is False

    def test_get_notifications_pagination(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
    ) -> None:
        """Test pagination of notifications."""
        # Create a valid access token
        access_token = create_access_token(
            data={
                "sub": sample_user.id,
                "email": sample_user.email,
                "role": sample_user.role,
            }
        )

        # Setup: Mock database queries
        # First call: get_current_user
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user

        # Second call: Count query
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 25  # Total 25 notifications

        # Third call: Main query
        mock_main_result = MagicMock()
        mock_main_result.scalars.return_value.all.return_value = []  # Empty page 2

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # get_current_user
                return mock_user_result
            if call_count == 2:  # Count query
                return mock_count_result
            # Main query
            return mock_main_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request with pagination
        response = test_client.get(
            "/api/v1/notifications?page=2&size=20",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 2
        assert data["size"] == 20
        assert data["total"] == 25
        assert data["pages"] == 2  # 25 items / 20 per page = 2 pages

    def test_get_notifications_no_token(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
    ) -> None:
        """Test get notifications without authentication token."""
        # Test request without token
        response = test_client.get("/api/v1/notifications")

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_notifications_invalid_token(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
    ) -> None:
        """Test get notifications with invalid token."""
        # Test request with invalid token
        response = test_client.get(
            "/api/v1/notifications",
            headers={"Authorization": "Bearer invalid.token.here"},
        )

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        # Headers are case-insensitive in HTTP - check if WWW-Authenticate header exists
        header_keys_lower = [k.lower() for k in response.headers]
        assert "www-authenticate" in header_keys_lower

    def test_get_notifications_empty_list(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
    ) -> None:
        """Test get notifications when user has no notifications."""
        # Create a valid access token
        access_token = create_access_token(
            data={
                "sub": sample_user.id,
                "email": sample_user.email,
                "role": sample_user.role,
            }
        )

        # Setup: Mock database queries - no notifications
        # First call: get_current_user
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user

        # Second call: Count query
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 0

        # Third call: Main query
        mock_main_result = MagicMock()
        mock_main_result.scalars.return_value.all.return_value = []

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # get_current_user
                return mock_user_result
            if call_count == 2:  # Count query
                return mock_count_result
            # Main query
            return mock_main_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request
        response = test_client.get(
            "/api/v1/notifications",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0
        assert data["page"] == 1
