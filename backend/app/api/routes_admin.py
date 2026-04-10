"""
backend/app/api/routes_admin.py
---------------------------------
System administration endpoints — admin role only.

Endpoints
---------
    GET    /api/v1/admin/users              — list all users
    POST   /api/v1/admin/users              — create user (admin bypass)
    GET    /api/v1/admin/users/{user_id}    — get user details
    PATCH  /api/v1/admin/users/{user_id}    — update user (role, active, etc.)
    DELETE /api/v1/admin/users/{user_id}    — delete user account
    GET    /api/v1/admin/logs               — view all audit logs
    GET    /api/v1/admin/health             — system health check

All routes require role=admin via AdminUser dependency.

From project report scenario 3:
    "Admin creates, updates, deactivates, or deletes user (investigator) accounts."
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database     import get_db, check_db_connection
from app.core.dependencies import AdminUser
from app.core.security     import hash_password
from app.models.user       import User
from app.schemas.user_schema import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
)
from app.services             import auth_service
from app.services.log_service import create_log, list_logs

router = APIRouter(prefix="/admin", tags=["Administration"])


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------

@router.get(
    "/users",
    response_model = UserListResponse,
    summary        = "List all system users",
)
async def list_users(
    role:       Optional[str] = None,
    is_active:  Optional[bool] = None,
    page:       int  = 1,
    limit:      int  = 20,
    _:          AdminUser   = Depends(),
    db:         AsyncSession = Depends(get_db),
):
    """
    List all registered users with optional filters.
    - **role**: filter by analyst | admin | ai_engineer
    - **is_active**: filter by account status
    """
    limit = min(limit, 100)
    query = select(User)

    if role:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)

    count_result = await db.execute(query.with_only_columns(User.id))
    total = len(count_result.all())

    from sqlalchemy import desc
    offset = (page - 1) * limit
    rows   = await db.execute(
        query.order_by(desc(User.created_at)).offset(offset).limit(limit)
    )
    users = rows.scalars().all()

    return UserListResponse(
        total = total,
        page  = page,
        limit = limit,
        users = [UserResponse.model_validate(u) for u in users],
    )


# ---------------------------------------------------------------------------
@router.post(
    "/users",
    response_model = UserResponse,
    status_code    = status.HTTP_201_CREATED,
    summary        = "Create a user account (admin)",
)
async def create_user(
    payload: UserCreate,
    request: Request,
    admin:   AdminUser   = Depends(),
    db:      AsyncSession = Depends(get_db),
):
    """
    Create a new user account directly as admin.
    Bypasses the public registration endpoint — allows creating
    admin and ai_engineer accounts.
    """
    user = await auth_service.register(payload, db)

    await create_log(
        db          = db,
        action_type = "user_created",
        user_id     = admin.id,
        details     = {
            "created_user_id": user.id,
            "email":           user.email,
            "role":            user.role,
        },
        ip_address  = request.client.host if request.client else None,
    )
    return UserResponse.model_validate(user)


# ---------------------------------------------------------------------------
@router.get(
    "/users/{user_id}",
    response_model = UserResponse,
    summary        = "Get a user by ID",
)
async def get_user(
    user_id: int,
    _:       AdminUser    = Depends(),
    db:      AsyncSession = Depends(get_db),
):
    """Retrieve details for any user by their ID."""
    row  = await db.execute(select(User).where(User.id == user_id))
    user = row.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = f"User {user_id} not found.",
        )
    return UserResponse.model_validate(user)


# ---------------------------------------------------------------------------
@router.patch(
    "/users/{user_id}",
    response_model = UserResponse,
    summary        = "Update a user account",
)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    request: Request,
    admin:   AdminUser    = Depends(),
    db:      AsyncSession = Depends(get_db),
):
    """
    Update a user's profile, role, or active status.
    All fields are optional — only provided fields are changed.

    Common uses:
    - Deactivate an account: `{"is_active": false}`
    - Promote to admin:      `{"role": "admin"}`
    - Reset password:        `{"password": "NewPass123!"}`
    """
    row  = await db.execute(select(User).where(User.id == user_id))
    user = row.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = f"User {user_id} not found.",
        )

    update_data = payload.model_dump(exclude_unset=True)

    # Hash password if being updated
    if "password" in update_data:
        update_data["password_hash"] = hash_password(update_data.pop("password"))

    # Convert role enum to string value
    if "role" in update_data and hasattr(update_data["role"], "value"):
        update_data["role"] = update_data["role"].value

    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    await create_log(
        db          = db,
        action_type = "user_updated",
        user_id     = admin.id,
        details     = {
            "updated_user_id": user_id,
            "fields_changed":  list(update_data.keys()),
        },
        ip_address  = request.client.host if request.client else None,
    )
    return UserResponse.model_validate(user)


# ---------------------------------------------------------------------------
@router.delete(
    "/users/{user_id}",
    status_code = status.HTTP_204_NO_CONTENT,
    summary     = "Delete a user account",
)
async def delete_user(
    user_id: int,
    request: Request,
    admin:   AdminUser    = Depends(),
    db:      AsyncSession = Depends(get_db),
):
    """
    Permanently delete a user account.
    Consider deactivating instead to preserve audit history.
    Audit logs linked to this user are preserved (SET NULL on user FK).
    """
    # Prevent admin from deleting their own account
    if user_id == admin.id:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = "Cannot delete your own admin account.",
        )

    row  = await db.execute(select(User).where(User.id == user_id))
    user = row.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = f"User {user_id} not found.",
        )

    # Log before deletion (user_id still exists in DB at this point)
    await create_log(
        db          = db,
        action_type = "user_deleted",
        user_id     = admin.id,
        details     = {
            "deleted_user_id": user_id,
            "email":           user.email,
        },
        ip_address  = request.client.host if request.client else None,
    )

    await db.delete(user)
    await db.commit()


# ---------------------------------------------------------------------------
# Audit logs
# ---------------------------------------------------------------------------

@router.get(
    "/logs",
    summary = "View system audit logs",
)
async def get_audit_logs(
    user_id:     Optional[int] = None,
    action_type: Optional[str] = None,
    page:        int           = 1,
    limit:       int           = 50,
    _:           AdminUser     = Depends(),
    db:          AsyncSession  = Depends(get_db),
):
    """
    Retrieve paginated system audit logs.

    - **user_id**: filter to one user's actions
    - **action_type**: filter by action (e.g. `image_uploaded`, `comparison_completed`)
    - Returns logs ordered newest-first
    """
    logs, total = await list_logs(
        db          = db,
        page        = page,
        limit       = limit,
        user_id     = user_id,
        action_type = action_type,
    )
    return {
        "total":  total,
        "page":   page,
        "limit":  limit,
        "logs": [
            {
                "id":          log.id,
                "action_type": log.action_type,
                "user_id":     log.user_id,
                "details":     log.details,
                "ip_address":  log.ip_address,
                "timestamp":   log.timestamp,
            }
            for log in logs
        ],
    }


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@router.get(
    "/health",
    summary = "System health check",
    tags    = ["Administration", "Health"],
)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Check system component health.
    Returns status of database connection and AI model availability.
    Does not require authentication — used by deployment health probes.
    """
    from pathlib import Path
    from app.core.config import settings

    db_ok = await check_db_connection()

    fp_weights = Path(settings.MODEL_WEIGHTS_PATH_FINGERPRINT
                      if hasattr(settings, "MODEL_WEIGHTS_PATH_FINGERPRINT")
                      else settings.MODEL_WEIGHTS_PATH)
    tm_weights = Path("ai_engine/models/weights/toolmark/best_model.pth")

    return {
        "status": "ok" if db_ok else "degraded",
        "components": {
            "database":           "ok" if db_ok else "error",
            "model_fingerprint":  "ok" if fp_weights.exists() else "not_loaded",
            "model_toolmark":     "ok" if tm_weights.exists() else "not_loaded",
        },
    }