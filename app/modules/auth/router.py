"""Authentication routes."""

import hashlib
import logging
import random
import secrets
import string
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_session_id
from app.core.config import settings
from app.core.exceptions import ApplicationError
from app.db.session import get_db
from app.modules.auth.model import EmailConfirmation, OtpCode, Session
from app.modules.auth.schema import (
    AccountDeletionRequest,
    CancelDeletionRequest,
    ChangeEmailRequest,
    ChangeRefCodeRequest,
    CheckPhoneResponse,
    CheckRefCodeResponse,
    ConfirmEmailRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SendOtpRequest,
    SessionInfoResponse,
    SessionListResponse,
    TokenResponse,
    VerifyOtpRequest,
)
from app.modules.user.model import User
from app.utils.hashing import hash_password, verify_password
from app.utils.helpers import get_user_by_email, get_user_by_phone

AuthRouter = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)

_DEV_OTP = "000000"
_EMAIL_CONF_EXPIRE_DAYS = 7


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _make_access_token(user: User, session_id: int) -> str:
    from app.core.security import create_access_token
    return create_access_token(
        data={
            "sub": str(user.id),
            "phone": user.phone,
            "role": user.status_tier,
            "sid": session_id,
        }
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


def _gen_email_code() -> str:
    return "".join(random.choices(string.digits, k=6))


async def _create_email_confirmation(user: User, db: AsyncSession) -> str:
    """Create an EmailConfirmation record and return the plaintext code."""
    # Invalidate any previous active confirmations for this user
    result = await db.execute(
        select(EmailConfirmation).where(
            EmailConfirmation.user_id == user.id,
            EmailConfirmation.is_used == False,  # noqa: E712
        )
    )
    for old in result.scalars().all():
        old.is_used = True

    code = _gen_email_code()
    confirmation = EmailConfirmation(
        user_id=user.id,
        code_hash=_hash_token(code),
        expires_at=datetime.now(UTC) + timedelta(days=_EMAIL_CONF_EXPIRE_DAYS),
    )
    db.add(confirmation)
    await db.flush()
    return code


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


@AuthRouter.post("/otp/send", status_code=status.HTTP_200_OK)
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
        # TODO: deliver via WhatsApp (Twilio), SMS fallback
        raise NotImplementedError("OTP delivery not configured — set TWILIO credentials")

    expires_at = datetime.now(UTC) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
    otp = OtpCode(
        phone=phone,
        code_hash=_hash_token(code),
        channel=channel,
        purpose=request.purpose,
        expires_at=expires_at,
    )
    db.add(otp)
    await db.commit()

    return {"message": "Code sent", "channel": channel}


def _map_account_state(user: User) -> str:
    """Map current boolean flags to a logical account state string."""
    if not user.is_active:
        return "blocked"
    if not user.email_confirmed:
        return "email_unconfirmed"
    return "active"


@AuthRouter.post("/otp/verify", status_code=status.HTTP_200_OK)
async def verify_otp(
    request: VerifyOtpRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Verify OTP code. Returns {verified, is_registered, account_state}.

    Does NOT issue tokens — token issuance happens at /login or /register.
    Frontend uses account_state to route: email_unconfirmed → email confirm screen,
    active/blocked → login screen, not registered → registration form.
    """
    phone = request.phone
    code = request.code

    if settings.ENV == "dev" and code == _DEV_OTP:
        user = await get_user_by_phone(phone, db)
        if user is not None:
            return {"verified": True, "is_registered": True, "account_state": _map_account_state(user)}
        return {"verified": True, "is_registered": False, "account_state": None}

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
    if user is not None:
        return {"verified": True, "is_registered": True, "account_state": _map_account_state(user)}
    return {"verified": True, "is_registered": False, "account_state": None}


@AuthRouter.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Register a new user. Requires a recently verified OTP."""
    phone = request.phone

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

    # Pass if: a recently-verified OTP exists OR we're in dev mode (code bypass or code omitted)
    dev_bypass = settings.ENV == "dev" and (request.code == _DEV_OTP or request.code is None)
    if verified_otp is None and not dev_bypass:
        raise ApplicationError("OTP not verified. Complete phone verification first.")

    result = await db.execute(
        select(User).where(func.lower(User.ref_code) == request.ref_code.lower())
    )
    referrer = result.scalar_one_or_none()
    if referrer is None:
        raise ApplicationError("Invalid referral code.")

    existing = await get_user_by_phone(phone, db)
    if existing:
        raise ApplicationError("Phone number already registered.")

    if await get_user_by_email(request.email, db):
        raise ApplicationError("Email already registered.")

    today = datetime.now(UTC).date()
    age = today.year - request.dob.year - (
        (today.month, today.day) < (request.dob.month, request.dob.day)
    )
    if age < 18:
        raise ApplicationError("You must be at least 18 years old to register.")

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

    # Create email confirmation record
    email_code = await _create_email_confirmation(user, db)
    from app.utils.email import send_transactional
    await send_transactional(str(user.email), "email_confirmation", {"code": email_code})

    refresh_token = _make_refresh_token()
    session = await _create_session(user, refresh_token, http_request, db)
    access_token = _make_access_token(user, session.id)
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

    refresh_token = _make_refresh_token()
    session = await _create_session(user, refresh_token, http_request, db)
    access_token = _make_access_token(user, session.id)
    await db.commit()

    return _build_token_response(access_token, refresh_token)


@AuthRouter.post("/token/refresh", response_model=TokenResponse)
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
    await db.flush()

    access_token = _make_access_token(user, session.id)
    await db.commit()

    return _build_token_response(access_token, new_refresh_token)


@AuthRouter.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    current_user: User = Depends(get_current_user),
    session_id: int | None = Depends(get_session_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Revoke the current session identified by the JWT sid claim."""
    if session_id is not None:
        result = await db.execute(
            select(Session).where(
                Session.id == session_id,
                Session.user_id == current_user.id,
            )
        )
        session = result.scalars().first()
        if session:
            await db.delete(session)
            await db.commit()
    return {"message": "Logged out"}


# ── Phone / ref-code lookup (public) ──────────────────────────────────────────

@AuthRouter.get("/check-phone", response_model=CheckPhoneResponse)
async def check_phone(
    phone: str = Query(..., description="Phone in E.164 format"),
    db: AsyncSession = Depends(get_db),
) -> CheckPhoneResponse:
    """Return whether a phone is registered and its account state.

    Used by the frontend after OTP verify to decide routing:
    not registered → registration form, registered → login screen.
    """
    from app.utils.phone import normalize_phone, validate_e164
    try:
        normalized = normalize_phone(phone)
        if not validate_e164(normalized):
            raise ValueError
    except (ValueError, Exception):
        raise ApplicationError("Invalid phone format.", status_code=422)

    user = await get_user_by_phone(normalized, db)
    if user is None:
        return CheckPhoneResponse(registered=False)
    return CheckPhoneResponse(registered=True, account_state=_map_account_state(user))


@AuthRouter.get("/check-refcode", response_model=CheckRefCodeResponse)
async def check_refcode(
    ref_code: str = Query(..., description="Upline's referral code"),
    db: AsyncSession = Depends(get_db),
) -> CheckRefCodeResponse:
    """Validate an upline ref code and return the owner's name.

    Called on blur from Registration Step 3 ref-code field.
    """
    result = await db.execute(
        select(User).where(func.upper(User.ref_code) == ref_code.strip().upper())
    )
    user = result.scalar_one_or_none()
    if user is None:
        return CheckRefCodeResponse(valid=False)
    owner_name = f"{user.first_name} {user.last_name or ''}".strip()
    return CheckRefCodeResponse(valid=True, owner_name=owner_name)


# ── Email confirmation ─────────────────────────────────────────────────────────

@AuthRouter.post("/email/confirm", response_model=MessageResponse)
async def confirm_email(
    request: ConfirmEmailRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Confirm email with 6-digit code sent during registration."""
    if current_user.email_confirmed:
        return MessageResponse(message="Email already confirmed.")

    result = await db.execute(
        select(EmailConfirmation).where(
            EmailConfirmation.user_id == current_user.id,
            EmailConfirmation.is_used == False,  # noqa: E712
            EmailConfirmation.expires_at > datetime.now(UTC),
        ).order_by(EmailConfirmation.created_at.desc())
    )
    conf = result.scalars().first()
    if conf is None:
        raise ApplicationError("No active confirmation code. Request a new one.")

    conf.attempts += 1

    # Spec: attempts 1–4 inline error, attempt 5 → 15-min lockout
    if conf.attempts > 5:
        await db.commit()
        raise ApplicationError("Too many attempts. Request a new code.", status_code=429)

    if conf.code_hash != _hash_token(request.code):
        await db.commit()
        raise ApplicationError("Invalid confirmation code.")

    conf.is_used = True
    current_user.email_confirmed = True
    await db.commit()
    return MessageResponse(message="Email confirmed.")


@AuthRouter.post("/email/resend", response_model=MessageResponse)
async def resend_email_confirmation(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Resend email confirmation code. 60-second cooldown between sends."""
    if current_user.email_confirmed:
        return MessageResponse(message="Email already confirmed.")

    # Enforce 60-second cooldown
    cooldown_cutoff = datetime.now(UTC) - timedelta(seconds=60)
    result = await db.execute(
        select(EmailConfirmation).where(
            EmailConfirmation.user_id == current_user.id,
            EmailConfirmation.created_at > cooldown_cutoff,
        ).order_by(EmailConfirmation.created_at.desc())
    )
    if result.scalars().first() is not None:
        raise ApplicationError("Please wait before requesting another code.", status_code=429)

    email_code = await _create_email_confirmation(current_user, db)
    from app.utils.email import send_transactional
    await send_transactional(str(current_user.email), "email_confirmation", {"code": email_code})
    await db.commit()
    return MessageResponse(message="Confirmation code sent.")


@AuthRouter.post("/email/change", response_model=MessageResponse)
async def change_email(
    request: ChangeEmailRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Change email before it has been confirmed. Max 3 changes per registration.

    Requires migration 0005 for email_change_count enforcement.
    """
    if current_user.email_confirmed:
        raise ApplicationError("Email is already confirmed and cannot be changed here.")

    new_email = str(request.new_email)

    existing = await get_user_by_email(new_email, db)
    if existing and existing.id != current_user.id:
        raise ApplicationError("Email already in use.")

    current_user.email = new_email
    email_code = await _create_email_confirmation(current_user, db)
    from app.utils.email import send_transactional
    await send_transactional(new_email, "email_confirmation", {"code": email_code})
    await db.commit()
    return MessageResponse(message="Email updated. Confirmation code sent to new address.")


# ── Password reset ─────────────────────────────────────────────────────────────

@AuthRouter.post("/password/forgot", response_model=MessageResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Send OTP to phone for password reset.

    Always returns 200 to prevent phone number enumeration.
    Blocked accounts cannot reset their password (spec requirement).
    """
    user = await get_user_by_phone(request.phone, db)

    if user is None or not user.is_active:
        # Don't reveal whether phone exists or account is blocked
        return MessageResponse(message="If this number is registered, a code will be sent.")

    send_count = await _count_recent_otp_sends(request.phone, db)
    if send_count >= settings.OTP_RESEND_LIMIT:
        raise ApplicationError(
            f"Too many OTP requests. Try again in {settings.OTP_RESEND_WINDOW_MINUTES} minutes.",
            status_code=429,
        )

    if settings.ENV == "dev":
        code = _DEV_OTP
        channel = "mock"
    else:
        raise NotImplementedError("OTP delivery not configured — set provider credentials")

    expires_at = datetime.now(UTC) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
    otp = OtpCode(
        phone=request.phone,
        code_hash=_hash_token(code),
        channel=channel,
        expires_at=expires_at,
    )
    db.add(otp)
    await db.commit()
    return MessageResponse(message="If this number is registered, a code will be sent.")


@AuthRouter.post("/password/reset", response_model=MessageResponse)
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Set a new password after OTP verification.

    Verifies a recently-used OTP (marked used by /otp/verify), updates the password,
    and invalidates ALL active sessions. The user must log in again.
    Per spec: blocked users cannot reset password.
    """
    user = await get_user_by_phone(request.phone, db)
    if user is None:
        raise ApplicationError("Phone not registered.", status_code=404)
    if not user.is_active:
        raise ApplicationError("Account is blocked. Password reset is not available.", status_code=403)

    # Dev bypass
    if not (settings.ENV == "dev" and request.code == _DEV_OTP):
        window = datetime.now(UTC) - timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
        result = await db.execute(
            select(OtpCode).where(
                OtpCode.phone == request.phone,
                OtpCode.is_used == True,  # noqa: E712
                OtpCode.created_at >= window,
            ).order_by(OtpCode.created_at.desc())
        )
        if result.scalars().first() is None:
            raise ApplicationError("OTP not verified. Complete phone verification first.")

    user.password_hash = hash_password(request.new_password)
    await db.execute(delete(Session).where(Session.user_id == user.id))
    await db.commit()

    # TODO: send security notification email (password_changed template)
    return MessageResponse(message="Password updated. All sessions have been terminated.")


# ── Account deletion ───────────────────────────────────────────────────────────

@AuthRouter.delete("/account", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def delete_account(
    request: AccountDeletionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Initiate account deletion (soft-delete with 7-day grace period).

    Requires OTP to confirm identity. Moves account to soft_deleting state,
    revokes all sessions, sends deletion-scheduled email.
    Full soft_deleting state requires migration 0005 (deletion_scheduled_at column).
    """
    # TODO: check for pending orders — cannot delete with active orders

    # Verify OTP
    if not (settings.ENV == "dev" and request.code == _DEV_OTP):
        otp = await _get_active_otp(current_user.phone, db)
        if otp is None:
            raise ApplicationError("No active OTP found. Request a new code.")

        otp.attempts += 1
        if otp.attempts > settings.OTP_MAX_ATTEMPTS:
            await db.commit()
            raise ApplicationError("Too many failed attempts.", status_code=429)

        if otp.code_hash != _hash_token(request.code):
            await db.commit()
            raise ApplicationError("Invalid OTP code.")

        otp.is_used = True

    # Mark for deletion — deletion_scheduled_at populated by migration 0005
    # For now deactivate; full soft_deleting logic enabled after 0005 is applied
    current_user.is_active = False
    await db.execute(delete(Session).where(Session.user_id == current_user.id))
    await db.commit()

    # TODO: send account_deletion_scheduled email with cancel token
    return MessageResponse(message="Account deletion initiated. You have been logged out.")


@AuthRouter.post("/account/cancel-deletion", response_model=MessageResponse)
async def cancel_deletion(
    request: CancelDeletionRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Cancel a pending account deletion using the token from the deletion email.

    Requires migration 0005 (deletion_cancel_token column on users).
    """
    # TODO: implement once migration 0005 is applied
    # Logic: find user where deletion_cancel_token == request.token AND deletion_scheduled_at > now()
    # → set is_active=True, clear deletion_scheduled_at and deletion_cancel_token
    raise ApplicationError("Not yet implemented. Requires migration 0005.", status_code=501)


# ── Sessions ───────────────────────────────────────────────────────────────────

@AuthRouter.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    current_user: User = Depends(get_current_user),
    current_session_id: int | None = Depends(get_session_id),
    db: AsyncSession = Depends(get_db),
) -> SessionListResponse:
    """List all active sessions for the current user.

    Per spec: shows device type + city-level location (NOT raw IP) + last active.
    City is stored at login time (requires migration 0005 to populate).
    """
    result = await db.execute(
        select(Session)
        .where(Session.user_id == current_user.id)
        .order_by(Session.last_used_at.desc())
    )
    sessions = result.scalars().all()
    return SessionListResponse(
        sessions=[
            SessionInfoResponse(
                id=s.id,
                device_info=s.device_info,
                city=None,  # TODO: populate from session.city after migration 0005
                last_active=s.last_used_at.isoformat(),
                is_current=(s.id == current_session_id),
            )
            for s in sessions
        ]
    )


@AuthRouter.delete("/sessions/{session_id}", response_model=MessageResponse)
async def revoke_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Revoke a specific session (remote logout from another device)."""
    result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == current_user.id,
        )
    )
    session = result.scalars().first()
    if session is None:
        raise ApplicationError("Session not found.", status_code=404)
    await db.delete(session)
    await db.commit()
    return MessageResponse(message="Session revoked.")


# ── Ref code ───────────────────────────────────────────────────────────────────

@AuthRouter.post("/ref-code/change", response_model=dict)
async def change_ref_code(
    request: ChangeRefCodeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Change own ref code. Allowed ONCE. Code must be 4–10 chars, Latin A-Z + digits.

    Old code is logged to ref_code_history (requires migration 0005 for the table).
    """
    if current_user.ref_code_changed:
        raise ApplicationError("Ref code can only be changed once.")

    new_code = request.new_ref_code  # already uppercased by schema validator

    result = await db.execute(select(User).where(User.ref_code == new_code))
    if result.scalar_one_or_none() is not None:
        raise ApplicationError("This ref code is already taken.")

    current_user.ref_code = new_code
    current_user.ref_code_changed = True
    await db.commit()

    # TODO: log to ref_code_history table after migration 0005
    # TODO: send ref_code_changed email notification

    return {"message": "Ref code updated.", "ref_code": new_code}
