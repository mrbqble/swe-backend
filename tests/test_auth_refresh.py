"""Unit tests for authentication refresh token route."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

from fastapi import status
from fastapi.testclient import TestClient

from app.core.constants import ErrorMessages
from app.modules.user.model import User


class TestRefresh:
    """Test cases for refresh token endpoint."""

    def test_refresh_success(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
    ) -> None:
        """Test successful token refresh."""
        from app.core.security import create_refresh_token

        # Create a valid refresh token
        refresh_token = create_refresh_token(data={"sub": sample_user.id})

        # Setup: User exists and is active
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Test request
        response = test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_invalid_token(
        self, test_client: TestClient, mock_db_session: AsyncMock, override_get_db: Any
    ) -> None:
        """Test refresh with invalid token."""
        # Test request with invalid token
        response = test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert ErrorMessages.INVALID_REFRESH_TOKEN in response.json()["detail"]
        # Headers are case-insensitive in HTTP - check if WWW-Authenticate header exists
        header_keys_lower = [k.lower() for k in response.headers]
        assert "www-authenticate" in header_keys_lower

    def test_refresh_expired_token(
        self, test_client: TestClient, mock_db_session: AsyncMock, override_get_db: Any
    ) -> None:
        """Test refresh with expired token."""
        from datetime import timedelta

        from app.core.security import create_refresh_token

        # Create an expired refresh token
        refresh_token = create_refresh_token(
            data={"sub": 1}, expires_delta=timedelta(seconds=-1)
        )

        # Test request
        response = test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert ErrorMessages.INVALID_REFRESH_TOKEN in response.json()["detail"]

    def test_refresh_user_not_found(
        self, test_client: TestClient, mock_db_session: AsyncMock, override_get_db: Any
    ) -> None:
        """Test refresh with token for non-existent user."""
        from app.core.security import create_refresh_token

        # Create a valid refresh token for non-existent user
        refresh_token = create_refresh_token(data={"sub": 99999})

        # Setup: User doesn't exist
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Test request
        response = test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert ErrorMessages.USER_NOT_FOUND_OR_INACTIVE in response.json()["detail"]

    def test_refresh_inactive_user(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_inactive_user: User,
    ) -> None:
        """Test refresh with token for inactive user."""
        from app.core.security import create_refresh_token

        # Create a valid refresh token
        refresh_token = create_refresh_token(data={"sub": sample_inactive_user.id})

        # Setup: User exists but is inactive
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_inactive_user
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Test request
        response = test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert ErrorMessages.USER_NOT_FOUND_OR_INACTIVE in response.json()["detail"]

    def test_refresh_access_token_instead_of_refresh_token(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
    ) -> None:
        """Test refresh with access token instead of refresh token."""
        from app.core.security import create_access_token

        # Create an access token (not a refresh token)
        access_token = create_access_token(
            data={
                "sub": sample_user.id,
                "email": sample_user.email,
                "role": sample_user.role,
            }
        )

        # Test request
        response = test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert ErrorMessages.INVALID_REFRESH_TOKEN in response.json()["detail"]
