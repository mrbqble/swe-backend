import os

import pytest_asyncio
from httpx import AsyncClient

os.environ.setdefault("APP_ENV", "test")

def get_app():
    from app.main import app
    return app


@pytest_asyncio.fixture
async def async_client() -> AsyncClient:
    async with AsyncClient(app=get_app(), base_url="http://testserver") as client:
        yield client
