"""IP/TOO binding routes."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.exceptions import ApplicationError
from app.db.session import get_db
from app.modules.ip_too.model import IpToo
from app.modules.ip_too.schema import BindIpTooRequest, IpTooResponse
from app.modules.user.model import User
from app.utils.stat_gov import verify_iin_bin

IpTooRouter = APIRouter(prefix="/users/me/ip-too", tags=["users"])


@IpTooRouter.post("", response_model=IpTooResponse)
async def bind_ip_too(
    body: BindIpTooRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IpTooResponse:
    """Bind an IIN/BIN to the current partner account."""
    # Fraud prevention: no other user may already hold this IIN/BIN
    existing = (
        await db.execute(select(IpToo).where(IpToo.iin_bin == body.iin_bin))
    ).scalar_one_or_none()
    if existing and existing.user_id != current_user.id:
        raise ApplicationError("This IIN/BIN is already registered to another account.")

    result = await verify_iin_bin(body.iin_bin)
    if result is None:
        raise ApplicationError(
            "Business not found in state registry. Check your IIN/BIN."
        )

    # Deactivate any existing active record for this user
    prev_rows = (
        await db.execute(
            select(IpToo).where(
                IpToo.user_id == current_user.id, IpToo.is_active == True  # noqa: E712
            )
        )
    ).scalars().all()
    for prev in prev_rows:
        prev.is_active = False

    if result["status"] == "active":
        record = IpToo(
            user_id=current_user.id,
            type=result["type"],
            iin_bin=body.iin_bin,
            name=result.get("name"),
            status="verified",
            verified_at=datetime.now(UTC),
            is_active=True,
        )
    else:
        # pending_manual
        record = IpToo(
            user_id=current_user.id,
            type="ip",  # unknown until manual review
            iin_bin=body.iin_bin,
            name=result.get("name"),
            status="pending",
            is_active=True,
        )

    db.add(record)
    await db.commit()
    await db.refresh(record)
    return IpTooResponse.model_validate(record)


@IpTooRouter.get("", response_model=IpTooResponse | None)
async def get_ip_too(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IpTooResponse | None:
    """Return the current active IP/TOO record, or null."""
    record = (
        await db.execute(
            select(IpToo).where(
                IpToo.user_id == current_user.id, IpToo.is_active == True  # noqa: E712
            )
        )
    ).scalar_one_or_none()
    if record is None:
        return None
    return IpTooResponse.model_validate(record)


@IpTooRouter.delete("")
async def unlink_ip_too(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Soft-delete the active IP/TOO record."""
    record = (
        await db.execute(
            select(IpToo).where(
                IpToo.user_id == current_user.id, IpToo.is_active == True  # noqa: E712
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise ApplicationError("No active IP/TOO record found.", status_code=404)

    record.is_active = False
    await db.commit()
    return {"message": "IP/TOO unlinked"}
