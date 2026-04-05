"""
backend/app/schemas/report_schema.py
--------------------------------------
Pydantic schemas for forensic PDF report generation and retrieval.

Flow
----
    POST /api/v1/reports
        Body:     ReportCreate     (link to a similarity result)
        Response: ReportResponse   (report metadata + download path)

    GET /api/v1/reports/{report_id}
        Response: ReportResponse

    GET /api/v1/reports/{report_id}/download
        Response: FileResponse     (PDF binary — handled by FastAPI directly,
                                   not a Pydantic schema)

    GET /api/v1/reports
        Response: ReportListResponse (paginated history)

From project report scenario 4:
    "System compiles similarity score, analysis summary, enhanced images,
     and feature visualizations into a formatted PDF. Investigator receives
     a clear, professional report ready for documentation or courtroom use."
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.similarity_schema import SimilarityResponse


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class ReportCreate(BaseModel):
    """
    Body for POST /api/v1/reports.
    The result_id links the report to a completed similarity analysis.
    """
    result_id: int = Field(
        ...,
        description="ID of the SimilarityResult this report summarises",
        examples=[1],
    )
    title: str = Field(
        default  = "Forensic Analysis Report",
        max_length = 255,
        examples = ["Case #2025-001 Fingerprint Analysis"],
    )
    notes: Optional[str] = Field(
        None,
        max_length  = 1000,
        description = "Optional analyst observations to include in the report",
        examples    = ["Evidence collected from scene B, locker 14."],
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class ReportResponse(BaseModel):
    """
    Report metadata returned after generation or retrieval.
    pdf_path is the server-side path — the frontend uses the
    /reports/{id}/download endpoint to get the actual file.
    """
    id:         int
    title:      str
    notes:      Optional[str]
    pdf_path:   str
    created_at: datetime
    user_id:    int
    result_id:  int

    # Optionally embed the similarity result summary for dashboard display
    similarity_result: Optional[SimilarityResponse] = None

    model_config = {"from_attributes": True}


class ReportListResponse(BaseModel):
    """Paginated list of reports for GET /api/v1/reports."""
    total:   int
    page:    int
    limit:   int
    reports: list[ReportResponse]