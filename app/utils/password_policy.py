"""Password policy validation utilities."""

import re

from app.core.config import settings


class PasswordPolicyError(ValueError):
    """Raised when password doesn't meet policy requirements."""


def validate_password_policy(password: str) -> None:
    """
    Validate password against policy requirements.

    Raises:
        PasswordPolicyError: If password doesn't meet requirements.
    """
    errors: list[str] = []

    if len(password) < settings.PASSWORD_MIN_LENGTH:
        errors.append(
            f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters long"
        )

    if settings.PASSWORD_REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")

    if settings.PASSWORD_REQUIRE_LOWERCASE and not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")

    if settings.PASSWORD_REQUIRE_DIGIT and not re.search(r"\d", password):
        errors.append("Password must contain at least one digit")

    if settings.PASSWORD_REQUIRE_SPECIAL and not re.search(
        r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password
    ):
        errors.append("Password must contain at least one special character")

    if errors:
        raise PasswordPolicyError("; ".join(errors))
