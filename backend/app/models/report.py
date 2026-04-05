"""
backend/app/models/report.py
------------------------------
SQLAlchemy ORM model for the reports table.

Maps to report persistence model:
    Table: Reports
    PK: reportId
    Fields: userId, resultId, pdfPath
    Relations: linked to Users and SimilarityResults
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Report(Base):
    """
    Forensic PDF report generated from a SimilarityResult.

    Created by report_service.py when an investigator clicks
    "Generate Report" on the dashboard.  The PDF is stored in
    storage/reports/ and the path recorded here for later download.

    From report scenario 4:
        "System compiles similarity score, analysis summary, enhanced
         images, and feature visualizations into a formatted PDF."
    """

    __tablename__ = "reports"

    # ------------------------------------------------------------------
    # Primary key
    # ------------------------------------------------------------------
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # ------------------------------------------------------------------
    # Ownership and source
    # ------------------------------------------------------------------
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    result_id: Mapped[int] = mapped_column(
        ForeignKey("similarity_results.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,     # one report per similarity result
        index=True,
    )

    # ------------------------------------------------------------------
    # Report metadata
    # ------------------------------------------------------------------
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="Forensic Analysis Report",
    )
    pdf_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="Path inside storage/reports/ directory",
    )
    notes: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="Optional analyst notes attached to the report",
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    owner: Mapped["User"] = relationship(                            # noqa: F821
        "User",
        back_populates="reports",
    )
    similarity_result: Mapped["SimilarityResult"] = relationship(    # noqa: F821
        "SimilarityResult",
        back_populates="report",
    )

    def __repr__(self) -> str:
        return (
            f"<Report id={self.id} user_id={self.user_id} "
            f"result_id={self.result_id}>"
        )