"""
backend/app/api/routes_cases.py
---------------------------------
Case Management API — all endpoints for creating, managing,
and linking forensic evidence cases.

Endpoints
---------
    POST   /api/v1/cases                          create case
    GET    /api/v1/cases                          list cases (with filters)
    GET    /api/v1/cases/{id}                     get full case detail
    PUT    /api/v1/cases/{id}                     update case
    DELETE /api/v1/cases/{id}                     delete case (admin only)

    POST   /api/v1/cases/{id}/evidence            link evidence image
    GET    /api/v1/cases/{id}/evidence            list linked evidence

    POST   /api/v1/cases/{id}/analyses            link similarity result
    GET    /api/v1/cases/{id}/analyses            list linked analyses

    POST   /api/v1/cases/{id}/reports             link report
    GET    /api/v1/cases/{id}/reports             list linked reports

    POST   /api/v1/cases/{id}/notes               add a note
    GET    /api/v1/cases/{id}/notes               list notes

    POST   /api/v1/cases/{id}/analyze             run analysis inside case
                                                  (links two images + stores result)
"""

from typing import Optional

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database     import get_db
from app.core.dependencies import get_current_active_user
from app.models.user       import User
from app.schemas.case_schema import (
    CaseCreate, CaseUpdate,
    CaseResponse, CaseListResponse, CaseDetailResponse,
    CaseEvidenceResponse, CaseAnalysisResponse,
    CaseReportResponse, CaseNoteResponse, CaseNoteCreate,
    LinkEvidenceRequest, LinkAnalysisRequest, LinkReportRequest,
)
from app.services import case_service

router = APIRouter(prefix="/cases", tags=["Case Management"])


# ---------------------------------------------------------------------------
# Case CRUD
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model = CaseResponse,
    status_code    = status.HTTP_201_CREATED,
    summary        = "Create a new investigation case",
)
async def create_case(
    payload:      CaseCreate,
    request:      Request,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_active_user),
):
    """
    Create a new case.
    The authenticated user becomes the case creator (created_by).
    An investigator can optionally be assigned at creation.
    """
    return await case_service.create_case(
        payload    = payload,
        user       = current_user,
        db         = db,
        ip_address = request.client.host if request.client else None,
    )


@router.get(
    "",
    response_model = CaseListResponse,
    summary        = "List cases",
)
async def list_cases(
    status_filter: Optional[str] = None,
    priority:      Optional[str] = None,
    page:          int           = 1,
    limit:         int           = 20,
    db:            AsyncSession  = Depends(get_db),
    current_user:  User          = Depends(get_current_active_user),
):
    """
    List cases.
    - Admins see all cases.
    - Analysts see only cases they created or are assigned to.
    Filter by status (OPEN, IN_PROGRESS, REVIEW, CLOSED) or priority (LOW, MEDIUM, HIGH).
    """
    return await case_service.list_cases(
        user     = current_user,
        db       = db,
        status_f = status_filter,
        priority = priority,
        page     = page,
        limit    = limit,
    )


@router.get(
    "/{case_id}",
    response_model = CaseDetailResponse,
    summary        = "Get full case detail",
)
async def get_case(
    case_id:      int,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_active_user),
):
    """
    Return full case details including all linked evidence,
    analyses, reports, and notes.
    """
    return await case_service.get_case(
        case_id = case_id,
        user    = current_user,
        db      = db,
    )


@router.put(
    "/{case_id}",
    response_model = CaseResponse,
    summary        = "Update case details",
)
async def update_case(
    case_id:      int,
    payload:      CaseUpdate,
    request:      Request,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_active_user),
):
    """
    Update case title, description, status, priority, or assigned investigator.
    Only the creator, assigned investigator, or admin can update.
    """
    return await case_service.update_case(
        case_id    = case_id,
        payload    = payload,
        user       = current_user,
        db         = db,
        ip_address = request.client.host if request.client else None,
    )


@router.delete(
    "/{case_id}",
    status_code = status.HTTP_204_NO_CONTENT,
    summary     = "Delete a case (admin only)",
)
async def delete_case(
    case_id:      int,
    request:      Request,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_active_user),
):
    """
    Permanently delete a case and all its links.
    Admin only. Linked images, results, and reports are NOT deleted —
    only the case linkage records are removed (cascade on case tables).
    """
    await case_service.delete_case(
        case_id    = case_id,
        user       = current_user,
        db         = db,
        ip_address = request.client.host if request.client else None,
    )


# ---------------------------------------------------------------------------
# Evidence linking
# ---------------------------------------------------------------------------

@router.post(
    "/{case_id}/evidence",
    response_model = CaseEvidenceResponse,
    status_code    = status.HTTP_201_CREATED,
    summary        = "Link an evidence image to this case",
)
async def link_evidence(
    case_id:      int,
    payload:      LinkEvidenceRequest,
    request:      Request,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_active_user),
):
    """
    Attach an uploaded ForensicImage to this case.
    The same image can be linked to multiple cases.
    Linking the same image twice to the same case returns HTTP 409.
    """
    return await case_service.link_evidence(
        case_id    = case_id,
        payload    = payload,
        user       = current_user,
        db         = db,
        ip_address = request.client.host if request.client else None,
    )


@router.get(
    "/{case_id}/evidence",
    response_model = list[CaseEvidenceResponse],
    summary        = "List evidence linked to this case",
)
async def list_case_evidence(
    case_id:      int,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_active_user),
):
    return await case_service.list_case_evidence(
        case_id = case_id,
        user    = current_user,
        db      = db,
    )


# ---------------------------------------------------------------------------
# Analysis linking
# ---------------------------------------------------------------------------

@router.post(
    "/{case_id}/analyses",
    response_model = CaseAnalysisResponse,
    status_code    = status.HTTP_201_CREATED,
    summary        = "Link a similarity result to this case",
)
async def link_analysis(
    case_id:      int,
    payload:      LinkAnalysisRequest,
    request:      Request,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_active_user),
):
    """
    Attach an existing SimilarityResult to this case.
    Run the comparison first via POST /compare, then link it here.
    """
    return await case_service.link_analysis(
        case_id    = case_id,
        payload    = payload,
        user       = current_user,
        db         = db,
        ip_address = request.client.host if request.client else None,
    )


@router.get(
    "/{case_id}/analyses",
    response_model = list[CaseAnalysisResponse],
    summary        = "List analyses linked to this case",
)
async def list_case_analyses(
    case_id:      int,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_active_user),
):
    case = await case_service._load_case(case_id, db)
    case_service._check_access(case, current_user)
    from sqlalchemy import select
    from app.models.case import CaseAnalysis
    rows = await db.execute(
        select(CaseAnalysis).where(CaseAnalysis.case_id == case_id)
        .order_by(CaseAnalysis.added_at.desc())
    )
    return [CaseAnalysisResponse.model_validate(r) for r in rows.scalars().all()]


# ---------------------------------------------------------------------------
# Report linking
# ---------------------------------------------------------------------------

@router.post(
    "/{case_id}/reports",
    response_model = CaseReportResponse,
    status_code    = status.HTTP_201_CREATED,
    summary        = "Link a report to this case",
)
async def link_report(
    case_id:      int,
    payload:      LinkReportRequest,
    request:      Request,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_active_user),
):
    return await case_service.link_report(
        case_id    = case_id,
        payload    = payload,
        user       = current_user,
        db         = db,
        ip_address = request.client.host if request.client else None,
    )


@router.get(
    "/{case_id}/reports",
    response_model = list[CaseReportResponse],
    summary        = "List reports linked to this case",
)
async def list_case_reports(
    case_id:      int,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_active_user),
):
    case = await case_service._load_case(case_id, db)
    case_service._check_access(case, current_user)
    from sqlalchemy import select
    from app.models.case import CaseReport
    rows = await db.execute(
        select(CaseReport).where(CaseReport.case_id == case_id)
        .order_by(CaseReport.added_at.desc())
    )
    return [CaseReportResponse.model_validate(r) for r in rows.scalars().all()]


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------

@router.post(
    "/{case_id}/notes",
    response_model = CaseNoteResponse,
    status_code    = status.HTTP_201_CREATED,
    summary        = "Add a note to this case",
)
async def add_note(
    case_id:      int,
    payload:      CaseNoteCreate,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_active_user),
):
    """
    Post a free-text investigator note inside a case.
    Notes are ordered by creation time — they form the case timeline.
    """
    return await case_service.add_note(
        case_id = case_id,
        payload = payload,
        user    = current_user,
        db      = db,
    )


@router.get(
    "/{case_id}/notes",
    response_model = list[CaseNoteResponse],
    summary        = "List notes for this case",
)
async def list_notes(
    case_id:      int,
    db:           AsyncSession = Depends(get_db),
    current_user: User         = Depends(get_current_active_user),
):
    return await case_service.list_notes(
        case_id = case_id,
        user    = current_user,
        db      = db,
    )
