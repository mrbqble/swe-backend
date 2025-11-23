"""Authentication routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ErrorMessages
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
from app.modules.user.model import User
from app.modules.consumer.model import Consumer
from app.utils.hashing import hash_password, verify_password
from app.utils.helpers import get_user_by_email, get_user_by_id
from app.utils.password_policy import validate_password_policy
from app.core.roles import Role

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
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new user account.

    **Role Requirements:** None (public endpoint)

    **Password Policy:**
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    """
    existing_user = await get_user_by_email(request.email, db)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorMessages.EMAIL_ALREADY_REGISTERED,
        )

    # Validate password policy
    try:
        validate_password_policy(request.password)
    except ValueError as e:  # PasswordPolicyError is a ValueError subclass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    password_hash = hash_password(request.password)
    user = User(
        email=request.email,
        password_hash=password_hash,
        role=request.role.value,
    )

    # Create user and consumer (if applicable) in a single commit so
    # consumer profile creation cannot silently fail after user is created.
    try:
        role_value = request.role.value if hasattr(request.role, "value") else str(request.role)
        db.add(user)
        # Flush so user.id is populated for the consumer FK
        await db.flush()
        if role_value == Role.CONSUMER.value:
            org_name = getattr(request, "organization_name", None) or (
                user.email.split("@")[0] if user and user.email else f"consumer-{user.id}"
            )
            consumer = Consumer(user_id=user.id, organization_name=org_name)
            db.add(consumer)

        await db.commit()

        # Refresh the user (and consumer if created) to populate model fields
        await db.refresh(user)
        if role_value == Role.CONSUMER.value:
            try:
                await db.refresh(consumer)
            except Exception:
                # If refresh fails, continue; creation likely succeeded
                pass
    except Exception as e:
        # Rollback and surface error
        try:
            await db.rollback()
        except Exception:
            pass
        logger.error(f"Failed to create user and consumer: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorMessages.FAILED_TO_CREATE_USER,
        )

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
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user and return tokens.

    **Role Requirements:** None (public endpoint)

    Returns JWT tokens with role-based scopes for API access.
    """
    user = await get_user_by_email(request.email, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorMessages.INCORRECT_CREDENTIALS,
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorMessages.INCORRECT_CREDENTIALS,
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ErrorMessages.USER_INACTIVE,
        )
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
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token using refresh token.

    **Role Requirements:** None (public endpoint, requires valid refresh token)
    """
    payload = decode_refresh_token(request.refresh_token)
    if payload is None or (user_id := payload.get("sub")) is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorMessages.INVALID_REFRESH_TOKEN,
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await get_user_by_id(user_id, db)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorMessages.USER_NOT_FOUND_OR_INACTIVE,
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _create_tokens(user)
