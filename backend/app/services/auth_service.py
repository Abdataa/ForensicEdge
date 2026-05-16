"""
backend/app/services/auth_service.py
--------------------------------------
Business logic for user authentication and token management.

Responsibilities
----------------
    register()          — create a new user account (supports full UserCreate payload)
    login()             — verify credentials, return access + refresh tokens
    refresh_token()     — exchange a valid refresh token for a new access token
    change_password()   — verify current password, store new hash
    update_my_profile() — let a user update their own name / email / agency info
    create_first_admin()— bootstrap the system's first admin on startup

This service is the ONLY place passwords are hashed or verified.
Route handlers call these functions and return the results directly —
no auth logic lives in the routes.
"""
from datetime import datetime
from sqlalchemy import select, func
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
from app.models.user import User
from app.schemas.user_schema import (
    UserCreate,
    TokenResponse,
    AccessTokenResponse,
    UserResponse,
)


# ---------------------------------------------------------------------------
# Helper: Generate Unique Investigator ID
# ---------------------------------------------------------------------------
async def generate_investigator_id(db: AsyncSession) -> str:
    """
    Generates a forensic ID in the format: FE-ETH-YYYY-0000X
    """
    year = datetime.utcnow().year

    result = await db.execute(select(func.count(User.id)))
    count  = result.scalar() or 0
    next_num = count + 1

    return f"FE-ETH-{year}-{next_num:05d}"


# ---------------------------------------------------------------------------
async def register(
    payload: UserCreate,
    db:      AsyncSession,
) -> User:
    """
    Register a new user account.

    Persists all fields declared in UserCreate, including the optional
    agency / rank metadata introduced in the expanded User model:
        department, agency, rank, badge_number,
        clearance_level, employment_status.

    Validates:
        - Email is not already taken
        - Password strength (enforced by UserCreate schema validator)

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

    investigator_id = await generate_investigator_id(db)

    user = User(
        investigator_id   = investigator_id,
        full_name         = payload.full_name,
        email             = payload.email,
        password_hash     = hash_password(payload.password),
        role              = payload.role.value,
        is_active         = True,
        # ── Agency / rank metadata (optional at registration) ──────────────
        department        = payload.department,
        agency            = payload.agency,
        rank              = payload.rank,
        badge_number      = payload.badge_number,
        clearance_level   = payload.clearance_level   or 1,
        employment_status = payload.employment_status or "ACTIVE",
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
    "wrong password" to prevent email-enumeration attacks.

    Raises:
        HTTP 401 — invalid credentials or inactive account
    """
    _credentials_error = HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail      = "Invalid email or password.",
        headers     = {"WWW-Authenticate": "Bearer"},
    )

    result = await db.execute(select(User).where(User.email == email))
    user   = result.scalar_one_or_none()

    if user is None:
        raise _credentials_error

    if not verify_password(password, user.password_hash):
        raise _credentials_error

    if not user.is_active:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "Account deactivated. Contact your administrator.",
        )

    access_token  = create_access_token(subject=user.email, role=UserRole(user.role))
    refresh_token = create_refresh_token(subject=user.email, role=UserRole(user.role))

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

    Re-fetches the user from the database to ensure the account still
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

    return AccessTokenResponse(access_token=new_access_token, token_type="bearer")


# ---------------------------------------------------------------------------
async def change_password(
    user:             User,
    current_password: str,
    new_password:     str,
    db:               AsyncSession,
) -> None:
    """
    Change a user's password after verifying their current one.
    Called from POST /auth/change-password.

    Raises:
        HTTP 401 — current password is wrong
    """
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "Current password is incorrect.",
        )
    user.password_hash = hash_password(new_password)
    await db.commit()


# ---------------------------------------------------------------------------
async def create_first_admin(db: AsyncSession) -> None:
    """
    Create the initial admin account on first startup if no users exist.
    Credentials are read from FIRST_ADMIN_EMAIL and FIRST_ADMIN_PASSWORD
    in the .env file.

    Safe to call on every startup — does nothing if any user already exists.
    """
    from app.core.config import settings

    result = await db.execute(select(func.count(User.id)))
    count  = result.scalar()
    if count and count > 0:
        return

    email    = getattr(settings, "FIRST_ADMIN_EMAIL",    None)
    password = getattr(settings, "FIRST_ADMIN_PASSWORD", None)

    if not email or not password:
        print(
            "WARNING: No users exist but FIRST_ADMIN_EMAIL / "
            "FIRST_ADMIN_PASSWORD not set in .env. "
            "Add them and restart to create the first admin account."
        )
        return

    investigator_id = await generate_investigator_id(db)

    admin = User(
        investigator_id   = investigator_id,
        full_name         = "System Administrator",
        email             = email,
        password_hash     = hash_password(password),
        role              = UserRole.ADMIN.value,
        is_active         = True,
        clearance_level   = 5,
        employment_status = "ACTIVE",
    )
    db.add(admin)
    await db.commit()
    print(f"First admin account created: {email}")


# ---------------------------------------------------------------------------
async def update_my_profile(
    *,
    user:         User,
    full_name:    str | None,
    email:        str | None,
    department:   str | None = None,
    agency:       str | None = None,
    rank:         str | None = None,
    badge_number: str | None = None,
    db:           AsyncSession,
) -> User:
    """
    Update the currently authenticated user's own profile.

    Users may update: full_name, email, department, agency, rank, badge_number.
    Role, clearance_level, and employment_status are admin-only fields.
    """
    # Email uniqueness check
    if email and email != user.email:
        existing = await db.execute(select(User).where(User.email == email))
        existing_user = existing.scalar_one_or_none()
        if existing_user and existing_user.id != user.id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Email already in use.",
            )
        user.email = email

    if full_name:
        user.full_name = full_name

    # Optional agency metadata
    if department is not None:
        user.department = department
    if agency is not None:
        user.agency = agency
    if rank is not None:
        user.rank = rank
    if badge_number is not None:
        user.badge_number = badge_number

    await db.commit()
    await db.refresh(user)
    return user