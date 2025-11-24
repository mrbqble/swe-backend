"""Unit tests for authentication signup route."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

from fastapi import status
from fastapi.testclient import TestClient

from app.core.constants import ErrorMessages
from app.modules.consumer.model import Consumer
from app.modules.user.model import User


class TestSignup:
    """Test cases for signup endpoint."""

    def test_signup_success_consumer(
        self, test_client: TestClient, mock_db_session: AsyncMock, override_get_db: Any
    ) -> None:
        """Test successful consumer signup."""
        # Setup: No existing user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Mock flush to set user.id
        async def mock_flush():
            # Simulate user.id being set after flush
            pass

        mock_db_session.flush = AsyncMock(side_effect=mock_flush)

        # Mock commit
        mock_db_session.commit = AsyncMock()

        # Mock refresh
        async def mock_refresh(obj: Any) -> None:
            if isinstance(obj, (User, Consumer)):
                obj.id = 1

        mock_db_session.refresh = AsyncMock(side_effect=mock_refresh)

        # Test request
        response = test_client.post(
            "/api/v1/auth/signup",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123",
                "first_name": "New",
                "last_name": "User",
                "role": "consumer",
            },
        )

        # Assertions
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert mock_db_session.add.call_count == 2  # User and Consumer
        assert mock_db_session.commit.called

    def test_signup_success_supplier_owner(
        self, test_client: TestClient, mock_db_session: AsyncMock, override_get_db: Any
    ) -> None:
        """Test successful supplier owner signup."""
        # Setup: No existing user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Mock flush and commit
        mock_db_session.flush = AsyncMock()
        mock_db_session.commit = AsyncMock()

        # Mock refresh
        async def mock_refresh(obj: Any) -> None:
            if isinstance(obj, User):
                obj.id = 1

        mock_db_session.refresh = AsyncMock(side_effect=mock_refresh)

        # Test request
        response = test_client.post(
            "/api/v1/auth/signup",
            json={
                "email": "supplier@example.com",
                "password": "SecurePass123",
                "first_name": "Supplier",
                "last_name": "Owner",
                "role": "supplier_owner",
            },
        )

        # Assertions
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert mock_db_session.add.call_count == 1  # Only User
        assert mock_db_session.commit.called

    def test_signup_email_already_registered(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        override_get_db: Any,
        sample_user: User,
    ) -> None:
        """Test signup with already registered email."""
        # Setup: User already exists
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Test request
        response = test_client.post(
            "/api/v1/auth/signup",
            json={
                "email": "test@example.com",
                "password": "SecurePass123",
                "first_name": "Test",
                "last_name": "User",
                "role": "consumer",
            },
        )

        # Assertions
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert ErrorMessages.EMAIL_ALREADY_REGISTERED in response.json()["detail"]
        assert not mock_db_session.add.called

    def test_signup_invalid_password_too_short(
        self, test_client: TestClient, mock_db_session: AsyncMock, override_get_db: Any
    ) -> None:
        """Test signup with password that's too short."""
        # Setup: No existing user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Test request
        response = test_client.post(
            "/api/v1/auth/signup",
            json={
                "email": "newuser@example.com",
                "password": "Short1",  # Too short (Pydantic validation)
                "first_name": "New",
                "last_name": "User",
                "role": "consumer",
            },
        )

        # Assertions
        # Password length is validated by Pydantic schema (min_length=8), so returns 422
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        # Check that validation error mentions password length
        response_data = response.json()
        assert "validation error" in response_data["detail"].lower() or any(
            "password" in str(error).lower() and "8" in str(error)
            for error in response_data.get("meta", {}).get("errors", [])
        )
        assert not mock_db_session.add.called

    def test_signup_invalid_password_no_uppercase(
        self, test_client: TestClient, mock_db_session: AsyncMock, override_get_db: Any
    ) -> None:
        """Test signup with password missing uppercase letter."""
        # Setup: No existing user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Test request
        response = test_client.post(
            "/api/v1/auth/signup",
            json={
                "email": "newuser@example.com",
                "password": "lowercase123",  # No uppercase
                "first_name": "New",
                "last_name": "User",
                "role": "consumer",
            },
        )

        # Assertions
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "uppercase" in response.json()["detail"].lower()
        assert not mock_db_session.add.called

    def test_signup_invalid_password_no_digit(
        self, test_client: TestClient, mock_db_session: AsyncMock, override_get_db: Any
    ) -> None:
        """Test signup with password missing digit."""
        # Setup: No existing user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Test request
        response = test_client.post(
            "/api/v1/auth/signup",
            json={
                "email": "newuser@example.com",
                "password": "NoDigitsHere",  # No digit
                "first_name": "New",
                "last_name": "User",
                "role": "consumer",
            },
        )

        # Assertions
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "digit" in response.json()["detail"].lower()
        assert not mock_db_session.add.called

    def test_signup_with_organization_name(
        self, test_client: TestClient, mock_db_session: AsyncMock, override_get_db: Any
    ) -> None:
        """Test consumer signup with custom organization name."""
        # Setup: No existing user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Mock flush and commit
        mock_db_session.flush = AsyncMock()
        mock_db_session.commit = AsyncMock()

        # Mock refresh
        async def mock_refresh(obj: Any) -> None:
            if isinstance(obj, (User, Consumer)):
                obj.id = 1

        mock_db_session.refresh = AsyncMock(side_effect=mock_refresh)

        # Test request
        response = test_client.post(
            "/api/v1/auth/signup",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123",
                "first_name": "New",
                "last_name": "User",
                "role": "consumer",
                "organization_name": "Custom Org Name",
            },
        )

        # Assertions
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "access_token" in data
        assert mock_db_session.add.call_count == 2  # User and Consumer
