"""
backend/app/services/auth_service.py
--------------------------------------
Business logic for user authentication and token management.

Responsibilities
----------------
    register()      — create a new user account
    login()         — verify credentials, return access + refresh tokens
    refresh_token() — exchange a valid refresh token for a new access token

This service is the ONLY place passwords are hashed or verified.
Route handlers in routes_auth.py call these functions and return
the results directly — no auth logic lives in routes.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    UserRole,
)
from app.models.user       import User
from app.schemas.user_schema import (
    UserCreate,
    TokenResponse,
    AccessTokenResponse,
    UserResponse,
)


# ---------------------------------------------------------------------------
async def register(
    payload: UserCreate,
    db:      AsyncSession,
) -> User:
    """
    Register a new user account.

    Validates:
        - Email is not already taken
        - Password strength (enforced by UserCreate schema validator)

    Hashes the password with bcrypt before storing.
    Returns the created User ORM object.

    Raises:
        HTTP 409 — email already registered
    """
    # Check for duplicate email
    existing = await db.execute(
        select(User).where(User.email == payload.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code = status.HTTP_409_CONFLICT,
            detail      = f"Email '{payload.email}' is already registered.",
        )

    user = User(
        full_name     = payload.full_name,
        email         = payload.email,
        password_hash = hash_password(payload.password),
        role          = payload.role.value,
        is_active     = True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# ---------------------------------------------------------------------------
async def login(
    email:    str,
    password: str,
    db:       AsyncSession,
) -> TokenResponse:
    """
    Authenticate a user and return JWT access + refresh tokens.

    Intentionally returns the same error for both "user not found" and
    "wrong password" — revealing which one is true would help attackers
    enumerate valid email addresses.

    Raises:
        HTTP 401 — invalid credentials or inactive account
    """
    _credentials_error = HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail      = "Invalid email or password.",
        headers     = {"WWW-Authenticate": "Bearer"},
    )

    # Fetch user
    result = await db.execute(
        select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise _credentials_error

    # Verify password
    if not verify_password(password, user.password_hash):
        raise _credentials_error

    # Reject deactivated accounts
    if not user.is_active:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "Account deactivated. Contact your administrator.",
        )

    # Issue tokens
    access_token  = create_access_token(
        subject = user.email,
        role    = UserRole(user.role),
    )
    refresh_token = create_refresh_token(
        subject = user.email,
        role    = UserRole(user.role),
    )

    return TokenResponse(
        access_token  = access_token,
        refresh_token = refresh_token,
        token_type    = "bearer",
        user          = UserResponse.model_validate(user),
    )


# ---------------------------------------------------------------------------
async def refresh_token(
    token: str,
    db:    AsyncSession,
) -> AccessTokenResponse:
    """
    Exchange a valid refresh token for a new access token.

    The refresh token is validated (signature + expiry + type=refresh).
    The user is re-fetched from the database to ensure the account still
    exists and is still active — tokens issued before deactivation are
    rejected here.

    Raises:
        HTTP 401 — invalid/expired refresh token
        HTTP 401 — user no longer exists or is inactive
    """
    try:
        token_data = decode_token(token, expected_type="refresh")
    except ValueError as e:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = str(e),
            headers     = {"WWW-Authenticate": "Bearer"},
        )

    # Re-validate user still exists and is active
    result = await db.execute(
        select(User).where(User.email == token_data.subject)
    )
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "User not found or account deactivated.",
        )

    new_access_token = create_access_token(
        subject = user.email,
        role    = UserRole(user.role),
    )

    return AccessTokenResponse(
        access_token = new_access_token,
        token_type   = "bearer",
    )