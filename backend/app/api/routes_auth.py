"""
backend/app/api/routes_auth.py
--------------------------------
Authentication endpoints – registration, login, token refresh.

Depends on:
    - app.services.auth_service (register, login, refresh_token)
    - app.schemas.user_schema (UserCreate, LoginRequest, TokenResponse, etc.)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.user_schema import (
    UserCreate,
    UserResponse,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    AccessTokenResponse,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new forensic analyst or admin account.

    - **email**: must be unique
    - **password**: minimum 8 characters, must include uppercase, lowercase, and digit
    - **role**: defaults to 'analyst'
    """
    user = await auth_service.register(payload, db)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive access/refresh tokens",
)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate with email and password.

    Returns:
    - **access_token**: short-lived JWT for API authorization
    - **refresh_token**: long-lived JWT for obtaining new access tokens
    - **user**: profile of the authenticated user
    """
    return await auth_service.login(
        email=credentials.email,
        password=credentials.password,
        db=db,
    )


@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    summary="Obtain a new access token using a refresh token",
)
async def refresh(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Exchange a valid refresh token for a new access token.

    The refresh token must not be expired and must be of type 'refresh'.
    The user account must still exist and be active.
    """
    return await auth_service.refresh_token(payload.refresh_token, db)
