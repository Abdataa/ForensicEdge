"""
backend/app/services/case_service.py
--------------------------------------
Business logic for the Case Management Subsystem.

Cases are the central coordinator of all forensic work.
All evidence, analyses, and reports are linked TO a case.
"""

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case, CaseEvidence, CaseAnalysis, CaseReport, CaseNote
from app.models.forensic_image    import ForensicImage
from app.models.similarity_result import SimilarityResult
from app.models.report            import Report
from app.models.user              import User
from app.schemas.case_schema import (
    CaseCreate, CaseUpdate,
    CaseResponse, CaseListResponse, CaseDetailResponse,
    CaseEvidenceResponse, CaseAnalysisResponse,
    CaseReportResponse, CaseNoteResponse,
    LinkEvidenceRequest, LinkAnalysisRequest,
    LinkReportRequest, CaseNoteCreate,
)
from app.services.log_service import create_log


# ── Load options for full detail queries ──────────────────────────────────────
_CASE_DETAIL_OPTIONS = [
    selectinload(Case.evidence),
    selectinload(Case.analyses),
    selectinload(Case.reports),
    selectinload(Case.notes),
]


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

async def create_case(
    payload:    CaseCreate,
    user:       User,
    db:         AsyncSession,
    ip_address: Optional[str] = None,
) -> CaseResponse:
    case = Case(
        title       = payload.title,
        description = payload.description,
        created_by  = user.id,
        assigned_to = payload.assigned_to,
        status      = payload.status.value,
        priority    = payload.priority.value,
    )
    db.add(case)
    await db.commit()
    await db.refresh(case)

    await create_log(
        db=db, action_type="case_created", user_id=user.id,
        details={"case_id": case.id, "title": case.title},
        ip_address=ip_address,
    )
    return _to_response(case)


async def get_case(
    case_id: int,
    user:    User,
    db:      AsyncSession,
) -> CaseDetailResponse:
    """Return full case detail including all linked items."""
    row = await db.execute(
        select(Case)
        .options(*_CASE_DETAIL_OPTIONS)
        .where(Case.id == case_id)
    )
    case = row.scalar_one_or_none()
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Case {case_id} not found.")
    _check_access(case, user)
    return _to_detail_response(case)


async def list_cases(
    user:     User,
    db:       AsyncSession,
    status_f: Optional[str] = None,
    priority: Optional[str] = None,
    page:     int           = 1,
    limit:    int           = 20,
) -> CaseListResponse:
    limit = min(limit, 100)
    query = select(Case).order_by(desc(Case.created_at))

    # Analysts see only cases they created or are assigned to
    if user.role not in ("admin",):
        from sqlalchemy import or_
        query = query.where(
            or_(Case.created_by == user.id, Case.assigned_to == user.id)
        )
    if status_f:
        query = query.where(Case.status == status_f)
    if priority:
        query = query.where(Case.priority == priority)

    count_result = await db.execute(query.with_only_columns(Case.id))
    total        = len(count_result.all())

    rows  = await db.execute(query.offset((page - 1) * limit).limit(limit))
    cases = rows.scalars().all()

    return CaseListResponse(
        total=total, page=page, limit=limit,
        cases=[_to_response(c) for c in cases],
    )


async def update_case(
    case_id:    int,
    payload:    CaseUpdate,
    user:       User,
    db:         AsyncSession,
    ip_address: Optional[str] = None,
) -> CaseResponse:
    case = await _load_case(case_id, db)
    _check_access(case, user)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(value, "value"):   # enum → string
            value = value.value
        setattr(case, field, value)

    await db.commit()
    await db.refresh(case)

    await create_log(
        db=db, action_type="case_updated", user_id=user.id,
        details={"case_id": case_id, "fields": list(update_data.keys())},
        ip_address=ip_address,
    )
    return _to_response(case)


async def delete_case(
    case_id:    int,
    user:       User,
    db:         AsyncSession,
    ip_address: Optional[str] = None,
) -> None:
    case = await _load_case(case_id, db)
    _check_access(case, user, admin_only=True)

    await db.delete(case)
    await db.commit()

    await create_log(
        db=db, action_type="case_deleted", user_id=user.id,
        details={"case_id": case_id, "title": case.title},
        ip_address=ip_address,
    )


# ---------------------------------------------------------------------------
# Evidence linking
# ---------------------------------------------------------------------------

async def link_evidence(
    case_id:    int,
    payload:    LinkEvidenceRequest,
    user:       User,
    db:         AsyncSession,
    ip_address: Optional[str] = None,
) -> CaseEvidenceResponse:
    case = await _load_case(case_id, db)
    _check_access(case, user)

    # Verify the image exists and belongs to user
    img_row = await db.execute(
        select(ForensicImage).where(ForensicImage.id == payload.image_id)
    )
    image = img_row.scalar_one_or_none()
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Image {payload.image_id} not found.")

    # Check not already linked
    existing = await db.execute(
        select(CaseEvidence)
        .where(CaseEvidence.case_id == case_id)
        .where(CaseEvidence.image_id == payload.image_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="This image is already linked to the case.")

    link = CaseEvidence(
        case_id=case_id, image_id=payload.image_id,
        linked_by=user.id, notes=payload.notes,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)

    await create_log(
        db=db, action_type="case_evidence_linked", user_id=user.id,
        details={"case_id": case_id, "image_id": payload.image_id},
        ip_address=ip_address,
    )
    return CaseEvidenceResponse.model_validate(link)


async def list_case_evidence(
    case_id: int, user: User, db: AsyncSession,
) -> list[CaseEvidenceResponse]:
    case = await _load_case(case_id, db)
    _check_access(case, user)
    rows = await db.execute(
        select(CaseEvidence).where(CaseEvidence.case_id == case_id)
        .order_by(CaseEvidence.linked_at.desc())
    )
    return [CaseEvidenceResponse.model_validate(r) for r in rows.scalars().all()]


# ---------------------------------------------------------------------------
# Analysis linking
# ---------------------------------------------------------------------------

async def link_analysis(
    case_id:    int,
    payload:    LinkAnalysisRequest,
    user:       User,
    db:         AsyncSession,
    ip_address: Optional[str] = None,
) -> CaseAnalysisResponse:
    case = await _load_case(case_id, db)
    _check_access(case, user)

    res_row = await db.execute(
        select(SimilarityResult).where(SimilarityResult.id == payload.result_id)
    )
    if res_row.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Result {payload.result_id} not found.")

    existing = await db.execute(
        select(CaseAnalysis)
        .where(CaseAnalysis.case_id == case_id)
        .where(CaseAnalysis.result_id == payload.result_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="This analysis is already linked to the case.")

    link = CaseAnalysis(case_id=case_id, result_id=payload.result_id)
    db.add(link)
    await db.commit()
    await db.refresh(link)

    await create_log(
        db=db, action_type="case_analysis_linked", user_id=user.id,
        details={"case_id": case_id, "result_id": payload.result_id},
        ip_address=ip_address,
    )
    return CaseAnalysisResponse.model_validate(link)


# ---------------------------------------------------------------------------
# Report linking
# ---------------------------------------------------------------------------

async def link_report(
    case_id:    int,
    payload:    LinkReportRequest,
    user:       User,
    db:         AsyncSession,
    ip_address: Optional[str] = None,
) -> CaseReportResponse:
    case = await _load_case(case_id, db)
    _check_access(case, user)

    rep_row = await db.execute(
        select(Report).where(Report.id == payload.report_id)
    )
    if rep_row.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Report {payload.report_id} not found.")

    existing = await db.execute(
        select(CaseReport)
        .where(CaseReport.case_id == case_id)
        .where(CaseReport.report_id == payload.report_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="This report is already linked to the case.")

    link = CaseReport(case_id=case_id, report_id=payload.report_id)
    db.add(link)
    await db.commit()
    await db.refresh(link)

    return CaseReportResponse.model_validate(link)


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------

async def add_note(
    case_id: int,
    payload: CaseNoteCreate,
    user:    User,
    db:      AsyncSession,
) -> CaseNoteResponse:
    case = await _load_case(case_id, db)
    _check_access(case, user)

    note = CaseNote(
        case_id=case_id, user_id=user.id,
        note_text=payload.note_text,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return CaseNoteResponse.model_validate(note)


async def list_notes(
    case_id: int, user: User, db: AsyncSession,
) -> list[CaseNoteResponse]:
    case = await _load_case(case_id, db)
    _check_access(case, user)
    rows = await db.execute(
        select(CaseNote).where(CaseNote.case_id == case_id)
        .order_by(CaseNote.created_at)
    )
    return [CaseNoteResponse.model_validate(n) for n in rows.scalars().all()]


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

async def _load_case(case_id: int, db: AsyncSession) -> Case:
    row = await db.execute(select(Case).where(Case.id == case_id))
    case = row.scalar_one_or_none()
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Case {case_id} not found.")
    return case


def _check_access(case: Case, user: User, admin_only: bool = False) -> None:
    """Verify user can access this case."""
    if user.role == "admin":
        return
    if admin_only:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Admin only.")
    if case.created_by != user.id and case.assigned_to != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied to this case.")


def _to_response(case: Case) -> CaseResponse:
    return CaseResponse(
        id=case.id, title=case.title, description=case.description,
        created_by=case.created_by, assigned_to=case.assigned_to,
        status=case.status, priority=case.priority,
        created_at=case.created_at, updated_at=case.updated_at,
    )


def _to_detail_response(case: Case) -> CaseDetailResponse:
    return CaseDetailResponse(
        id=case.id, title=case.title, description=case.description,
        created_by=case.created_by, assigned_to=case.assigned_to,
        status=case.status, priority=case.priority,
        created_at=case.created_at, updated_at=case.updated_at,
        evidence_count=len(case.evidence),
        analyses_count=len(case.analyses),
        reports_count=len(case.reports),
        notes_count=len(case.notes),
        evidence =[CaseEvidenceResponse.model_validate(e) for e in case.evidence],
        analyses =[CaseAnalysisResponse.model_validate(a) for a in case.analyses],
        reports  =[CaseReportResponse.model_validate(r)   for r in case.reports],
        notes    =[CaseNoteResponse.model_validate(n)     for n in case.notes],
    )