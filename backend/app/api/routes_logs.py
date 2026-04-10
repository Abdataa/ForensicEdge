"""
backend/app/api/routes_logs.py
--------------------------------
Investigator's own activity log endpoints.

Endpoints
---------
    GET /api/v1/logs         — list current user's own audit logs

From report scenario 5:
    "Investigator opens 'Analysis History'. System retrieves stored metadata,
     similarity scores, timestamps, and report files. Investigator can filter,
     sort, and view past analysis records easily."

Note: Admin-level logs (all users) are in routes_admin.py.
This file only exposes a user's OWN activity history.
"""

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database     import get_db
from app.core.dependencies import CurrentUser
from app.services.log_service import list_logs

router = APIRouter(prefix="/logs", tags=["Activity Logs"])


# ---------------------------------------------------------------------------
@router.get(
    "",
    summary = "Get your activity history",
)
async def get_my_logs(
    action_type:  Optional[str] = None,
    page:         int           = 1,
    limit:        int           = 50,
    current_user: CurrentUser   = Depends(),
    db:           AsyncSession  = Depends(get_db),
):
    """
    Retrieve the current user's own activity history.

    - **action_type**: filter by action type (e.g. `image_uploaded`,
      `comparison_completed`, `report_generated`)
    - Results are ordered newest-first

    This supports the "Analysis History" dashboard view where investigators
    can review their past uploads, comparisons, and reports.
    """
    logs, total = await list_logs(
        db          = db,
        page        = page,
        limit       = limit,
        user_id     = current_user.id,   # always scoped to current user
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
                "details":     log.details,
                "timestamp":   log.timestamp,
            }
            for log in logs
        ],
    }