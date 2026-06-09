"""Admin: partner management routes."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_admin
from app.core.exceptions import ApplicationError
from app.db.session import get_db
from app.modules.admin.model import AdminAction, AdminUser
from app.modules.auth.model import Session
from app.modules.user.model import User
from app.utils.hashing import hash_password
from app.utils.pagination import create_pagination_response

AdminPartnerRouter = APIRouter(tags=["admin"])

_ALLOWED_PATCH_FIELDS = {"is_active", "is_frozen", "status_tier", "city", "email", "first_name", "last_name"}


def _user_snapshot(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "phone": user.phone,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "email_confirmed": user.email_confirmed,
        "city": user.city,
        "status_tier": user.status_tier,
        "is_active": user.is_active,
        "is_frozen": user.is_frozen,
    }


async def _log_action(
    admin: AdminUser,
    action_type: str,
    target_type: str,
    target_id: int | None,
    before: dict | None,
    after: dict | None,
    request: Request,
    db: AsyncSession,
) -> None:
    action = AdminAction(
        admin_id=admin.id,
        action_type=action_type,
        target_type=target_type,
        target_id=target_id,
        before_data=before,
        after_data=after,
        ip=request.client.host if request.client else None,
    )
    db.add(action)
    await db.flush()


@AdminPartnerRouter.get("/partners")
async def list_partners(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    search: str | None = Query(None),
    city: str | None = Query(None),
    status_tier: str | None = Query(None),
    is_active: bool | None = Query(None),
    is_frozen: bool | None = Query(None),
    date_from: str | None = Query(None, description="ISO date: 2026-01-01"),
    date_to: str | None = Query(None, description="ISO date: 2026-12-31"),
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List partners with search and filters."""
    base = select(User)

    if search:
        like = f"%{search}%"
        base = base.where(
            or_(
                User.phone.ilike(like),
                User.first_name.ilike(like),
                User.last_name.ilike(like),
                User.email.ilike(like),
                User.ref_code.ilike(like),
            )
        )
    if city:
        base = base.where(User.city.ilike(f"%{city}%"))
    if status_tier:
        base = base.where(User.status_tier == status_tier)
    if is_active is not None:
        base = base.where(User.is_active == is_active)
    if is_frozen is not None:
        base = base.where(User.is_frozen == is_frozen)
    if date_from:
        try:
            base = base.where(User.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            base = base.where(User.created_at <= datetime.fromisoformat(date_to + "T23:59:59"))
        except ValueError:
            pass

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()

    rows = (
        await db.execute(
            base.order_by(User.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    ).scalars().all()

    # Fetch parent ref_codes in bulk
    parent_ids = [u.parent_id for u in rows if u.parent_id is not None]
    parent_map: dict[int, str] = {}
    if parent_ids:
        parents = (
            await db.execute(select(User.id, User.ref_code).where(User.id.in_(parent_ids)))
        ).all()
        parent_map = {pid: ref for pid, ref in parents}

    items = [
        {
            "id": u.id,
            "phone": u.phone,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "email": u.email,
            "email_confirmed": u.email_confirmed,
            "ref_code": u.ref_code,
            "city": u.city,
            "status_tier": u.status_tier,
            "is_active": u.is_active,
            "is_frozen": u.is_frozen,
            "created_at": u.created_at.isoformat(),
            "parent_ref_code": parent_map.get(u.parent_id) if u.parent_id else None,
        }
        for u in rows
    ]

    return create_pagination_response(items, page, limit, total).model_dump()


@AdminPartnerRouter.get("/partners/{user_id}")
async def get_partner(
    user_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get full partner detail."""
    user = await db.get(User, user_id)
    if user is None:
        raise ApplicationError("Partner not found.", status_code=404)

    # Parent info
    parent_info = None
    if user.parent_id:
        parent = await db.get(User, user.parent_id)
        if parent:
            parent_info = {"id": parent.id, "phone": parent.phone, "first_name": parent.first_name, "ref_code": parent.ref_code}

    # Direct downline count
    downline_count = (
        await db.execute(select(func.count()).where(User.parent_id == user_id))
    ).scalar_one()

    # Last 10 sessions
    sessions = (
        await db.execute(
            select(Session)
            .where(Session.user_id == user_id)
            .order_by(Session.last_used_at.desc())
            .limit(10)
        )
    ).scalars().all()
    session_list = [
        {
            "id": s.id,
            "device_info": s.device_info,
            "ip": s.ip,
            "created_at": s.created_at.isoformat(),
            "last_used_at": s.last_used_at.isoformat(),
        }
        for s in sessions
    ]

    data = _user_snapshot(user)
    data.update({
        "patronymic": user.patronymic,
        "dob": user.dob.isoformat() if user.dob else None,
        "ref_code": user.ref_code,
        "ref_code_changed": user.ref_code_changed,
        "avatar_url": user.avatar_url,
        "team_volume": float(user.team_volume),
        "parent_id": user.parent_id,
        "is_root": user.is_root,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
        "parent": parent_info,
        "direct_downline_count": downline_count,
        "last_10_sessions": session_list,
    })
    return data


@AdminPartnerRouter.patch("/partners/{user_id}")
async def update_partner(
    user_id: int,
    body: dict,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update partner fields. Creates an audit record for every change."""
    user = await db.get(User, user_id)
    if user is None:
        raise ApplicationError("Partner not found.", status_code=404)

    patch = {k: v for k, v in body.items() if k in _ALLOWED_PATCH_FIELDS}
    if not patch:
        raise ApplicationError("No allowed fields provided.")

    before = _user_snapshot(user)

    for field, value in patch.items():
        setattr(user, field, value)

    # Terminate sessions if deactivating
    if patch.get("is_active") is False:
        await db.execute(delete(Session).where(Session.user_id == user_id))

    await db.flush()
    after = _user_snapshot(user)

    await _log_action(admin, "update_partner", "user", user_id, before, after, request, db)
    await db.commit()
    await db.refresh(user)

    return _user_snapshot(user)


@AdminPartnerRouter.post("/partners/{user_id}/force-verify-email")
async def force_verify_email(
    user_id: int,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Force-verify partner email regardless of OTP."""
    user = await db.get(User, user_id)
    if user is None:
        raise ApplicationError("Partner not found.", status_code=404)

    before = {"email_confirmed": user.email_confirmed}
    user.email_confirmed = True
    after = {"email_confirmed": True}

    await _log_action(admin, "force_verify_email", "user", user_id, before, after, request, db)
    await db.commit()

    return {"message": "Email verified"}


@AdminPartnerRouter.post("/partners/{user_id}/reset-password")
async def reset_partner_password(
    user_id: int,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate and set a temporary password for the partner."""
    import secrets
    user = await db.get(User, user_id)
    if user is None:
        raise ApplicationError("Partner not found.", status_code=404)

    # 12-char temp password: letters + digits + special
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$"
    temp_password = "".join(secrets.choice(alphabet) for _ in range(12))
    user.password_hash = hash_password(temp_password)

    await _log_action(admin, "reset_password", "user", user_id, None, None, request, db)
    await db.commit()

    if settings.ENV == "dev":
        return {"message": "Password reset", "temp_password": temp_password}
    else:
        # TODO: send temp_password via SMS/email (SendGrid/Mailgun)
        return {"message": "Password reset"}


# ── Block / unblock ───────────────────────────────────────────────────────────

@AdminPartnerRouter.post("/partners/{user_id}/block")
async def block_partner(
    user_id: int,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Block a partner account. Terminates all active sessions immediately."""
    user = await db.get(User, user_id)
    if user is None:
        raise ApplicationError("Partner not found.", status_code=404)
    if not user.is_active:
        raise ApplicationError("Partner is already blocked.")

    before = _user_snapshot(user)
    user.is_active = False
    await db.execute(delete(Session).where(Session.user_id == user_id))
    after = _user_snapshot(user)

    await _log_action(admin, "block_partner", "user", user_id, before, after, request, db)
    await db.commit()

    # TODO: send push notification to partner informing of block
    return {"message": "Partner blocked."}


@AdminPartnerRouter.post("/partners/{user_id}/unblock")
async def unblock_partner(
    user_id: int,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Unblock a partner account. Per spec: triggers push notification to partner."""
    user = await db.get(User, user_id)
    if user is None:
        raise ApplicationError("Partner not found.", status_code=404)
    if user.is_active:
        raise ApplicationError("Partner is not blocked.")

    before = _user_snapshot(user)
    user.is_active = True
    after = _user_snapshot(user)

    await _log_action(admin, "unblock_partner", "user", user_id, before, after, request, db)
    await db.commit()

    # TODO: send push notification to partner informing of unblock
    return {"message": "Partner unblocked."}


# ── IP/TOO verification queue ─────────────────────────────────────────────────

@AdminPartnerRouter.get("/ip-too/pending")
async def list_pending_ip_too(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List all IP/TOO records awaiting manual verification."""
    from app.modules.ip_too.model import IpToo

    rows = (
        await db.execute(
            select(IpToo, User)
            .join(User, IpToo.user_id == User.id)
            .where(IpToo.status == "pending")
            .order_by(IpToo.created_at.asc())
        )
    ).all()

    return [
        {
            "id": ip.id,
            "user_id": ip.user_id,
            "user_phone": u.phone,
            "user_name": f"{u.first_name} {u.last_name or ''}".strip(),
            "user_ref_code": u.ref_code,
            "type": ip.type,
            "iin_bin": ip.iin_bin,
            "name": ip.name,
            "status": ip.status,
            "created_at": ip.created_at.isoformat(),
        }
        for ip, u in rows
    ]


@AdminPartnerRouter.patch("/ip-too/{record_id}/verify")
async def verify_ip_too(
    record_id: int,
    body: dict,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Approve or reject a pending IP/TOO record."""
    from datetime import UTC, datetime

    from app.modules.ip_too.model import IpToo

    action_str = body.get("action", "").strip().lower()
    if action_str not in ("approve", "reject"):
        raise ApplicationError("'action' must be 'approve' or 'reject'.")
    if action_str == "reject" and not body.get("rejection_reason"):
        raise ApplicationError("'rejection_reason' is required when rejecting.")

    record = await db.get(IpToo, record_id)
    if record is None:
        raise ApplicationError("IP/TOO record not found.", status_code=404)

    before = {"status": record.status}

    if action_str == "approve":
        record.status = "verified"
        record.verified_at = datetime.now(UTC)
    else:
        record.status = "rejected"
        record.rejection_reason = body["rejection_reason"]
        record.is_active = False

    after = {"status": record.status}

    await _log_action(admin, f"ip_too_{action_str}", "ip_too", record_id, before, after, request, db)
    await db.commit()
    await db.refresh(record)

    return {
        "id": record.id,
        "user_id": record.user_id,
        "iin_bin": record.iin_bin,
        "status": record.status,
        "rejection_reason": record.rejection_reason,
        "verified_at": record.verified_at.isoformat() if record.verified_at else None,
    }


# avoid circular import
from app.core.config import settings  # noqa: E402
