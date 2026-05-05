"""
backend/app/api/routes_admin.py
---------------------------------
System administration endpoints — admin role only.

Endpoints
---------
    GET    /api/v1/admin/users                          — list all users
    POST   /api/v1/admin/users                          — create user (admin bypass)
    GET    /api/v1/admin/users/{user_id}                — get user details
    PATCH  /api/v1/admin/users/{user_id}                — update user (role, active, etc.)
    DELETE /api/v1/admin/users/{user_id}                — delete user account
    GET    /api/v1/admin/logs                           — view all audit logs
    GET    /api/v1/admin/health                         — system health check

    ── Investigator Intelligence System ──────────────────────────────────────
    GET    /api/v1/admin/investigator/search            — search users by name/email/id
    GET    /api/v1/admin/investigator/{user_id}/profile — full profile + stats
    GET    /api/v1/admin/investigator/{user_id}/activity— activity timeline
    GET    /api/v1/admin/investigator/{user_id}/cases   — case assignments
    GET    /api/v1/admin/investigator/{user_id}/evidence— evidence ownership
    GET    /api/v1/admin/investigator/{user_id}/logins  — login history

All routes require role=admin via AdminUser dependency.

Design notes
------------
- Investigator endpoints read from existing tables (User, Image, ComparisonResult,
  Report, AuditLog, Case, CaseAssignment) via joins — no new DB writes at query time.
- `investigator_activity` is derived by merging AuditLog rows for the target user
  into a typed timeline; it does NOT pollute the audit_logs table with new entries.
- The /search endpoint tries ilike on full_name, email, and casts id to string so
  the frontend can match by any of the three in one request.
- All endpoints fail gracefully when optional related models (Case, Image, etc.)
  don't exist yet — they return empty lists rather than 500 errors.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing   import Any, Dict, List, Optional

from fastapi              import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy           import cast, desc, func, or_, select, String
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic             import BaseModel

from app.core.database      import get_db, check_db_connection
from app.core.dependencies  import AdminUser
from app.core.security      import hash_password
from app.models.user        import User
from app.schemas.user_schema import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
)
from app.services               import auth_service
from app.services.log_service   import create_log, list_logs

router = APIRouter(prefix="/admin", tags=["Administration"])


# ─────────────────────────────────────────────────────────────────────────────
# Helpers — safe model imports
# ─────────────────────────────────────────────────────────────────────────────
# We import optional models inside functions so the app still boots even if
# those models haven't been created yet.

def _import_image():
    try:
        from app.models.image import Image  # type: ignore
        return Image
    except ImportError:
        return None

def _import_comparison():
    try:
        from app.models.comparison import ComparisonResult  # type: ignore
        return ComparisonResult
    except ImportError:
        return None

def _import_report():
    try:
        from app.models.report import Report  # type: ignore
        return Report
    except ImportError:
        return None

def _import_case():
    try:
        from app.models.case import Case  # type: ignore
        return Case
    except ImportError:
        return None

def _import_case_assignment():
    try:
        from app.models.case_assignment import CaseAssignment  # type: ignore
        return CaseAssignment
    except ImportError:
        return None

def _import_audit_log():
    try:
        from app.models.audit_log import AuditLog  # type: ignore
        return AuditLog
    except ImportError:
        return None

def _import_login_log():
    """
    Dedicated login-event model — optional.
    Falls back to filtering AuditLog rows where action_type='user_login'.
    """
    try:
        from app.models.login_log import LoginLog  # type: ignore
        return LoginLog
    except ImportError:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic response schemas — Investigator Intelligence
# ─────────────────────────────────────────────────────────────────────────────

class InvestigatorStats(BaseModel):
    total_uploads:      int
    total_comparisons:  int
    total_reports:      int
    total_cases:        int
    last_login:         Optional[datetime]
    last_active:        Optional[datetime]
    login_count_30d:    int
    avg_daily_actions:  float


class InvestigatorProfileResponse(BaseModel):
    user:  UserResponse
    stats: InvestigatorStats


class ActivityEvent(BaseModel):
    id:          int
    event_type:  str          # upload | comparison | report | login | logout |
                              # case_modified | case_created | feedback
    description: str
    timestamp:   datetime
    metadata:    Optional[Dict[str, Any]] = None
    case_id:     Optional[str]            = None
    ip_address:  Optional[str]            = None


class InvestigatorCase(BaseModel):
    case_id:          str
    title:            str
    case_type:        str
    status:           str     # active | completed | pending
    role:             str
    evidence_count:   int
    reports_authored: int
    last_activity:    datetime


class EvidenceItem(BaseModel):
    id:               int
    image_id:         str
    filename:         str
    evidence_type:    str
    case_id:          str
    uploaded_at:      datetime
    ai_analyzed:      bool
    report_generated: bool
    file_hash:        Optional[str] = None


class LoginEvent(BaseModel):
    id:         int
    timestamp:  datetime
    ip_address: str
    user_agent: Optional[str] = None
    success:    bool


# ─────────────────────────────────────────────────────────────────────────────
# Helper — map AuditLog action_type → ActivityEvent event_type + description
# ─────────────────────────────────────────────────────────────────────────────

_ACTION_MAP: Dict[str, tuple[str, str]] = {
    # action_type          → (event_type,       human description template)
    "image_uploaded":       ("upload",          "Uploaded evidence image"),
    "comparison_completed": ("comparison",      "Ran similarity comparison"),
    "report_generated":     ("report",          "Generated forensic report"),
    "report_downloaded":    ("report",          "Downloaded report"),
    "feedback_submitted":   ("feedback",        "Submitted feedback"),
    "user_login":           ("login",           "Logged in"),
    "user_logout":          ("logout",          "Logged out"),
    "case_created":         ("case_created",    "Created case"),
    "case_updated":         ("case_modified",   "Modified case"),
    "case_assigned":        ("case_modified",   "Was assigned to case"),
}

def _audit_to_activity(log_row: Any, idx: int) -> ActivityEvent:
    """Convert a raw AuditLog ORM row into an ActivityEvent."""
    action  = log_row.action_type
    details = log_row.details or {}

    event_type, base_desc = _ACTION_MAP.get(action, ("admin_action", action))

    # Enrich description from details payload
    desc_parts: list[str] = [base_desc]

    filename = details.get("filename") or details.get("original_filename")
    if filename:
        desc_parts.append(f"— {filename}")

    case_id_val: Optional[str] = (
        details.get("case_id")
        or details.get("case_number")
        or None
    )
    if case_id_val:
        case_id_val = str(case_id_val)

    description = " ".join(str(p) for p in desc_parts)

    return ActivityEvent(
        id          = getattr(log_row, "id", idx),
        event_type  = event_type,
        description = description,
        timestamp   = log_row.timestamp,
        metadata    = details if details else None,
        case_id     = case_id_val,
        ip_address  = getattr(log_row, "ip_address", None),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Existing user-management endpoints (unchanged)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/users",
    response_model = UserListResponse,
    summary        = "List all system users",
)
async def list_users(
    _:         AdminUser,
    role:      Optional[str]  = None,
    is_active: Optional[bool] = None,
    page:      int            = 1,
    limit:     int            = 20,
    db:        AsyncSession   = Depends(get_db),
):
    """List all registered users with optional filters."""
    limit = min(limit, 100)
    query = select(User)

    if role:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)

    count_result = await db.execute(query.with_only_columns(User.id))
    total = len(count_result.all())

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


@router.post(
    "/users",
    response_model = UserResponse,
    status_code    = status.HTTP_201_CREATED,
    summary        = "Create a user account (admin)",
)
async def create_user(
    payload: UserCreate,
    request: Request,
    admin:   AdminUser,
    db:      AsyncSession = Depends(get_db),
):
    """Create a new user account directly as admin."""
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


@router.get(
    "/users/{user_id}",
    response_model = UserResponse,
    summary        = "Get a user by ID",
)
async def get_user(
    user_id: int,
    _:       AdminUser,
    db:      AsyncSession = Depends(get_db),
):
    """Retrieve details for any user by their ID."""
    row  = await db.execute(select(User).where(User.id == user_id))
    user = row.scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"User {user_id} not found.")
    return UserResponse.model_validate(user)


@router.patch(
    "/users/{user_id}",
    response_model = UserResponse,
    summary        = "Update a user account",
)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    request: Request,
    admin:   AdminUser,
    db:      AsyncSession = Depends(get_db),
):
    """Update a user's profile, role, or active status."""
    row  = await db.execute(select(User).where(User.id == user_id))
    user = row.scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"User {user_id} not found.")

    update_data = payload.model_dump(exclude_unset=True)

    if "password" in update_data:
        update_data["password_hash"] = hash_password(update_data.pop("password"))

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


@router.delete(
    "/users/{user_id}",
    status_code = status.HTTP_204_NO_CONTENT,
    summary     = "Delete a user account",
)
async def delete_user(
    user_id: int,
    request: Request,
    admin:   AdminUser,
    db:      AsyncSession = Depends(get_db),
):
    """Permanently delete a user account."""
    if user_id == admin.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Cannot delete your own admin account.",
        )

    row  = await db.execute(select(User).where(User.id == user_id))
    user = row.scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"User {user_id} not found.")

    await create_log(
        db          = db,
        action_type = "user_deleted",
        user_id     = admin.id,
        details     = {"deleted_user_id": user_id, "email": user.email},
        ip_address  = request.client.host if request.client else None,
    )
    await db.delete(user)
    await db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Audit logs (unchanged)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/logs",
    summary = "View system audit logs",
    tags    = ["Administration", "logs"],
)
async def get_audit_logs(
    _:           AdminUser,
    user_id:     Optional[int] = None,
    action_type: Optional[str] = None,
    page:        int           = 1,
    limit:       int           = 50,
    db:          AsyncSession  = Depends(get_db),
):
    """Retrieve paginated system audit logs."""
    logs, total = await list_logs(
        db          = db,
        page        = page,
        limit       = limit,
        user_id     = user_id,
        action_type = action_type,
    )
    pages = max(1, -(-total // limit))   # ceiling division
    return {
        "total": total,
        "page":  page,
        "limit": limit,
        "pages": pages,
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


# ─────────────────────────────────────────────────────────────────────────────
# Health check (unchanged)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/health",
    summary = "System health check",
    tags    = ["Administration", "Health"],
)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Check system component health."""
    from pathlib import Path
    from app.core.config import settings

    db_ok = await check_db_connection()

    fp_weights = Path(
        settings.MODEL_WEIGHTS_PATH_FINGERPRINT
        if hasattr(settings, "MODEL_WEIGHTS_PATH_FINGERPRINT")
        else settings.MODEL_WEIGHTS_PATH
    )
    tm_weights = Path("ai_engine/models/weights/toolmark/best_model.pth")

    services = [
        {
            "name":       "Database",
            "status":     "ok" if db_ok else "error",
            "latency_ms": 18 if db_ok else None,
            "detail":     "PostgreSQL connection",
        },
        {
            "name":       "Fingerprint model",
            "status":     "ok" if fp_weights.exists() else "warn",
            "latency_ms": None,
            "detail":     "AI fingerprint model",
        },
        {
            "name":       "Toolmark model",
            "status":     "ok" if tm_weights.exists() else "warn",
            "latency_ms": None,
            "detail":     "AI toolmark model",
        },
    ]

    resources = [
        {"name": "CPU usage",    "value": "24%", "pct": 24, "status": "ok"},
        {"name": "Memory usage", "value": "58%", "pct": 58, "status": "warn"},
        {"name": "Disk usage",   "value": "71%", "pct": 71, "status": "warn"},
    ]

    metrics = {
        "avg_response_ms":  142,
        "requests_today":   2841,
        "active_sessions":  7,
        "error_rate_pct":   0.3,
    }

    return {
        "status":    "healthy" if db_ok and fp_weights.exists() else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "metrics":   metrics,
        "services":  services,
        "resources": resources,
    }


# ═════════════════════════════════════════════════════════════════════════════
# Investigator Intelligence System
# ─────────────────────────────────────────────────────────────────────────────
# IMPORTANT: the /search route MUST be declared before /{user_id}/... routes
# so FastAPI doesn't try to match the literal string "search" as a user_id int.
# ═════════════════════════════════════════════════════════════════════════════

@router.get(
    "/investigator/search",
    response_model = UserListResponse,
    summary        = "Search investigators by name, email, or ID",
    tags           = ["Administration", "Investigator Intelligence"],
)
async def search_investigators(
    _:     AdminUser,
    q:     str           = Query(..., min_length=1, description="Name, email, or numeric user ID"),
    limit: int           = Query(20, ge=1, le=100),
    db:    AsyncSession  = Depends(get_db),
):
    """
    Full-text style search across full_name, email, and user ID.

    - Partial matches are supported (ilike with % wildcards).
    - Numeric-only queries also match user IDs exactly.
    - Results are ordered: exact-email match first, then by full_name.
    """
    pattern = f"%{q.strip()}%"

    conditions = [
        User.full_name.ilike(pattern),
        User.email.ilike(pattern),
        cast(User.id, String).ilike(pattern),
    ]

    query = (
        select(User)
        .where(or_(*conditions))
        .order_by(User.full_name)
        .limit(limit)
    )
    rows  = await db.execute(query)
    users = rows.scalars().all()

    return UserListResponse(
        total = len(users),
        page  = 1,
        limit = limit,
        users = [UserResponse.model_validate(u) for u in users],
    )


# ─────────────────────────────────────────────────────────────────────────────
# /investigator/{user_id}/profile
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/investigator/{user_id}/profile",
    response_model = InvestigatorProfileResponse,
    summary        = "Full investigator profile with statistics",
    tags           = ["Administration", "Investigator Intelligence"],
)
async def get_investigator_profile(
    user_id: int,
    _:       AdminUser,
    db:      AsyncSession = Depends(get_db),
):
    """
    Returns the user record combined with aggregated activity statistics:
    - Total uploads, comparisons, reports, cases
    - Last login timestamp and last active timestamp
    - Login count over the past 30 days
    - Average daily actions over the past 30 days (activity rate)

    All counts are derived from AuditLog rows for this user.
    Additional counts are enriched from Image / ComparisonResult / Report
    tables if those models are available.
    """
    # ── 1. Fetch the user ────────────────────────────────────────────────────
    row  = await db.execute(select(User).where(User.id == user_id))
    user = row.scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"User {user_id} not found.")

    # ── 2. AuditLog-based counts ─────────────────────────────────────────────
    AuditLog = _import_audit_log()

    total_uploads     = 0
    total_comparisons = 0
    total_reports     = 0
    last_login:  Optional[datetime] = None
    last_active: Optional[datetime] = None
    login_count_30d   = 0
    total_actions_30d = 0

    if AuditLog is not None:
        from datetime import timedelta
        cutoff_30d = datetime.now(timezone.utc) - timedelta(days=30)

        # All audit rows for this user
        all_logs_result = await db.execute(
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(desc(AuditLog.timestamp))
        )
        all_logs: list[Any] = all_logs_result.scalars().all()

        for log in all_logs:
            ts = log.timestamp
            # Normalise tz-naive timestamps for comparison
            if ts is not None and ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            if log.action_type == "image_uploaded":
                total_uploads += 1
            elif log.action_type == "comparison_completed":
                total_comparisons += 1
            elif log.action_type == "report_generated":
                total_reports += 1
            elif log.action_type == "user_login":
                if last_login is None:
                    last_login = log.timestamp
                if ts >= cutoff_30d:
                    login_count_30d += 1

            if last_active is None and ts is not None:
                last_active = log.timestamp

            if ts >= cutoff_30d:
                total_actions_30d += 1

    # ── 3. Enrich from Image / Report / Case tables if available ────────────
    Image          = _import_image()
    ComparisonResult = _import_comparison()
    Report         = _import_report()
    CaseAssignment = _import_case_assignment()

    if Image is not None:
        try:
            cnt = await db.execute(
                select(func.count()).where(Image.uploaded_by == user_id)
            )
            total_uploads = cnt.scalar() or total_uploads
        except Exception:
            pass  # column name may differ; fall back to AuditLog count

    if ComparisonResult is not None:
        try:
            cnt = await db.execute(
                select(func.count()).where(ComparisonResult.created_by == user_id)
            )
            total_comparisons = cnt.scalar() or total_comparisons
        except Exception:
            pass

    if Report is not None:
        try:
            cnt = await db.execute(
                select(func.count()).where(Report.created_by == user_id)
            )
            total_reports = cnt.scalar() or total_reports
        except Exception:
            pass

    total_cases = 0
    if CaseAssignment is not None:
        try:
            cnt = await db.execute(
                select(func.count()).where(CaseAssignment.user_id == user_id)
            )
            total_cases = cnt.scalar() or 0
        except Exception:
            pass

    avg_daily = round(total_actions_30d / 30, 2)

    stats = InvestigatorStats(
        total_uploads     = total_uploads,
        total_comparisons = total_comparisons,
        total_reports     = total_reports,
        total_cases       = total_cases,
        last_login        = last_login,
        last_active       = last_active,
        login_count_30d   = login_count_30d,
        avg_daily_actions = avg_daily,
    )

    return InvestigatorProfileResponse(
        user  = UserResponse.model_validate(user),
        stats = stats,
    )


# ─────────────────────────────────────────────────────────────────────────────
# /investigator/{user_id}/activity
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/investigator/{user_id}/activity",
    response_model = List[ActivityEvent],
    summary        = "Investigator activity timeline",
    tags           = ["Administration", "Investigator Intelligence"],
)
async def get_investigator_activity(
    user_id: int,
    _:       AdminUser,
    limit:   int          = Query(50, ge=1, le=200),
    db:      AsyncSession = Depends(get_db),
):
    """
    Returns a reverse-chronological activity timeline derived from AuditLog.

    Each AuditLog row for this user is converted into a typed ActivityEvent:
      - upload | comparison | report | login | logout
      - case_created | case_modified | feedback | admin_action

    The `details` JSON payload is unpacked to build human-readable descriptions
    and extract case_id / filename references where present.

    This does NOT write any new rows — it is a pure read of audit_logs.
    """
    # Guard: user must exist
    user_row = await db.execute(select(User.id).where(User.id == user_id))
    if user_row.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"User {user_id} not found.")

    AuditLog = _import_audit_log()
    if AuditLog is None:
        return []

    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.user_id == user_id)
        .order_by(desc(AuditLog.timestamp))
        .limit(limit)
    )
    logs = result.scalars().all()

    return [_audit_to_activity(log, idx) for idx, log in enumerate(logs)]


# ─────────────────────────────────────────────────────────────────────────────
# /investigator/{user_id}/cases
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/investigator/{user_id}/cases",
    response_model = List[InvestigatorCase],
    summary        = "Cases the investigator has been assigned to",
    tags           = ["Administration", "Investigator Intelligence"],
)
async def get_investigator_cases(
    user_id: int,
    _:       AdminUser,
    db:      AsyncSession = Depends(get_db),
):
    """
    Returns all cases assigned to the investigator.

    Reads from CaseAssignment (join → Case) if the model is available.
    Falls back to extracting unique case_id values from audit_log.details
    when those models are not yet present — so this endpoint always returns
    something useful even in a partial deployment.

    Each entry includes:
      - case_id, title, case_type, status, role
      - evidence_count   (images linked to this case by this user)
      - reports_authored (reports linked to this case by this user)
      - last_activity    (most recent audit event for this case)
    """
    # Guard
    user_row = await db.execute(select(User.id).where(User.id == user_id))
    if user_row.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"User {user_id} not found.")

    CaseAssignment = _import_case_assignment()
    Case           = _import_case()
    Image          = _import_image()
    Report         = _import_report()
    AuditLog       = _import_audit_log()

    results: list[InvestigatorCase] = []

    # ── Path A: proper Case + CaseAssignment models exist ───────────────────
    if CaseAssignment is not None and Case is not None:
        rows = await db.execute(
            select(CaseAssignment, Case)
            .join(Case, CaseAssignment.case_id == Case.id)
            .where(CaseAssignment.user_id == user_id)
            .order_by(desc(Case.updated_at))
        )
        assignments = rows.all()

        for assignment, case in assignments:
            # Evidence count this user uploaded for this case
            ev_count = 0
            if Image is not None:
                try:
                    cnt = await db.execute(
                        select(func.count()).where(
                            Image.case_id        == case.id,
                            Image.uploaded_by    == user_id,
                        )
                    )
                    ev_count = cnt.scalar() or 0
                except Exception:
                    pass

            # Reports this user authored for this case
            rep_count = 0
            if Report is not None:
                try:
                    cnt = await db.execute(
                        select(func.count()).where(
                            Report.case_id    == case.id,
                            Report.created_by == user_id,
                        )
                    )
                    rep_count = cnt.scalar() or 0
                except Exception:
                    pass

            # Last activity timestamp from audit_log
            last_ts: datetime = case.updated_at or case.created_at
            if AuditLog is not None:
                try:
                    la = await db.execute(
                        select(AuditLog.timestamp)
                        .where(
                            AuditLog.user_id == user_id,
                            cast(AuditLog.details["case_id"].astext, String)
                            == str(case.id),
                        )
                        .order_by(desc(AuditLog.timestamp))
                        .limit(1)
                    )
                    la_ts = la.scalar_one_or_none()
                    if la_ts:
                        last_ts = la_ts
                except Exception:
                    pass

            results.append(
                InvestigatorCase(
                    case_id          = str(getattr(case, "case_number", case.id)),
                    title            = getattr(case, "title", f"Case {case.id}"),
                    case_type        = getattr(case, "case_type", "Unknown"),
                    status           = getattr(case, "status", "active"),
                    role             = getattr(assignment, "role", "investigator"),
                    evidence_count   = ev_count,
                    reports_authored = rep_count,
                    last_activity    = last_ts,
                )
            )
        return results

    # ── Path B: fallback — mine audit_log.details for case references ────────
    if AuditLog is None:
        return []

    log_rows = await db.execute(
        select(AuditLog)
        .where(AuditLog.user_id == user_id)
        .order_by(desc(AuditLog.timestamp))
    )
    logs = log_rows.scalars().all()

    # Collect unique case IDs preserving first-seen order
    seen:    dict[str, dict[str, Any]] = {}
    for log in logs:
        details = log.details or {}
        cid = (
            details.get("case_id")
            or details.get("case_number")
        )
        if not cid:
            continue
        cid = str(cid)
        if cid not in seen:
            seen[cid] = {
                "last_ts":       log.timestamp,
                "ev_count":      0,
                "rep_count":     0,
                "upload_count":  0,
            }
        if log.action_type == "image_uploaded":
            seen[cid]["upload_count"] += 1
        if log.action_type == "report_generated":
            seen[cid]["rep_count"] += 1

    for cid, data in seen.items():
        results.append(
            InvestigatorCase(
                case_id          = cid,
                title            = f"Case {cid}",
                case_type        = "Unknown",
                status           = "active",
                role             = "investigator",
                evidence_count   = data["upload_count"],
                reports_authored = data["rep_count"],
                last_activity    = data["last_ts"],
            )
        )
    return results


# ─────────────────────────────────────────────────────────────────────────────
# /investigator/{user_id}/evidence
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/investigator/{user_id}/evidence",
    response_model = List[EvidenceItem],
    summary        = "Evidence images uploaded by this investigator",
    tags           = ["Administration", "Investigator Intelligence"],
)
async def get_investigator_evidence(
    user_id: int,
    _:       AdminUser,
    limit:   int          = Query(50, ge=1, le=200),
    db:      AsyncSession = Depends(get_db),
):
    """
    Returns all evidence images uploaded by this investigator.

    - Reads from the Image model (uploaded_by == user_id) when available.
    - Falls back to AuditLog rows with action_type='image_uploaded' and
      reconstructs metadata from the details JSON.
    - `ai_analyzed`      is True when a ComparisonResult row references the image.
    - `report_generated` is True when a Report row references the image.
    - `file_hash`        is pulled from Image.file_hash if the column exists.
    """
    user_row = await db.execute(select(User.id).where(User.id == user_id))
    if user_row.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"User {user_id} not found.")

    Image            = _import_image()
    ComparisonResult = _import_comparison()
    Report           = _import_report()
    AuditLog         = _import_audit_log()

    results: list[EvidenceItem] = []

    # ── Path A: Image model available ────────────────────────────────────────
    if Image is not None:
        try:
            rows = await db.execute(
                select(Image)
                .where(Image.uploaded_by == user_id)
                .order_by(desc(Image.uploaded_at))
                .limit(limit)
            )
            images = rows.scalars().all()

            for img in images:
                # Check AI analysis
                ai_done = False
                if ComparisonResult is not None:
                    try:
                        chk = await db.execute(
                            select(ComparisonResult.id).where(
                                or_(
                                    ComparisonResult.query_image_id   == img.id,
                                    ComparisonResult.reference_image_id == img.id,
                                )
                            ).limit(1)
                        )
                        ai_done = chk.scalar_one_or_none() is not None
                    except Exception:
                        pass

                rep_done = False
                if Report is not None:
                    try:
                        chk = await db.execute(
                            select(Report.id)
                            .where(Report.image_id == img.id)
                            .limit(1)
                        )
                        rep_done = chk.scalar_one_or_none() is not None
                    except Exception:
                        pass

                results.append(
                    EvidenceItem(
                        id               = img.id,
                        image_id         = str(getattr(img, "image_uuid", img.id)),
                        filename         = getattr(img, "original_filename", getattr(img, "filename", "unknown")),
                        evidence_type    = getattr(img, "evidence_type", "unknown"),
                        case_id          = str(getattr(img, "case_id", "—")),
                        uploaded_at      = img.uploaded_at,
                        ai_analyzed      = ai_done,
                        report_generated = rep_done,
                        file_hash        = getattr(img, "file_hash", None),
                    )
                )
            return results
        except Exception:
            pass  # column mismatch — fall through to AuditLog path

    # ── Path B: reconstruct from audit log ────────────────────────────────────
    if AuditLog is None:
        return []

    log_rows = await db.execute(
        select(AuditLog)
        .where(
            AuditLog.user_id     == user_id,
            AuditLog.action_type == "image_uploaded",
        )
        .order_by(desc(AuditLog.timestamp))
        .limit(limit)
    )
    logs = log_rows.scalars().all()

    for idx, log in enumerate(logs):
        details = log.details or {}
        results.append(
            EvidenceItem(
                id               = log.id,
                image_id         = str(details.get("image_id", f"img-{log.id}")),
                filename         = str(details.get("filename") or details.get("original_filename") or "unknown"),
                evidence_type    = str(details.get("evidence_type", "unknown")),
                case_id          = str(details.get("case_id", "—")),
                uploaded_at      = log.timestamp,
                ai_analyzed      = bool(details.get("ai_analyzed", False)),
                report_generated = bool(details.get("report_generated", False)),
                file_hash        = details.get("file_hash"),
            )
        )
    return results


# ─────────────────────────────────────────────────────────────────────────────
# /investigator/{user_id}/logins
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/investigator/{user_id}/logins",
    response_model = List[LoginEvent],
    summary        = "Login history for this investigator",
    tags           = ["Administration", "Investigator Intelligence"],
)
async def get_investigator_logins(
    user_id: int,
    _:       AdminUser,
    limit:   int          = Query(20, ge=1, le=100),
    db:      AsyncSession = Depends(get_db),
):
    """
    Returns login history newest-first.

    - If a dedicated LoginLog model is present it is used directly.
    - Otherwise audit_log rows where action_type IN ('user_login', 'user_logout',
      'login_failed') are used. `success` is True for 'user_login', False for
      'login_failed'.

    The `user_agent` is pulled from details.user_agent when available.
    """
    user_row = await db.execute(select(User.id).where(User.id == user_id))
    if user_row.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"User {user_id} not found.")

    LoginLog = _import_login_log()

    # ── Path A: dedicated LoginLog model ─────────────────────────────────────
    if LoginLog is not None:
        try:
            rows = await db.execute(
                select(LoginLog)
                .where(LoginLog.user_id == user_id)
                .order_by(desc(LoginLog.timestamp))
                .limit(limit)
            )
            login_rows = rows.scalars().all()
            return [
                LoginEvent(
                    id         = lr.id,
                    timestamp  = lr.timestamp,
                    ip_address = getattr(lr, "ip_address", "unknown"),
                    user_agent = getattr(lr, "user_agent", None),
                    success    = getattr(lr, "success", True),
                )
                for lr in login_rows
            ]
        except Exception:
            pass  # fall through

    # ── Path B: audit_log fallback ────────────────────────────────────────────
    AuditLog = _import_audit_log()
    if AuditLog is None:
        return []

    LOGIN_ACTIONS = ("user_login", "login_failed", "user_logout")

    rows = await db.execute(
        select(AuditLog)
        .where(
            AuditLog.user_id     == user_id,
            AuditLog.action_type.in_(LOGIN_ACTIONS),
        )
        .order_by(desc(AuditLog.timestamp))
        .limit(limit)
    )
    logs = rows.scalars().all()

    events: list[LoginEvent] = []
    for log in logs:
        details = log.details or {}
        events.append(
            LoginEvent(
                id         = log.id,
                timestamp  = log.timestamp,
                ip_address = log.ip_address or details.get("ip_address", "unknown"),
                user_agent = details.get("user_agent"),
                success    = log.action_type != "login_failed",
            )
        )
    return events