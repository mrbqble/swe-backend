"""Authentication routes."""

import contextlib
import logging

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import is_mobile_client
from app.core.exceptions import ApplicationError
from app.core.roles import Role
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from app.db.session import get_db
from app.modules.auth.schema import (
    LoginRequest,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
)
from app.modules.consumer.model import Consumer
from app.modules.user.model import User
from app.utils.hashing import hash_password, verify_password
from app.utils.helpers import get_user_by_email, get_user_by_id
from app.utils.password_policy import validate_password_policy

AuthRouter = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


def _create_tokens(user: User) -> TokenResponse:
    """Create access and refresh tokens for user with role-based scopes."""
    return TokenResponse(
        access_token=create_access_token(
            data={"sub": user.id, "email": user.email, "role": user.role}
        ),
        refresh_token=create_refresh_token(data={"sub": user.id}),
        token_type="bearer",
    )


@AuthRouter.post(
    "/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account. Available roles: consumer, supplier_owner. Password must meet policy requirements. Rate limited to 10 requests per minute.",
    responses={
        201: {"description": "User created successfully"},
        400: {"description": "Invalid input or email already registered"},
        422: {"description": "Validation error"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def signup(
    request: SignupRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new user account.

    **Role Requirements:** None (public endpoint)

    **Client Restrictions:**
    - Mobile app: Only consumers can sign up
    - Web app: Only supplier owners can sign up

    **Password Policy:**
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    """
    is_mobile = is_mobile_client(http_request)

    # Mobile app: Only consumers can sign up
    if is_mobile and request.role != Role.CONSUMER:
        raise ApplicationError("Only consumers can sign up through the mobile app")

    # Web app: Only supplier owners can sign up
    if not is_mobile and request.role != Role.SUPPLIER_OWNER:
        raise ApplicationError("Only supplier owners can sign up through the web app")

    existing_user = await get_user_by_email(request.email, db)

    if existing_user:
        raise ApplicationError("Email already registered")

    # Validate password policy
    try:
        validate_password_policy(request.password)
    except ValueError as e:  # PasswordPolicyError is a ValueError subclass
        raise ApplicationError(str(e))

    password_hash = hash_password(request.password)
    user = User(
        email=request.email,
        password_hash=password_hash,
        first_name=request.first_name,
        last_name=request.last_name,
        role=request.role.value,
    )

    # Create user and consumer (if applicable) in a single commit so
    # consumer profile creation cannot silently fail after user is created.
    consumer = None
    try:
        role_value = (
            request.role.value if hasattr(
                request.role, "value") else str(request.role)
        )
        db.add(user)
        # Flush so user.id is populated for the consumer FK
        await db.flush()
        if role_value == Role.CONSUMER.value:
            org_name = getattr(request, "organization_name", None) or (
                user.email.split("@")[0]
                if user and user.email
                else f"consumer-{user.id}"
            )
            consumer = Consumer(user_id=user.id, organization_name=org_name)
            db.add(consumer)

        await db.commit()

        # Refresh the user (and consumer if created) to populate model fields
        await db.refresh(user)
        if role_value == Role.CONSUMER.value and consumer is not None:
            with contextlib.suppress(Exception):
                # If refresh fails, continue; creation likely succeeded
                await db.refresh(consumer)
    except Exception as e:
        # Rollback and surface error
        with contextlib.suppress(Exception):
            await db.rollback()
        logger.error(f"Failed to create user and consumer: {e}", exc_info=True)
        raise ApplicationError("Failed to create user account")

    return _create_tokens(user)


@AuthRouter.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate user",
    description="Authenticate user with email and password, returns JWT access and refresh tokens. Rate limited to 10 requests per minute.",
    responses={
        200: {"description": "Authentication successful"},
        401: {"description": "Invalid credentials"},
        403: {"description": "User account is inactive"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def login(
    request: LoginRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user and return tokens.

    **Role Requirements:** None (public endpoint)

    **Client Restrictions:**
    - Mobile app: Only consumers and sales representatives can login
    - Web app: Only supplier owners, managers, and sales representatives can login

    Returns JWT tokens with role-based scopes for API access.
    """
    user = await get_user_by_email(request.email, db)
    if not user:
        raise ApplicationError("Incorrect email or password")
    if not verify_password(request.password, user.password_hash):
        raise ApplicationError("Incorrect email or password")
    if not user.is_active:
        raise ApplicationError("User account is inactive")

    is_mobile = is_mobile_client(http_request)

    # Mobile app: Only consumers and sales representatives can login
    if is_mobile:
        if user.role not in [Role.CONSUMER.value, Role.SUPPLIER_SALES.value]:
            raise ApplicationError("Only consumers and sales representatives can login through the mobile app")
    else:
        # Web app: Only supplier owners, managers, and sales representatives can login
        if user.role not in [Role.SUPPLIER_OWNER.value, Role.SUPPLIER_MANAGER.value, Role.SUPPLIER_SALES.value]:
            raise ApplicationError("Only supplier owners, managers, and sales representatives can login through the web app")

    return _create_tokens(user)


@AuthRouter.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Obtain a new access token using a valid refresh token.",
    responses={
        200: {"description": "Token refreshed successfully"},
        401: {"description": "Invalid or expired refresh token"},
    },
)
async def refresh(
    request: RefreshRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token using refresh token.

    **Role Requirements:** None (public endpoint, requires valid refresh token)

    **Client Restrictions:**
    - Mobile app: Only consumers and sales representatives can refresh tokens
    - Web app: Only supplier owners, managers, and sales representatives can refresh tokens
    """
    payload = decode_refresh_token(request.refresh_token)
    if payload is None or (user_id := payload.get("sub")) is None:
        raise ApplicationError("Invalid refresh token")
    user = await get_user_by_id(user_id, db)
    if not user or not user.is_active:
        raise ApplicationError("User not found or inactive")

    is_mobile = is_mobile_client(http_request)

    # Mobile app: Only consumers and sales representatives can refresh tokens
    if is_mobile:
        if user.role not in [Role.CONSUMER.value, Role.SUPPLIER_SALES.value]:
            raise ApplicationError("Only consumers and sales representatives can refresh tokens through the mobile app")
    else:
        # Web app: Only supplier owners, managers, and sales representatives can refresh tokens
        if user.role not in [Role.SUPPLIER_OWNER.value, Role.SUPPLIER_MANAGER.value, Role.SUPPLIER_SALES.value]:
            raise ApplicationError("Only supplier owners, managers, and sales representatives can refresh tokens through the web app")

    return _create_tokens(user)
