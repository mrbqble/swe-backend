"""User routes."""

import hashlib
import logging
import random
import re
import string
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_session_id
from app.core.config import settings
from app.core.exceptions import ApplicationError
from app.db.session import get_db
from app.modules.auth.model import EmailConfirmation, OtpCode, Session
from app.modules.user.model import User
from app.modules.user.schema import (
    ChangePasswordRequest,
    ChangeRefCodeRequest,
    DeleteConfirmRequest,
    EmailConfirmRequest,
    PushTokenRequest,
    SessionInfo,
    UpdateProfileRequest,
    UserProfile,
)
from app.utils.hashing import hash_password, verify_password
from app.utils.helpers import get_user_by_email

UserRouter = APIRouter(prefix="/users", tags=["users"])
logger = logging.getLogger(__name__)

_DEV_OTP = "000000"
_RESERVED_CODES = {"ADMIN", "ROOT", "ICARE"}
_EMAIL_CONF_EXPIRE_DAYS = 7
_EMAIL_CONF_RESEND_LIMIT = 3
_EMAIL_CONF_RESEND_WINDOW_MINUTES = 60
_EMAIL_CONF_MAX_ATTEMPTS = 5
_EMAIL_CONF_BLOCK_MINUTES = 15


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _validate_password_policy(password: str) -> None:
    if len(password) < 8:
        raise ApplicationError("Password must be at least 8 characters.")
    if not re.search(r"[A-Za-z]", password):
        raise ApplicationError("Password must contain at least one letter.")
    if not re.search(r"\d", password):
        raise ApplicationError("Password must contain at least one digit.")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?`~]", password):
        raise ApplicationError("Password must contain at least one special character.")


@UserRouter.get("/me", response_model=UserProfile)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Get current authenticated user's profile."""
    return current_user


@UserRouter.patch("/me", response_model=UserProfile)
async def update_me(
    data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Update current user's profile."""
    update_dict = data.model_dump(exclude_unset=True)

    if "email" in update_dict and update_dict["email"] is not None:
        new_email = str(update_dict["email"])
        if new_email != current_user.email:
            existing = await get_user_by_email(new_email, db)
            if existing and existing.id != current_user.id:
                raise ApplicationError("Email already registered.")
            # Email changed — reset confirmation
            current_user.email_confirmed = False
        update_dict["email"] = new_email

    for field, value in update_dict.items():
        setattr(current_user, field, value)

    await db.commit()
    await db.refresh(current_user)
    return current_user


# ── Step 1: change password ───────────────────────────────────────────────────

@UserRouter.post("/me/change-password")
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    current_session_id: int | None = Depends(get_session_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Change password. Terminates all other sessions."""
    if not verify_password(data.current_password, current_user.password_hash):
        raise ApplicationError("Current password is incorrect.")

    _validate_password_policy(data.new_password)

    current_user.password_hash = hash_password(data.new_password)

    # Terminate all sessions except the current one
    stmt = delete(Session).where(Session.user_id == current_user.id)
    if current_session_id is not None:
        stmt = stmt.where(Session.id != current_session_id)
    await db.execute(stmt)

    await db.commit()
    return {"message": "Password updated"}


# ── Step 2: list sessions ─────────────────────────────────────────────────────

@UserRouter.get("/me/sessions", response_model=list[SessionInfo])
async def list_sessions(
    current_user: User = Depends(get_current_user),
    current_session_id: int | None = Depends(get_session_id),
    db: AsyncSession = Depends(get_db),
) -> list[SessionInfo]:
    """List all active sessions for the current user."""
    now = datetime.now(UTC)
    result = await db.execute(
        select(Session)
        .where(Session.user_id == current_user.id, Session.expires_at > now)
        .order_by(Session.last_used_at.desc())
    )
    sessions = result.scalars().all()

    return [
        SessionInfo(
            id=s.id,
            device_info=s.device_info,
            ip=s.ip,
            created_at=s.created_at,
            last_used_at=s.last_used_at,
            is_current=(s.id == current_session_id),
        )
        for s in sessions
    ]


# ── Step 3: terminate a specific session ─────────────────────────────────────

@UserRouter.delete("/me/sessions/{session_id}")
async def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    current_session_id: int | None = Depends(get_session_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Terminate a specific session. Cannot delete the current session (use /auth/logout)."""
    if session_id == current_session_id:
        raise ApplicationError(
            "Cannot delete the current session. Use POST /auth/logout instead."
        )

    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()

    if session is None or session.user_id != current_user.id:
        raise ApplicationError("Session not found.", status_code=404)

    await db.delete(session)
    await db.commit()
    return {"message": "Session terminated"}


# ── Step 4: change ref-code ───────────────────────────────────────────────────

@UserRouter.post("/me/ref-code")
async def change_ref_code(
    data: ChangeRefCodeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Change own referral code. Allowed once per partner lifetime."""
    if current_user.ref_code_changed:
        raise ApplicationError("Referral code has already been changed. Only one change is allowed.")

    new_code = data.new_code.upper()

    if not re.match(r"^[A-Z0-9]{4,10}$", new_code):
        raise ApplicationError("Code must be 4–10 characters, letters A–Z and digits 0–9 only.")

    if new_code in _RESERVED_CODES:
        raise ApplicationError("That code is reserved and cannot be used.")

    # TODO: add profanity check before allowing custom codes

    existing = await db.execute(
        select(User).where(func.upper(User.ref_code) == new_code)
    )
    if existing.scalar_one_or_none() is not None:
        raise ApplicationError("That referral code is already taken.")

    current_user.ref_code = new_code
    current_user.ref_code_changed = True
    await db.commit()

    return {"ref_code": new_code}


# ── Step 5: account deletion (two-step OTP flow) ─────────────────────────────

@UserRouter.post("/me/delete-request")
async def delete_request(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Step 1 of account deletion: send OTP confirmation code."""
    phone = current_user.phone

    if settings.ENV == "dev":
        code = _DEV_OTP
        channel = "mock"
        logger.info(f"DEV delete-OTP for {phone}: {code}")
    else:
        # TODO: deliver via WhatsApp/SMS
        raise NotImplementedError("OTP delivery not configured")

    expires_at = datetime.now(UTC) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
    otp = OtpCode(
        phone=phone,
        code_hash=_hash_token(code),
        channel=channel,
        expires_at=expires_at,
    )
    db.add(otp)
    await db.commit()

    return {"message": "Confirmation code sent"}


@UserRouter.post("/me/delete-confirm")
async def delete_confirm(
    data: DeleteConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Step 2 of account deletion: verify OTP and anonymize account."""
    phone = current_user.phone
    code = data.code

    if not (settings.ENV == "dev" and code == _DEV_OTP):
        result = await db.execute(
            select(OtpCode)
            .where(
                OtpCode.phone == phone,
                OtpCode.is_used == False,  # noqa: E712
                OtpCode.expires_at > datetime.now(UTC),
            )
            .order_by(OtpCode.created_at.desc())
        )
        otp = result.scalars().first()

        if otp is None:
            raise ApplicationError("No active OTP found. Request a new code.")

        otp.attempts += 1
        if otp.attempts > settings.OTP_MAX_ATTEMPTS:
            await db.commit()
            raise ApplicationError("Too many failed attempts.", status_code=429)

        if otp.code_hash != _hash_token(code):
            await db.commit()
            raise ApplicationError("Invalid code.")

        otp.is_used = True

    # Anonymize PII
    current_user.is_active = False
    current_user.phone = f"deleted_{current_user.id}"
    current_user.email = None
    current_user.email_confirmed = False
    current_user.first_name = "Deleted"
    current_user.last_name = None
    current_user.patronymic = None
    current_user.avatar_url = None
    # NOTE: ref_code stays reserved for 90 days — do not clear it
    # TODO: schedule ref_code cleanup after 90 days

    # Terminate all sessions
    await db.execute(delete(Session).where(Session.user_id == current_user.id))

    await db.commit()
    return {"message": "Account deleted"}


# ── Steps 6 & 7: email confirmation ──────────────────────────────────────────

@UserRouter.post("/me/email-confirm")
async def email_confirm(
    data: EmailConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Confirm email address with 6-digit code."""
    if current_user.email_confirmed:
        raise ApplicationError("Email is already confirmed.")

    result = await db.execute(
        select(EmailConfirmation)
        .where(
            EmailConfirmation.user_id == current_user.id,
            EmailConfirmation.is_used == False,  # noqa: E712
            EmailConfirmation.expires_at > datetime.now(UTC),
        )
        .order_by(EmailConfirmation.created_at.desc())
    )
    conf = result.scalars().first()

    if conf is None:
        raise ApplicationError("No active confirmation code. Request a new one.")

    conf.attempts += 1

    if conf.attempts > _EMAIL_CONF_MAX_ATTEMPTS:
        await db.commit()
        raise ApplicationError(
            f"Too many failed attempts. Request a new code after {_EMAIL_CONF_BLOCK_MINUTES} minutes.",
            status_code=429,
        )

    if conf.code_hash != _hash_token(data.code):
        await db.commit()
        raise ApplicationError("Invalid confirmation code.")

    conf.is_used = True
    current_user.email_confirmed = True
    await db.commit()

    return {"message": "Email confirmed"}


@UserRouter.post("/me/email-resend")
async def email_resend(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Resend email confirmation code. Rate-limited to 3 per hour."""
    if current_user.email_confirmed:
        raise ApplicationError("Email is already confirmed.")

    if current_user.email is None:
        raise ApplicationError("No email address set on this account.")

    window = datetime.now(UTC) - timedelta(minutes=_EMAIL_CONF_RESEND_WINDOW_MINUTES)
    result = await db.execute(
        select(func.count()).where(
            EmailConfirmation.user_id == current_user.id,
            EmailConfirmation.created_at >= window,
        )
    )
    send_count = result.scalar_one()

    if send_count >= _EMAIL_CONF_RESEND_LIMIT:
        raise ApplicationError(
            f"Too many resend requests. Try again in {_EMAIL_CONF_RESEND_WINDOW_MINUTES} minutes.",
            status_code=429,
        )

    # Invalidate previous active codes
    result = await db.execute(
        select(EmailConfirmation).where(
            EmailConfirmation.user_id == current_user.id,
            EmailConfirmation.is_used == False,  # noqa: E712
        )
    )
    for old in result.scalars().all():
        old.is_used = True

    code = "".join(random.choices(string.digits, k=6))
    conf = EmailConfirmation(
        user_id=current_user.id,
        code_hash=_hash_token(code),
        expires_at=datetime.now(UTC) + timedelta(days=_EMAIL_CONF_EXPIRE_DAYS),
    )
    db.add(conf)
    await db.commit()

    from app.utils.email import send_transactional
    await send_transactional(str(current_user.email), "email_confirmation", {"code": code})

    return {"message": "Confirmation code resent"}


# ── Step 14 (push token) ──────────────────────────────────────────────────────

@UserRouter.post("/me/push-token")
async def register_push_token(
    data: PushTokenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Register Expo push token for the current user."""
    current_user.push_token = data.token
    await db.commit()
    return {"message": "Token registered"}
