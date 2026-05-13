"""Authentication routes."""

import hashlib
import logging
import random
import secrets
import string
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.exceptions import ApplicationError
from app.db.session import get_db
from app.modules.auth.model import OtpCode, Session
from app.modules.auth.schema import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    SendOtpRequest,
    TokenResponse,
    VerifyOtpRequest,
)
from app.modules.user.model import User
from app.utils.hashing import hash_password, verify_password
from app.utils.helpers import get_user_by_email, get_user_by_phone

AuthRouter = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)

_DEV_OTP = "000000"


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _make_access_token(user: User) -> str:
    from app.core.security import create_access_token
    return create_access_token(
        data={"sub": str(user.id), "phone": user.phone, "role": user.status_tier}
    )


def _make_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def _build_token_response(access_token: str, refresh_token: str) -> TokenResponse:
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


async def _create_session(user: User, refresh_token: str, request: Request, db: AsyncSession) -> Session:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    session = Session(
        user_id=user.id,
        refresh_token_hash=_hash_token(refresh_token),
        ip=request.client.host if request.client else None,
        expires_at=expires_at,
        last_used_at=datetime.now(UTC),
    )
    db.add(session)
    await db.flush()
    return session


async def _count_recent_otp_sends(phone: str, db: AsyncSession) -> int:
    window = datetime.now(UTC) - timedelta(minutes=settings.OTP_RESEND_WINDOW_MINUTES)
    result = await db.execute(
        select(func.count()).where(
            OtpCode.phone == phone,
            OtpCode.created_at >= window,
        )
    )
    return result.scalar_one()


async def _get_active_otp(phone: str, db: AsyncSession) -> OtpCode | None:
    result = await db.execute(
        select(OtpCode)
        .where(
            OtpCode.phone == phone,
            OtpCode.is_used == False,  # noqa: E712
            OtpCode.expires_at > datetime.now(UTC),
        )
        .order_by(OtpCode.created_at.desc())
    )
    return result.scalars().first()


def _gen_ref_code() -> str:
    digits = "".join(random.choices(string.digits, k=6))
    return f"ICR{digits}"


@AuthRouter.post("/send-otp", status_code=status.HTTP_200_OK)
async def send_otp(
    request: SendOtpRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Send OTP to phone. In dev mode, always sends 000000 (no delivery)."""
    phone = request.phone

    send_count = await _count_recent_otp_sends(phone, db)
    if send_count >= settings.OTP_RESEND_LIMIT:
        raise ApplicationError(
            f"Too many OTP requests. Try again in {settings.OTP_RESEND_WINDOW_MINUTES} minutes.",
            status_code=429,
        )

    if settings.ENV == "dev":
        code = _DEV_OTP
        channel = "mock"
        logger.info(f"DEV OTP for {phone}: {code}")
    else:
        # Production: deliver via WhatsApp, SMS fallback
        raise NotImplementedError(
            "OTP delivery not configured — set TWILIO credentials"
        )

    expires_at = datetime.now(UTC) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
    otp = OtpCode(
        phone=phone,
        code_hash=_hash_token(code),
        channel=channel,
        expires_at=expires_at,
    )
    db.add(otp)
    await db.commit()

    return {"message": "Code sent", "channel": channel}


@AuthRouter.post("/verify-otp", status_code=status.HTTP_200_OK)
async def verify_otp(
    request: VerifyOtpRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Verify OTP code. Returns verified status and whether phone is registered."""
    phone = request.phone
    code = request.code

    # In dev mode, accept 000000 directly without checking DB
    if settings.ENV == "dev" and code == _DEV_OTP:
        user = await get_user_by_phone(phone, db)
        return {"verified": True, "is_registered": user is not None}

    otp = await _get_active_otp(phone, db)
    if otp is None:
        raise ApplicationError("No active OTP found for this phone. Request a new code.")

    otp.attempts += 1

    if otp.attempts > settings.OTP_MAX_ATTEMPTS:
        await db.commit()
        raise ApplicationError(
            f"Too many failed attempts. Request a new code after {settings.OTP_BLOCK_MINUTES} minutes.",
            status_code=429,
        )

    if otp.code_hash != _hash_token(code):
        await db.commit()
        raise ApplicationError("Invalid OTP code.")

    otp.is_used = True
    await db.commit()

    user = await get_user_by_phone(phone, db)
    return {"verified": True, "is_registered": user is not None}


@AuthRouter.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Register a new user. Requires a recently verified OTP."""
    phone = request.phone

    # Check OTP was verified recently (used OTP within OTP_EXPIRE_MINUTES)
    window = datetime.now(UTC) - timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
    result = await db.execute(
        select(OtpCode)
        .where(
            OtpCode.phone == phone,
            OtpCode.is_used == True,  # noqa: E712
            OtpCode.created_at >= window,
        )
        .order_by(OtpCode.created_at.desc())
    )
    verified_otp = result.scalars().first()

    # In dev mode, also accept if code is 000000 (even without a stored used OTP)
    if verified_otp is None and not (settings.ENV == "dev" and request.code == _DEV_OTP):
        raise ApplicationError("OTP not verified. Complete phone verification first.")

    # Validate referral code
    result = await db.execute(
        select(User).where(func.lower(User.ref_code) == request.ref_code.lower())
    )
    referrer = result.scalar_one_or_none()
    if referrer is None:
        raise ApplicationError("Invalid referral code.")

    # Phone uniqueness
    existing = await get_user_by_phone(phone, db)
    if existing:
        raise ApplicationError("Phone number already registered.")

    # Email uniqueness
    if await get_user_by_email(request.email, db):
        raise ApplicationError("Email already registered.")

    # Age check
    today = datetime.now(UTC).date()
    age = today.year - request.dob.year - (
        (today.month, today.day) < (request.dob.month, request.dob.day)
    )
    if age < 18:
        raise ApplicationError("You must be at least 18 years old to register.")

    # Generate unique ref_code
    for _ in range(10):
        candidate = _gen_ref_code()
        check = await db.execute(select(User).where(User.ref_code == candidate))
        if check.scalar_one_or_none() is None:
            new_ref_code = candidate
            break
    else:
        raise ApplicationError("Could not generate a unique referral code. Please try again.")

    user = User(
        phone=phone,
        password_hash=hash_password(request.password),
        first_name=request.first_name,
        last_name=request.last_name,
        dob=request.dob,
        email=str(request.email),
        city=request.city,
        ref_code=new_ref_code,
        parent_id=referrer.id,
        status_tier="partner",
    )
    db.add(user)
    await db.flush()

    access_token = _make_access_token(user)
    refresh_token = _make_refresh_token()
    await _create_session(user, refresh_token, http_request, db)
    await db.commit()
    await db.refresh(user)

    return _build_token_response(access_token, refresh_token)


@AuthRouter.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate with phone + password."""
    user = await get_user_by_phone(request.phone, db)
    if not user or not verify_password(request.password, user.password_hash):
        raise ApplicationError("Incorrect phone or password.")

    if not user.is_active:
        raise ApplicationError("Account is inactive.")
    if user.is_frozen:
        raise ApplicationError("Account is frozen. Contact support.")

    access_token = _make_access_token(user)
    refresh_token = _make_refresh_token()
    await _create_session(user, refresh_token, http_request, db)
    await db.commit()

    return _build_token_response(access_token, refresh_token)


@AuthRouter.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: RefreshRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Rotate refresh token and return new token pair."""
    token_hash = _hash_token(request.refresh_token)
    result = await db.execute(
        select(Session).where(Session.refresh_token_hash == token_hash)
    )
    session = result.scalar_one_or_none()

    if session is None:
        raise ApplicationError("Invalid refresh token.")
    if session.expires_at <= datetime.now(UTC):
        await db.delete(session)
        await db.commit()
        raise ApplicationError("Refresh token expired. Please log in again.")

    result = await db.execute(select(User).where(User.id == session.user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active or user.is_frozen:
        raise ApplicationError("User not found or account unavailable.")

    new_refresh_token = _make_refresh_token()
    session.refresh_token_hash = _hash_token(new_refresh_token)
    session.last_used_at = datetime.now(UTC)
    session.expires_at = datetime.now(UTC) + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    await db.commit()

    access_token = _make_access_token(user)
    return _build_token_response(access_token, new_refresh_token)


@AuthRouter.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete the most recently used session for the current user."""
    result = await db.execute(
        select(Session)
        .where(Session.user_id == current_user.id)
        .order_by(Session.last_used_at.desc())
    )
    session = result.scalars().first()
    if session:
        await db.delete(session)
        await db.commit()

    return {"message": "Logged out"}
