"""Phone number utilities."""

import re


def normalize_phone(phone: str) -> str:
    """Strip formatting and ensure E.164 format with + prefix."""
    cleaned = re.sub(r"[\s\-\(\)]", "", phone)
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    return cleaned


def validate_e164(phone: str) -> bool:
    """Return True if phone matches E.164 format: +[1-9] followed by 6-14 digits."""
    return bool(re.match(r"^\+[1-9]\d{6,14}$", phone))
