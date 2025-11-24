"""Pytest configuration and fixtures."""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.roles import Role
from app.main import app
from app.modules.consumer.model import Consumer
from app.modules.user.model import User
from app.utils.hashing import hash_password


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.scalar_one_or_none = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def test_client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_user() -> User:
    """Create a sample user for testing."""
    return User(
        id=1,
        email="test@example.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="Test",
        last_name="User",
        role=Role.CONSUMER.value,
        is_active=True,
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_inactive_user() -> User:
    """Create a sample inactive user for testing."""
    return User(
        id=2,
        email="inactive@example.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="Inactive",
        last_name="User",
        role=Role.CONSUMER.value,
        is_active=False,
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_supplier_owner() -> User:
    """Create a sample supplier owner user for testing."""
    return User(
        id=3,
        email="supplier@example.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="Supplier",
        last_name="Owner",
        role=Role.SUPPLIER_OWNER.value,
        is_active=True,
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_consumer() -> Consumer:
    """Create a sample consumer for testing."""
    return Consumer(
        id=1,
        user_id=1,
        organization_name="Test Organization",
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def override_get_db(mock_db_session: AsyncMock):
    """
    Override the get_db dependency in the app.

    This fixture ensures proper cleanup of dependency overrides after each test,
    even if the test fails. Tests are completely independent and can run in any order.
    """
    from app.db.session import get_db

    async def _get_db():
        yield mock_db_session

    app.dependency_overrides[get_db] = _get_db
    yield
    # Cleanup happens automatically via yield, even if test fails
    app.dependency_overrides.clear()
