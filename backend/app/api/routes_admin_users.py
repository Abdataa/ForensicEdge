"""
backend/app/api/routes_admin_users.py
---------------------------------------
Admin endpoints for user management.

Depends on:
    - app.services.user_service (create, update, delete, list, etc.)
    - app.schemas.user_schema (UserCreate, UserUpdate, UserResponse, UserListResponse)
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.api.dependencies import get_current_active_user, require_role
from app.models.user import User
from app.schemas.user_schema import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
)
from app.services import user_service  # assumed to exist, similar pattern

router = APIRouter(prefix="/admin/users", tags=["Admin - Users"])


@router.get(
    "",
    response_model=UserListResponse,
    dependencies=[Depends(require_role(["admin"]))],
    summary="List all users",
)
async def list_users(
    page: int = 1,
    limit: int = 20,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve a paginated list of all registered users.
    Admin only.
    """
    return await user_service.list_users(
        db=db,
        page=page,
        limit=limit,
        role=role,
        is_active=is_active,
    )


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(["admin"]))],
    summary="Create a new user (admin only)",
)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Admin can create any user account directly."""
    return await user_service.create_user(payload, db)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_role(["admin"]))],
    summary="Get user details",
)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve details of a specific user."""
    return await user_service.get_user_by_id(user_id, db)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_role(["admin"]))],
    summary="Update a user",
)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update user fields (full_name, email, role, active status, password)."""
    return await user_service.update_user(user_id, payload, db)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(["admin"]))],
    summary="Delete a user",
)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete a user account (admin only)."""
    await user_service.delete_user(user_id, db)