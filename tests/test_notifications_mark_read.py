"""Unit tests for PATCH /notifications/{id}/read endpoint."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from fastapi import status
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.modules.notification.model import Notification
from app.modules.user.model import User


class TestMarkNotificationRead:
    """Test cases for PATCH /api/v1/notifications/{id}/read endpoint."""

    def test_mark_notification_read_success(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
    ) -> None:
        """Test successful marking of notification as read."""
        # Create a valid access token
        access_token = create_access_token(
            data={
                "sub": sample_user.id,
                "email": sample_user.email,
                "role": sample_user.role,
            }
        )

        # Create sample notification
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

        # Second call: Get notification
        mock_notification_result = MagicMock()
        mock_notification_result.scalar_one_or_none.return_value = notification

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # get_current_user
                return mock_user_result
            # Get notification
            return mock_notification_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        # Test request
        response = test_client.patch(
            "/api/v1/notifications/1/read",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == 1
        assert data["is_read"] is True
        assert data["message"] == "Your order has been created"
        # Verify commit was called
        mock_db_session.commit.assert_called_once()
        # Verify refresh was called
        mock_db_session.refresh.assert_called_once_with(notification)

    def test_mark_notification_read_not_found(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
    ) -> None:
        """Test marking non-existent notification as read."""
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

        # Second call: Notification doesn't exist
        mock_notification_result = MagicMock()
        mock_notification_result.scalar_one_or_none.return_value = None

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # get_current_user
                return mock_user_result
            # Get notification
            return mock_notification_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request
        response = test_client.patch(
            "/api/v1/notifications/999/read",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_mark_notification_read_wrong_recipient(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
    ) -> None:
        """Test marking notification as read by wrong user."""
        # Create a valid access token
        access_token = create_access_token(
            data={
                "sub": sample_user.id,
                "email": sample_user.email,
                "role": sample_user.role,
            }
        )

        # Create notification for different user
        notification = Notification(
            id=1,
            recipient_id=999,  # Different user
            type="order_created",
            message="Your order has been created",
            is_read=False,
            created_at=datetime.now(UTC),
        )

        # Setup: Mock database queries
        # First call: get_current_user
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user

        # Second call: Get notification
        mock_notification_result = MagicMock()
        mock_notification_result.scalar_one_or_none.return_value = notification

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # get_current_user
                return mock_user_result
            # Get notification
            return mock_notification_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)

        # Test request
        response = test_client.patch(
            "/api/v1/notifications/1/read",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "permission" in response.json()["detail"].lower()

    def test_mark_notification_read_no_token(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
    ) -> None:
        """Test marking notification as read without authentication token."""
        # Test request without token
        response = test_client.patch("/api/v1/notifications/1/read")

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_mark_notification_read_invalid_token(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
    ) -> None:
        """Test marking notification as read with invalid token."""
        # Test request with invalid token
        response = test_client.patch(
            "/api/v1/notifications/1/read",
            headers={"Authorization": "Bearer invalid.token.here"},
        )

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        # Headers are case-insensitive in HTTP - check if WWW-Authenticate header exists
        header_keys_lower = [k.lower() for k in response.headers]
        assert "www-authenticate" in header_keys_lower

    def test_mark_notification_read_already_read(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
    ) -> None:
        """Test marking already read notification as read (should still work)."""
        # Create a valid access token
        access_token = create_access_token(
            data={
                "sub": sample_user.id,
                "email": sample_user.email,
                "role": sample_user.role,
            }
        )

        # Create already read notification
        notification = Notification(
            id=1,
            recipient_id=sample_user.id,
            type="order_created",
            message="Your order has been created",
            is_read=True,  # Already read
            created_at=datetime.now(UTC),
        )

        # Setup: Mock database queries
        # First call: get_current_user
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user

        # Second call: Get notification
        mock_notification_result = MagicMock()
        mock_notification_result.scalar_one_or_none.return_value = notification

        call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # get_current_user
                return mock_user_result
            # Get notification
            return mock_notification_result

        mock_db_session.execute = AsyncMock(side_effect=execute_side_effect)
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        # Test request
        response = test_client.patch(
            "/api/v1/notifications/1/read",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_read"] is True  # Should still be True
        # Verify commit was called
        mock_db_session.commit.assert_called_once()
