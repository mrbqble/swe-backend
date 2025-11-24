"""Unit tests for user get_me route."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

from fastapi import status
from fastapi.testclient import TestClient

from app.core.roles import Role
from app.core.security import create_access_token
from app.modules.user.model import User


class TestGetMe:
    """Test cases for get_me endpoint."""

    def test_get_me_success(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
    ) -> None:
        """Test successful retrieval of current user."""
        # Create a valid access token
        access_token = create_access_token(
            data={
                "sub": sample_user.id,
                "email": sample_user.email,
                "role": sample_user.role,
            }
        )

        # Setup: User exists
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Test request
        response = test_client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == sample_user.id
        assert data["email"] == sample_user.email
        assert data["first_name"] == sample_user.first_name
        assert data["last_name"] == sample_user.last_name
        assert data["role"] == sample_user.role
        assert data["is_active"] == sample_user.is_active

    def test_get_me_no_token(
        self, test_client: TestClient, mock_db_session: AsyncMock, override_get_db: Any
    ) -> None:
        """Test get_me without authentication token."""
        # Test request without token
        response = test_client.get("/api/v1/users/me")

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_me_invalid_token(
        self, test_client: TestClient, mock_db_session: AsyncMock, override_get_db: Any
    ) -> None:
        """Test get_me with invalid token."""
        # Test request with invalid token
        response = test_client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        # Headers are case-insensitive in HTTP - check if WWW-Authenticate header exists
        header_keys_lower = [k.lower() for k in response.headers]
        assert "www-authenticate" in header_keys_lower

    def test_get_me_expired_token(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
    ) -> None:
        """Test get_me with expired token."""
        from datetime import timedelta

        from app.core.security import create_access_token

        # Create an expired access token
        access_token = create_access_token(
            data={
                "sub": sample_user.id,
                "email": sample_user.email,
                "role": sample_user.role,
            },
            expires_delta=timedelta(seconds=-1),
        )

        # Test request
        response = test_client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        # Headers are case-insensitive in HTTP - check if WWW-Authenticate header exists
        header_keys_lower = [k.lower() for k in response.headers]
        assert "www-authenticate" in header_keys_lower

    def test_get_me_user_not_found(
        self, test_client: TestClient, mock_db_session: AsyncMock, override_get_db: Any
    ) -> None:
        """Test get_me with token for non-existent user."""
        # Create a valid access token for non-existent user
        access_token = create_access_token(
            data={
                "sub": 99999,
                "email": "nonexistent@example.com",
                "role": Role.CONSUMER.value,
            }
        )

        # Setup: User doesn't exist
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Test request
        response = test_client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        # Headers are case-insensitive in HTTP - check if WWW-Authenticate header exists
        header_keys_lower = [k.lower() for k in response.headers]
        assert "www-authenticate" in header_keys_lower

    def test_get_me_inactive_user(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_inactive_user: User,
    ) -> None:
        """Test get_me with token for inactive user."""
        # Create a valid access token
        access_token = create_access_token(
            data={
                "sub": sample_inactive_user.id,
                "email": sample_inactive_user.email,
                "role": sample_inactive_user.role,
            }
        )

        # Setup: User exists but is inactive
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_inactive_user
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Test request
        response = test_client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_me_different_roles(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_supplier_owner: User,
    ) -> None:
        """Test get_me with different user roles."""
        # Create a valid access token for supplier owner
        access_token = create_access_token(
            data={
                "sub": sample_supplier_owner.id,
                "email": sample_supplier_owner.email,
                "role": sample_supplier_owner.role,
            }
        )

        # Setup: User exists
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_supplier_owner
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Test request
        response = test_client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["role"] == Role.SUPPLIER_OWNER.value
        assert data["email"] == sample_supplier_owner.email
