"""
backend/app/services/report_service.py
----------------------------------------
Business logic for forensic PDF report generation and retrieval.

From project report scenario 4:
    "System compiles similarity score, analysis summary, enhanced images,
     and feature visualizations into a formatted PDF. Investigator receives
     a clear, professional report ready for documentation or courtroom use."

PDF generation uses fpdf2 (pip install fpdf2) — lightweight, no Java
dependency, works on Colab and Linux servers.

Report contents
---------------
    Header      : ForensicEdge logo text, case metadata, analyst name
    Section 1   : Evidence images (original + enhanced side by side)
    Section 2   : Similarity analysis results
                    - Similarity percentage (large, coloured by match status)
                    - Match status badge
                    - All three metrics (similarity%, cosine, euclidean)
                    - Evidence type (fingerprint | toolmark)
    Section 3   : Analyst notes (if provided)
    Footer      : Timestamp, disclaimer, report ID
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config  import settings
from app.models.report import Report
from app.models.similarity_result import SimilarityResult
from app.models.forensic_image    import ForensicImage
from app.models.user   import User
from app.schemas.report_schema import (
    ReportCreate,
    ReportResponse,
    ReportListResponse,
)
from app.schemas.similarity_schema import SimilarityResponse
from app.services.log_service import create_log


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
    # Load similarity result
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

    # One report per result (unique constraint on result_id)
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

    # Load both images for the report
    img1_row = await db.execute(
        select(ForensicImage).where(ForensicImage.id == result.image_id_1)
    )
    img2_row = await db.execute(
        select(ForensicImage).where(ForensicImage.id == result.image_id_2)
    )
    image_1 = img1_row.scalar_one_or_none()
    image_2 = img2_row.scalar_one_or_none()

    # Generate PDF
    pdf_path = await _generate_pdf(
        result   = result,
        image_1  = image_1,
        image_2  = image_2,
        analyst  = user,
        title    = payload.title,
        notes    = payload.notes,
    )

    # Save Report record
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

    # Audit log
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

    return ReportResponse.model_validate(report)


# ---------------------------------------------------------------------------
async def get_report(
    report_id: int,
    user:      User,
    db:        AsyncSession,
) -> ReportResponse:
    """Retrieve a single report by ID."""
    row = await db.execute(
        select(Report).where(Report.id == report_id)
    )
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
    """List paginated reports for the current user."""
    limit = min(limit, 100)
    query = select(Report).order_by(desc(Report.created_at))

    if user.role != "admin":
        query = query.where(Report.user_id == user.id)

    count_result = await db.execute(query.with_only_columns(Report.id))
    total = len(count_result.all())

    offset  = (page - 1) * limit
    rows    = await db.execute(query.offset(offset).limit(limit))
    reports = rows.scalars().all()

    return ReportListResponse(
        total   = total,
        page    = page,
        limit   = limit,
        reports = [ReportResponse.model_validate(r) for r in reports],
    )


# ---------------------------------------------------------------------------
async def get_pdf_path(
    report_id: int,
    user:      User,
    db:        AsyncSession,
) -> Path:
    """
    Return the filesystem path to the PDF file.
    Used by routes_report.py to serve the file via FileResponse.

    Raises HTTP 404 if the report or PDF file does not exist.
    """
    report_resp = await get_report(report_id, user, db)
    pdf_path    = Path(report_resp.pdf_path)

    if not pdf_path.exists():
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
    """
    Build the forensic PDF report using fpdf2.

    Returns the path where the PDF was saved.
    """
    try:
        from fpdf import FPDF
    except ImportError:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail      = "PDF library not installed. Run: pip install fpdf2",
        )

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # -----------------------------------------------------------------------
    # Header
    # -----------------------------------------------------------------------
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

    # -----------------------------------------------------------------------
    # Evidence information
    # -----------------------------------------------------------------------
    evidence_type = image_1.evidence_type if image_1 else "unknown"
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Evidence Information", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Evidence Type : {evidence_type.title()}", ln=True)
    if image_1:
        pdf.cell(0, 6, f"Query Image   : {image_1.original_filename}", ln=True)
    if image_2:
        pdf.cell(0, 6, f"Reference Image: {image_2.original_filename}", ln=True)
    pdf.ln(4)

    # Evidence images (if files still exist on disk)
    _add_images_to_pdf(pdf, image_1, image_2)
    pdf.ln(4)

    # -----------------------------------------------------------------------
    # Similarity analysis results
    # -----------------------------------------------------------------------
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Similarity Analysis Results", ln=True)
    pdf.ln(2)

    # Large similarity percentage
    pdf.set_font("Helvetica", "B", 28)
    pdf.cell(0, 14, f"{result.similarity_percentage:.1f}%", ln=True, align="C")

    # Match status — coloured by result
    pdf.set_font("Helvetica", "B", 14)
    status_colors = {
        "MATCH":          (0,   128, 0),    # green
        "POSSIBLE MATCH": (200, 140, 0),    # amber
        "NO MATCH":       (180,  0,  0),    # red
    }
    r, g, b = status_colors.get(result.match_status, (0, 0, 0))
    pdf.set_text_color(r, g, b)
    pdf.cell(0, 8, result.match_status, ln=True, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    # Metrics table
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(95, 7, "Metric", border=1)
    pdf.cell(95, 7, "Value", border=1, ln=True)
    pdf.set_font("Helvetica", "", 10)

    metrics = [
        ("Similarity Percentage",   f"{result.similarity_percentage:.2f}%"),
        ("Cosine Similarity",        f"{result.cosine_similarity:.4f}"),
        ("Euclidean Distance",       f"{result.euclidean_distance:.4f}"),
        ("Match Status",             result.match_status),
        ("Evidence Type",            evidence_type.title()),
        ("Comparison Date",          result.created_at.strftime("%Y-%m-%d %H:%M UTC")),
    ]
    for label, value in metrics:
        pdf.cell(95, 6, label, border=1)
        pdf.cell(95, 6, value, border=1, ln=True)
    pdf.ln(6)

    # -----------------------------------------------------------------------
    # Analyst notes
    # -----------------------------------------------------------------------
    if notes:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Analyst Notes", ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, notes)
        pdf.ln(4)

    # -----------------------------------------------------------------------
    # Disclaimer footer
    # -----------------------------------------------------------------------
    pdf.ln(6)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(
        0, 5,
        "DISCLAIMER: This report is generated by the ForensicEdge AI-assisted "
        "analysis system and is intended to SUPPORT, not replace, the judgment "
        "of qualified forensic examiners. All results must be verified by a "
        "certified forensic professional before use in legal proceedings. "
        "AI-generated similarity scores are probabilistic and not definitive.",
    )

    # -----------------------------------------------------------------------
    # Save PDF
    # -----------------------------------------------------------------------
    reports_dir = settings.REPORTS_DIR
    Path(reports_dir).mkdir(parents=True, exist_ok=True)
    filename = f"report_{uuid.uuid4().hex[:12]}.pdf"
    pdf_path  = Path(reports_dir) / filename
    pdf.output(str(pdf_path))

    return pdf_path


def _add_images_to_pdf(
    pdf:     "FPDF",
    image_1: Optional[ForensicImage],
    image_2: Optional[ForensicImage],
) -> None:
    """
    Add evidence image thumbnails to the PDF if files exist on disk.
    Shows original image only (enhanced path could be added similarly).
    """
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
            label = "Query" if idx == 1 else "Reference"
            pdf.cell(img_width, 5, f"{label}: {image.original_filename}", align="C")
        except Exception:
            pass    # skip image silently if format unsupported by fpdf2

    pdf.set_y(y_start + img_width * 0.75 + 10)