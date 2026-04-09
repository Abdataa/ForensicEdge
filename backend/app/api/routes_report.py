"""
backend/app/api/routes_reports.py
-----------------------------------
Endpoints for forensic PDF report generation and retrieval.

Depends on:
    - app.services.report_service (generate_report, get_report, list_reports, get_pdf_path)
    - app.schemas.report_schema (ReportCreate, ReportResponse, ReportListResponse)
"""

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.report_schema import (
    ReportCreate,
    ReportResponse,
    ReportListResponse,
)
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post(
    "",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a forensic PDF report",
)
async def generate_report(
    request: Request,
    payload: ReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a professional PDF report summarizing a similarity result.

    The report includes:
    - Case metadata and analyst information
    - Side-by-side evidence images
    - Similarity metrics and match status
    - Analyst notes (optional)

    The PDF is saved on the server and can be downloaded via the `/download` endpoint.
    """
    return await report_service.generate_report(
        payload=payload,
        user=current_user,
        db=db,
        ip_address=request.client.host if request.client else None,
    )


@router.get(
    "",
    response_model=ReportListResponse,
    summary="List generated reports",
)
async def list_reports(
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve a paginated list of reports you have generated."""
    return await report_service.list_reports(
        user=current_user,
        db=db,
        page=page,
        limit=limit,
    )


@router.get(
    "/{report_id}",
    response_model=ReportResponse,
    summary="Get report metadata",
)
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve metadata for a specific report."""
    return await report_service.get_report(report_id, current_user, db)


@router.get(
    "/{report_id}/download",
    summary="Download PDF report",
    response_class=FileResponse,
)
async def download_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Download the generated PDF report.

    The response will have Content-Type: application/pdf and
    Content-Disposition: attachment; filename="report_xxx.pdf"
    """
    pdf_path = await report_service.get_pdf_path(report_id, current_user, db)
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=pdf_path.name,
    )