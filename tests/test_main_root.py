"""Unit tests for the root endpoint."""

from fastapi import status

from app.schemas.common import MessageResponse


class TestRoot:
    """Test cases for GET / endpoint."""

    def test_root_success(self, test_client):
        """Test that root endpoint returns correct message."""
        # Act
        response = test_client.get("/")

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert data["message"] == "Hello World"
        # Validate response matches schema
        MessageResponse.model_validate(data)
