"""
backend/app/services/report_service.py
----------------------------------------
Business logic for forensic PDF report generation and retrieval.

From project report scenario 4:
    "System compiles similarity score, analysis summary, enhanced images,
     and feature visualizations into a formatted PDF. Investigator receives
     a clear, professional report ready for documentation or courtroom use."

PDF generation uses fpdf2 (pip install fpdf2).

Report contents
---------------
    Header      : ForensicEdge title, case metadata, analyst name
    Section 1   : Evidence images (original + enhanced side by side)
    Section 2   : Similarity analysis results (score, status, all metrics)
    Section 3   : Evidence type (fingerprint | toolmark)
    Section 4   : Analyst notes (if provided)
    Footer      : Timestamp, disclaimer, report ID
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config              import settings
from app.models.report            import Report
from app.models.similarity_result import SimilarityResult
from app.models.forensic_image    import ForensicImage
from app.models.user              import User
from app.schemas.report_schema    import ReportCreate, ReportResponse, ReportListResponse
from app.services.log_service     import create_log
from app.utils.logger             import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
async def generate_report(
    payload:    ReportCreate,
    user:       User,
    db:         AsyncSession,
    ip_address: Optional[str] = None,
) -> ReportResponse:
    """
    Generate a forensic PDF report from a SimilarityResult.

    Raises:
        HTTP 404 — SimilarityResult not found
        HTTP 403 — result belongs to another user (non-admin)
        HTTP 409 — report already exists for this result
        HTTP 500 — PDF generation failure
    """
    row = await db.execute(
        select(SimilarityResult).where(SimilarityResult.id == payload.result_id)
    )
    result = row.scalar_one_or_none()

    if result is None:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = f"Similarity result {payload.result_id} not found.",
        )
    if result.requested_by != user.id and user.role != "admin":
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail      = "Access denied.",
        )

    existing = await db.execute(
        select(Report).where(Report.result_id == payload.result_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code = status.HTTP_409_CONFLICT,
            detail      = (
                f"A report already exists for result {payload.result_id}. "
                f"Use GET /reports to retrieve it."
            ),
        )

    img1_row = await db.execute(
        select(ForensicImage).where(ForensicImage.id == result.image_id_1)
    )
    img2_row = await db.execute(
        select(ForensicImage).where(ForensicImage.id == result.image_id_2)
    )
    image_1 = img1_row.scalar_one_or_none()
    image_2 = img2_row.scalar_one_or_none()

    pdf_path = await _generate_pdf(
        result  = result,
        image_1 = image_1,
        image_2 = image_2,
        analyst = user,
        title   = payload.title,
        notes   = payload.notes,
    )

    report = Report(
        user_id   = user.id,
        result_id = result.id,
        title     = payload.title,
        pdf_path  = str(pdf_path),
        notes     = payload.notes,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    await create_log(
        db          = db,
        action_type = "report_generated",
        user_id     = user.id,
        details     = {
            "report_id":     report.id,
            "result_id":     result.id,
            "evidence_type": image_1.evidence_type if image_1 else "unknown",
        },
        ip_address  = ip_address,
    )

    logger.info(
        "Report generated",
        extra={
            "report_id": report.id,
            "pdf_path":  str(pdf_path),
            "user_id":   user.id,
        },
    )

    return ReportResponse.model_validate(report)


# ---------------------------------------------------------------------------
async def get_report(
    report_id: int,
    user:      User,
    db:        AsyncSession,
) -> ReportResponse:
    row = await db.execute(select(Report).where(Report.id == report_id))
    report = row.scalar_one_or_none()

    if report is None:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = f"Report {report_id} not found.",
        )
    if report.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail      = "Access denied.",
        )
    return ReportResponse.model_validate(report)


# ---------------------------------------------------------------------------
async def list_reports(
    user:  User,
    db:    AsyncSession,
    page:  int = 1,
    limit: int = 20,
) -> ReportListResponse:
    limit = min(limit, 100)
    query = select(Report).order_by(desc(Report.created_at))

    if user.role != "admin":
        query = query.where(Report.user_id == user.id)

    count_result = await db.execute(query.with_only_columns(Report.id))
    total        = len(count_result.all())

    offset  = (page - 1) * limit
    rows    = await db.execute(query.offset(offset).limit(limit))
    reports = rows.scalars().all()

    return ReportListResponse(
        total   = total, page = page, limit = limit,
        reports = [ReportResponse.model_validate(r) for r in reports],
    )


# ---------------------------------------------------------------------------
async def get_pdf_path(
    report_id: int,
    user:      User,
    db:        AsyncSession,
) -> Path:
    report_resp = await get_report(report_id, user, db)
    pdf_path    = Path(report_resp.pdf_path)

    if not pdf_path.exists():
        logger.error(
            "PDF file missing on disk",
            extra={"report_id": report_id, "path": str(pdf_path)},
        )
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = (
                f"PDF file for report {report_id} not found on disk. "
                f"The report may have been deleted or moved."
            ),
        )
    return pdf_path


# ---------------------------------------------------------------------------
# PDF generation
# ---------------------------------------------------------------------------

async def _generate_pdf(
    result:  SimilarityResult,
    image_1: Optional[ForensicImage],
    image_2: Optional[ForensicImage],
    analyst: User,
    title:   str,
    notes:   Optional[str],
) -> Path:
    """Build the forensic PDF report using fpdf2."""
    try:
        from fpdf import FPDF
    except ImportError:
        logger.error("fpdf2 not installed — cannot generate PDF")
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail      = "PDF library not installed. Run: pip install fpdf2",
        )

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    evidence_type = image_1.evidence_type if image_1 else "unknown"

    # Header
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "ForensicEdge", ln=True, align="C")
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, title, ln=True, align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(
        0, 6,
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  |  "
        f"Report ID: {uuid.uuid4().hex[:8].upper()}  |  "
        f"Analyst: {analyst.full_name}",
        ln=True, align="C",
    )
    pdf.ln(4)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)

    # Evidence information
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Evidence Information", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Evidence Type : {evidence_type.title()}", ln=True)
    if image_1:
        pdf.cell(0, 6, f"Query Image   : {image_1.original_filename}", ln=True)
    if image_2:
        pdf.cell(0, 6, f"Reference Image: {image_2.original_filename}", ln=True)
    pdf.ln(4)

    _add_images_to_pdf(pdf, image_1, image_2)
    pdf.ln(4)

    # Similarity results
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Similarity Analysis Results", ln=True)
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 28)
    pdf.cell(0, 14, f"{result.similarity_percentage:.1f}%", ln=True, align="C")

    pdf.set_font("Helvetica", "B", 14)
    status_colors = {
        "MATCH":          (0,   128, 0),
        "POSSIBLE MATCH": (200, 140, 0),
        "NO MATCH":       (180,   0, 0),
    }
    r, g, b = status_colors.get(result.match_status, (0, 0, 0))
    pdf.set_text_color(r, g, b)
    pdf.cell(0, 8, result.match_status, ln=True, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(95, 7, "Metric", border=1)
    pdf.cell(95, 7, "Value", border=1, ln=True)
    pdf.set_font("Helvetica", "", 10)

    for label, value in [
        ("Similarity Percentage",  f"{result.similarity_percentage:.2f}%"),
        ("Cosine Similarity",       f"{result.cosine_similarity:.4f}"),
        ("Euclidean Distance",      f"{result.euclidean_distance:.4f}"),
        ("Match Status",            result.match_status),
        ("Evidence Type",           evidence_type.title()),
        ("Comparison Date",         result.created_at.strftime("%Y-%m-%d %H:%M UTC")),
    ]:
        pdf.cell(95, 6, label, border=1)
        pdf.cell(95, 6, value, border=1, ln=True)
    pdf.ln(6)

    if notes:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Analyst Notes", ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, notes)
        pdf.ln(4)

    # Disclaimer
    pdf.ln(6)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(
        0, 5,
        "DISCLAIMER: This report is generated by the ForensicEdge AI-assisted "
        "analysis system and is intended to SUPPORT, not replace, the judgment "
        "of qualified forensic examiners. All results must be verified by a "
        "certified forensic professional before use in legal proceedings.",
    )

    # Save PDF
    reports_dir = Path(settings.REPORTS_DIR)
    reports_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = reports_dir / f"report_{uuid.uuid4().hex[:12]}.pdf"
    pdf.output(str(pdf_path))

    logger.info("PDF saved", extra={"path": str(pdf_path)})
    return pdf_path


def _add_images_to_pdf(
    pdf:     "FPDF",
    image_1: Optional[ForensicImage],
    image_2: Optional[ForensicImage],
) -> None:
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Evidence Images", ln=True)

    img_width = 85
    y_start   = pdf.get_y()

    for idx, image in enumerate([image_1, image_2], start=1):
        if image is None:
            continue
        img_path = Path(image.file_path)
        if not img_path.exists():
            continue
        try:
            x = 10 if idx == 1 else 110
            pdf.image(str(img_path), x=x, y=y_start, w=img_width)
            pdf.set_xy(x, y_start + img_width * 0.75 + 2)
            pdf.set_font("Helvetica", "", 8)
            pdf.cell(
                img_width, 5,
                f"{'Query' if idx == 1 else 'Reference'}: {image.original_filename}",
                align="C",
            )
        except Exception as e:
            logger.warning(
                "Could not embed image in PDF",
                extra={"image_id": image.id, "error": str(e)},
            )

    pdf.set_y(y_start + img_width * 0.75 + 10)