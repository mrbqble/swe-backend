import pytest


@pytest.mark.asyncio
async def test_validation_error_returns_standard_payload(async_client):
    response = await async_client.get("/api/v1/users/not-an-int")
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["detail"] == "Validation error"
    assert "errors" in body["meta"]


@pytest.mark.asyncio
async def test_internal_error_returns_standard_payload(async_client):
    response = await async_client.get("/api/v1/users/error")
    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "internal_server_error"
    assert body["detail"] == "Simulated failure"
