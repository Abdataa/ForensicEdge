"""
backend/app/api/routes_logs.py
--------------------------------
Endpoints for viewing audit logs (admin) and user's own activity (analyst).

Depends on:
    - app.services.log_service (list_logs)
"""

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.api.dependencies import get_current_active_user, require_role
from app.models.user import User
from app.services import log_service

router = APIRouter(prefix="/logs", tags=["Audit Logs"])


@router.get(
    "",
    summary="List audit logs",
)
async def list_logs(
    page: int = 1,
    limit: int = 50,
    action_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve audit log entries.

    - **Admin**: sees all logs; can filter by `action_type` or `user_id`
    - **Analyst**: sees only logs for actions they performed
    """
    if current_user.role == "admin":
        # Admin can optionally filter by user_id via query param
        user_id = None  # would come from query param if implemented
        logs, total = await log_service.list_logs(
            db=db,
            page=page,
            limit=limit,
            user_id=user_id,
            action_type=action_type,
        )
    else:
        logs, total = await log_service.list_logs(
            db=db,
            page=page,
            limit=limit,
            user_id=current_user.id,
            action_type=action_type,
        )

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "logs": logs,
    }