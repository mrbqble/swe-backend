"""Unit tests for the health check endpoint."""

import warnings
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import status

from app.schemas.common import HealthCheckResponse


class TestHealthCheck:
    """Test cases for GET /health endpoint."""

    def test_health_check_database_ok(self, test_client):
        """Test health check when database is healthy."""
        # Arrange - Mock successful database connection
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=(1,))
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=mock_result)
        mock_conn.commit = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)

        with patch("app.api.main.engine") as mock_engine:
            mock_engine.connect = MagicMock(return_value=mock_conn)

            # Act
            response = test_client.get("/health")

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        assert "env" in data
        assert "db" in data
        assert data["status"] == "ok"
        assert data["db"] == "ok"
        # Validate response matches schema
        HealthCheckResponse.model_validate(data)

    def test_health_check_database_error(self, test_client):
        """Test health check when database connection fails."""
        # Arrange - Mock database connection failure
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(
            side_effect=Exception("Database connection failed")
        )
        mock_conn.__aexit__ = AsyncMock(return_value=None)

        with patch("app.api.main.engine") as mock_engine:
            mock_engine.connect = MagicMock(return_value=mock_conn)

            # Act
            response = test_client.get("/health")

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        assert "env" in data
        assert "db" in data
        assert data["status"] == "degraded"
        assert data["db"] == "error"
        # Validate response matches schema
        HealthCheckResponse.model_validate(data)

    def test_health_check_database_timeout(self, test_client):
        """Test health check when database query times out."""
        # Arrange - Mock asyncio.wait_for to raise TimeoutError
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("app.api.main.engine") as mock_engine,
            patch("app.api.main.asyncio.wait_for") as mock_wait_for,
        ):
            mock_engine.connect = MagicMock(return_value=mock_conn)
            mock_wait_for.side_effect = TimeoutError()

            # Act
            response = test_client.get("/health")

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        assert "env" in data
        assert "db" in data
        assert data["status"] == "degraded"
        assert data["db"] == "error"
        # Validate response matches schema
        HealthCheckResponse.model_validate(data)

    def test_health_check_database_connection_error(self, test_client):
        """Test health check when database connection raises an exception."""

        # Arrange - Mock database connection that raises exception
        # engine.connect() is synchronous but returns an async context manager
        # Use a plain function to avoid creating async mocks
        def connect_raises_exception():
            raise Exception("Connection refused")

        with patch("app.api.main.engine") as mock_engine:
            mock_engine.connect = connect_raises_exception

            # Suppress RuntimeWarning about unawaited coroutines from AsyncMock
            # This is a known limitation when testing async code with mocks
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message=".*coroutine.*AsyncMockMixin.*was never awaited.*",
                    category=RuntimeWarning,
                )
                # Act
                response = test_client.get("/health")

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        assert "env" in data
        assert "db" in data
        assert data["status"] == "degraded"
        assert data["db"] == "error"
        # Validate response matches schema
        HealthCheckResponse.model_validate(data)

    def test_health_check_database_execute_error(self, test_client):
        """Test health check when database execute raises an exception."""

        # Arrange - Mock database execute failure
        # Use a proper async context manager class with execute that raises
        class MockConnection:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            async def execute(self, *args, **kwargs):
                raise Exception("Query execution failed")

            async def commit(self):
                pass

        mock_conn = MockConnection()

        with patch("app.api.main.engine") as mock_engine:
            mock_engine.connect = MagicMock(return_value=mock_conn)

            # Suppress RuntimeWarning about unawaited coroutines from AsyncMock
            # This is a known limitation when testing async code with mocks
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message=".*coroutine.*AsyncMockMixin.*was never awaited.*",
                    category=RuntimeWarning,
                )
                # Act
                response = test_client.get("/health")

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        assert "env" in data
        assert "db" in data
        assert data["status"] == "degraded"
        assert data["db"] == "error"
        # Validate response matches schema
        HealthCheckResponse.model_validate(data)
