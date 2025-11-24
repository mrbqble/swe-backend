"""Unit tests for authentication login route."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

from fastapi import status
from fastapi.testclient import TestClient

from app.core.constants import ErrorMessages
from app.modules.user.model import User


class TestLogin:
    """Test cases for login endpoint."""

    def test_login_success(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
    ) -> None:
        """Test successful login."""
        # Setup: User exists with correct password
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Test request
        response = test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "TestPassword123!",
            },
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_user_not_found(
        self, test_client: TestClient, mock_db_session: AsyncMock, override_get_db: Any
    ) -> None:
        """Test login with non-existent user."""
        # Setup: User doesn't exist
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Test request
        response = test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "SomePassword123",
            },
        )

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert ErrorMessages.INCORRECT_CREDENTIALS in response.json()["detail"]
        # Headers are case-insensitive in HTTP - check if WWW-Authenticate header exists
        header_keys_lower = [k.lower() for k in response.headers]
        assert "www-authenticate" in header_keys_lower

    def test_login_incorrect_password(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
    ) -> None:
        """Test login with incorrect password."""
        # Setup: User exists but wrong password
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Test request
        response = test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "WrongPassword123",
            },
        )

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert ErrorMessages.INCORRECT_CREDENTIALS in response.json()["detail"]
        # Headers are case-insensitive in HTTP - check if WWW-Authenticate header exists
        header_keys_lower = [k.lower() for k in response.headers]
        assert "www-authenticate" in header_keys_lower

    def test_login_inactive_user(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_inactive_user: User,
    ) -> None:
        """Test login with inactive user account."""
        # Setup: User exists but is inactive
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_inactive_user
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Test request
        response = test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "inactive@example.com",
                "password": "TestPassword123!",
            },
        )

        # Assertions
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert ErrorMessages.USER_INACTIVE in response.json()["detail"]
