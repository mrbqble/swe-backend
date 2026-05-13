"""Mock stat.gov.kz verification API."""

from app.core.config import settings


async def verify_iin_bin(iin_bin: str) -> dict | None:
    """Verify IIN/BIN against the state registry.

    Returns None if not found, or a dict with name/status/type on success.
    """
    if not (iin_bin.isdigit() and len(iin_bin) == 12):
        return None

    if settings.ENV == "dev":
        if iin_bin.endswith("0000"):
            return None
        entity_type = "too" if iin_bin[0] in ("4", "5", "6") else "ip"
        return {"name": "Test Business Name", "status": "active", "type": entity_type}

    # TODO: implement actual stat.gov.kz API call when credentials are available
    # try:
    #     async with httpx.AsyncClient(timeout=10) as client:
    #         resp = await client.get(f"https://stat.gov.kz/api/...", params={"bin": iin_bin})
    #         ...
    # except Exception:
    return {"name": None, "status": "pending_manual"}
