"""
backend/app/api/routes_auth.py
--------------------------------
Authentication endpoints — register, login, token refresh.

Endpoints
---------
    POST /api/v1/auth/register   — create new user account
    POST /api/v1/auth/login      — authenticate and receive tokens
    POST /api/v1/auth/refresh    — exchange refresh token for new access token
    GET  /api/v1/auth/me         — return current user profile
"""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database      import get_db
from app.core.dependencies  import CurrentUser
from app.schemas.user_schema import (
    LoginRequest,
    RefreshRequest,
    ChangePasswordRequest,
    TokenResponse,
    AccessTokenResponse,
    UserResponse,
)
from app.services             import auth_service
from app.services.log_service import create_log

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ---------------------------------------------------------------------------
#router.post(
#   "/register",
#   response_model = UserResponse,
#   status_code    = status.HTTP_201_CREATED,
#   summary        = "Register a new user account",
#
#sync def register(
#   payload: UserCreate,
#   request: Request,
#   db:      AsyncSession = Depends(get_db),
#:
#   """
#   Register a new forensic analyst, admin, or AI engineer account.
#
#   - **full_name**: display name (2–120 chars)
#   - **email**: must be unique in the system
#   - **password**: min 8 chars, must include uppercase, lowercase, digit
#   - **role**: analyst | admin | ai_engineer  (default: analyst)
#   """
#   user = await auth_service.register(payload, db)
#
#   await create_log(
#       db          = db,
#       action_type = "user_registered",
#       user_id     = user.id,
#       details     = {"email": user.email, "role": user.role},
#       ip_address  = request.client.host if request.client else None,
#   )
# #  return UserResponse.model_validate(user)
##
#_

# ---------------------------------------------------------------------------
@router.post(
    "/login",
    response_model = TokenResponse,
    summary        = "Login and receive JWT tokens",
)
async def login(
    payload: LoginRequest,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    """
    Authenticate with email and password.

    Returns:
    - **access_token**: short-lived JWT (60 min) — send in Authorization header
    - **refresh_token**: long-lived JWT (7 days) — use to get new access tokens
    - **user**: authenticated user profile
    """
    token_response = await auth_service.login(
        email    = payload.email,
        password = payload.password,
        db       = db,
    )
    await create_log(
        db          = db,
        action_type = "user_login",
        user_id     = token_response.user.id,
        details     = {"email": payload.email},
        ip_address  = request.client.host if request.client else None,
    )
    return token_response


# ---------------------------------------------------------------------------
@router.post(
    "/refresh",
    response_model = AccessTokenResponse,
    summary        = "Refresh access token",
)
async def refresh(
    payload: RefreshRequest,
    db:      AsyncSession = Depends(get_db),
):
    """
    Exchange a valid refresh token for a new access token.
    The refresh token itself is unchanged.
    """
    return await auth_service.refresh_token(token=payload.refresh_token, db=db)


# ---------------------------------------------------------------------------
@router.get(
    "/me",
    response_model = UserResponse,
    summary        = "Get current user profile",
)
async def get_me(current_user: CurrentUser):
    """Return the profile of the currently authenticated user."""
    return UserResponse.model_validate(current_user)

#--------------------------------------------------
@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    current_user: CurrentUser,
    payload:      ChangePasswordRequest,
    db:           AsyncSession = Depends(get_db),

):
    """
    Change the current user's own password.
    Requires the current password to be provided for verification.
    Used after admin assigns a temporary password on account creation.
    """
    await auth_service.change_password(
        user=current_user,
        current_password=payload.current_password,
        new_password=payload.new_password,
        db=db,
    )
    return {"message": "Password changed successfully."}