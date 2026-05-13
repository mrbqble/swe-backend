"""Mock Kaspi payment API."""

from app.core.config import settings


async def create_kaspi_payment(order_id: int, amount: int) -> dict:
    if settings.ENV == "dev":
        return {
            "payment_url": f"https://mock-kaspi.kz/pay/ORDER_{order_id}",
            "payment_id": f"KASPI_DEV_{order_id}",
            "qr_token": "mock_qr_token",
        }
    # TODO: implement actual Kaspi QR API call when credentials are available
    raise NotImplementedError("Kaspi credentials not configured")


async def verify_kaspi_payment(payment_id: str) -> bool:
    if settings.ENV == "dev":
        return True
    # TODO: implement actual Kaspi verification
    raise NotImplementedError("Kaspi verification not configured")
