import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from app.api.deps import get_current_user, require_roles
from app.core.security import Role, create_access_token, verify_token
from app.utils.hashing import hash_password, verify_password


def test_password_hash_round_trip():
    secret = "SuperSecret123!"
    hashed = hash_password(secret)
    assert hashed != secret
    assert verify_password(secret, hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_round_trip():
    token = create_access_token("user-123", Role.SUPPLIER_OWNER)
    payload = verify_token(token)
    assert payload.sub == "user-123"
    assert payload.role == Role.SUPPLIER_OWNER
    assert payload.token_type == "access"


@pytest.mark.asyncio
async def test_role_guard_denies_unauthorized():
    token = create_access_token("user-456", Role.CONSUMER)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    user = await get_current_user(credentials)
    guard = require_roles(Role.SUPPLIER_OWNER)

    with pytest.raises(HTTPException) as exc:
        await guard(user=user)

    assert exc.value.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_role_guard_allows_authorized():
    token = create_access_token("user-789", Role.SUPPLIER_MANAGER)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    user = await get_current_user(credentials)
    guard = require_roles(Role.SUPPLIER_MANAGER, Role.SUPPLIER_OWNER)

    result = await guard(user=user)
    assert result.role == Role.SUPPLIER_MANAGER
