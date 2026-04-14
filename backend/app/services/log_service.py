"""
backend/app/services/log_service.py
-------------------------------------
Forensic audit logging service.

Every significant action in the system is logged here — uploads,
comparisons, report generation, logins, admin changes.  This provides:
    1. Chain-of-custody trail required for forensic evidence admissibility
    2. Admin audit trail (report use case: "View Audit Logs")
    3. Investigator history (report use case: "Retrieve Analysis Logs")

Design
------
log_service is intentionally simple — it only does INSERT.
Audit logs are NEVER updated or deleted (enforced by not providing
update/delete functions here).

All other services call create_log() after completing their action.
"""

from typing import Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


# ---------------------------------------------------------------------------
async def create_log(
    db:          AsyncSession,
    action_type: str,
    user_id:     Optional[int]  = None,
    details:     Optional[dict] = None,
    ip_address:  Optional[str]  = None,
) -> AuditLog:
    """
    Insert one audit log entry.

    Args:
        db          : database session
        action_type : one of the values in ACTION_TYPE_ENUM
                      e.g. "image_uploaded", "comparison_completed"
        user_id     : who performed the action (None for system actions)
        details     : action-specific context as a dict
                      e.g. {"image_id": 42, "evidence_type": "toolmark"}
        ip_address  : requester IP from Request.client.host

    Returns:
        The created AuditLog ORM object.

    Example:
        await create_log(
            db          = db,
            action_type = "comparison_completed",
            user_id     = current_user.id,
            details     = {
                "result_id":   result.id,
                "similarity":  result.similarity_percentage,
                "status":      result.match_status,
                "evidence_type": "fingerprint",
            },
            ip_address  = request.client.host,
        )
    """
    log = AuditLog(
        action_type = action_type,
        user_id     = user_id,
        details     = details or {},
        ip_address  = ip_address,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


# ---------------------------------------------------------------------------
async def list_logs(
    db:           AsyncSession,
    page:         int           = 1,
    limit:        int           = 50,
    user_id:      Optional[int] = None,
    action_type:  Optional[str] = None,
) -> tuple[list[AuditLog], int]:
    """
    Retrieve paginated audit logs with optional filters.

    Used by:
        - Admin dashboard: all logs, filterable by user or action
        - Investigator dashboard: their own logs only (user_id = current_user.id)

    Args:
        page        : 1-based page number
        limit       : records per page (max 100)
        user_id     : filter to one user's logs (None = all users)
        action_type : filter to one action type (None = all actions)

    Returns:
        (logs, total_count) tuple for pagination metadata.
    """
    limit = min(limit, 100)     # cap to prevent huge queries

    query = select(AuditLog).order_by(desc(AuditLog.timestamp))

    if user_id is not None:
        query = query.where(AuditLog.user_id == user_id)
    if action_type is not None:
        query = query.where(AuditLog.action_type == action_type)

    # Total count (for pagination)
    count_result = await db.execute(
        query.with_only_columns(AuditLog.id)
    )
    total = len(count_result.all())

    # Paginated results
    offset = (page - 1) * limit
    result = await db.execute(query.offset(offset).limit(limit))
    logs   = result.scalars().all()

    return list(logs), total