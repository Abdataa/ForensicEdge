"""
backend/app/models/case.py
----------------------------
SQLAlchemy ORM models for the Case Management Subsystem.

Tables
------
    Case          — the core investigation container
    CaseEvidence  — links a Case to one or more ForensicImages
    CaseAnalysis  — links a Case to one or more SimilarityResults
    CaseReport    — links a Case to one or more Reports
    CaseNote      — free-text notes posted inside a case

Design rationale
-----------------
A Case is the central coordinator of all forensic work.
Rather than embedding case_id on every downstream table (which would
require foreign keys on pre-existing tables), junction tables are used
(CaseEvidence, CaseAnalysis, CaseReport).  This is additive — no
existing models need to change.

Status flow
-----------
    OPEN → IN_PROGRESS → REVIEW → CLOSED

Priority levels
---------------
    LOW | MEDIUM | HIGH
"""

import enum
from datetime import datetime

from sqlalchemy import (
    DateTime, Enum, ForeignKey,
    Integer, String, Text, func, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CaseStatus(str, enum.Enum):
    OPEN        = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    REVIEW      = "REVIEW"
    CLOSED      = "CLOSED"


class CasePriority(str, enum.Enum):
    LOW    = "LOW"
    MEDIUM = "MEDIUM"
    HIGH   = "HIGH"


CASE_STATUS_ENUM = Enum(
    "OPEN", "IN_PROGRESS", "REVIEW", "CLOSED",
    name="case_status",
)

CASE_PRIORITY_ENUM = Enum(
    "LOW", "MEDIUM", "HIGH",
    name="case_priority",
)


# ---------------------------------------------------------------------------
# Case
# ---------------------------------------------------------------------------

class Case(Base):
    """
    Core investigation container.

    An investigator creates a case, then links evidence images,
    similarity analyses, and reports to it.  This gives a structured
    view of all forensic work done on one investigation.
    """

    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Title and description
    title: Mapped[str] = mapped_column(
        String(255), nullable=False,
        comment="Short descriptive title, e.g. 'Case #2025-001 Robbery Scene'"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Detailed case description and context"
    )

    # Ownership and assignment
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
        comment="User who created this case"
    )
    assigned_to: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
        comment="Investigator currently responsible for this case"
    )

    # Status + priority
    status: Mapped[str] = mapped_column(
        CASE_STATUS_ENUM,
        nullable=False,
        default="OPEN",
        server_default="OPEN",
    )
    priority: Mapped[str] = mapped_column(
        CASE_PRIORITY_ENUM,
        nullable=False,
        default="MEDIUM",
        server_default="MEDIUM",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ── Relationships ───────────────────────────────────────────────────────
    creator:  Mapped["User"] = relationship(               # noqa: F821
        "User", foreign_keys=[created_by],
        back_populates="created_cases",
    )
    assignee: Mapped["User"] = relationship(               # noqa: F821
        "User", foreign_keys=[assigned_to],
        back_populates="assigned_cases",
    )
    evidence:  Mapped[list["CaseEvidence"]]  = relationship(
        "CaseEvidence",  back_populates="case", cascade="all, delete-orphan"
    )
    analyses:  Mapped[list["CaseAnalysis"]]  = relationship(
        "CaseAnalysis",  back_populates="case", cascade="all, delete-orphan"
    )
    reports:   Mapped[list["CaseReport"]]    = relationship(
        "CaseReport",    back_populates="case", cascade="all, delete-orphan"
    )
    notes:     Mapped[list["CaseNote"]]      = relationship(
        "CaseNote",      back_populates="case", cascade="all, delete-orphan",
        order_by="CaseNote.created_at",
    )

    def __repr__(self) -> str:
        return f"<Case id={self.id} title={self.title!r} status={self.status}>"


# ---------------------------------------------------------------------------
# CaseEvidence — Case ↔ ForensicImage (many-to-many)
# ---------------------------------------------------------------------------

class CaseEvidence(Base):
    """
    Links a forensic image to a case.
    One case can have many evidence images.
    One image can be linked to multiple cases (e.g. shared evidence).
    """

    __tablename__ = "case_evidence"
    __table_args__ = (
        # Prevent the same image being linked to the same case twice
        UniqueConstraint("case_id", "image_id", name="uq_case_evidence"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    case_id: Mapped[int] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    image_id: Mapped[int] = mapped_column(
        ForeignKey("forensic_images.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # Who linked this evidence and when (chain of custody)
    linked_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(
        String(500), nullable=True,
        comment="Optional note about why this evidence is linked to the case"
    )

    # ── Relationships ───────────────────────────────────────────────────────
    case:  Mapped["Case"] = relationship("Case",  back_populates="evidence")
    image: Mapped["ForensicImage"] = relationship(      # noqa: F821
        "ForensicImage",
    )
    linker: Mapped["User"] = relationship(              # noqa: F821
        "User", foreign_keys=[linked_by],
    )

    def __repr__(self) -> str:
        return f"<CaseEvidence case={self.case_id} image={self.image_id}>"


# ---------------------------------------------------------------------------
# CaseAnalysis — Case ↔ SimilarityResult (many-to-many)
# ---------------------------------------------------------------------------

class CaseAnalysis(Base):
    """
    Links a similarity analysis result to a case.
    Tracks which analyses were run as part of this investigation.
    """

    __tablename__ = "case_analyses"
    __table_args__ = (
        UniqueConstraint("case_id", "result_id", name="uq_case_analysis"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    case_id: Mapped[int] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    result_id: Mapped[int] = mapped_column(
        ForeignKey("similarity_results.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ── Relationships ───────────────────────────────────────────────────────
    case:   Mapped["Case"] = relationship("Case",  back_populates="analyses")
    result: Mapped["SimilarityResult"] = relationship(  # noqa: F821
        "SimilarityResult",
    )

    def __repr__(self) -> str:
        return f"<CaseAnalysis case={self.case_id} result={self.result_id}>"


# ---------------------------------------------------------------------------
# CaseReport — Case ↔ Report (many-to-many)
# ---------------------------------------------------------------------------

class CaseReport(Base):
    """
    Links a generated PDF report to a case.
    One case can have multiple reports (one per analysis result).
    """

    __tablename__ = "case_reports"
    __table_args__ = (
        UniqueConstraint("case_id", "report_id", name="uq_case_report"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    case_id: Mapped[int] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    report_id: Mapped[int] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ── Relationships ───────────────────────────────────────────────────────
    case:   Mapped["Case"]   = relationship("Case",   back_populates="reports")
    report: Mapped["Report"] = relationship("Report")   # noqa: F821

    def __repr__(self) -> str:
        return f"<CaseReport case={self.case_id} report={self.report_id}>"


# ---------------------------------------------------------------------------
# CaseNote
# ---------------------------------------------------------------------------

class CaseNote(Base):
    """
    Free-text note posted by an investigator inside a case.
    Used for documenting observations, decisions, and case history.
    """

    __tablename__ = "case_notes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    case_id: Mapped[int] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    note_text: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Investigator observation or decision note"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ── Relationships ───────────────────────────────────────────────────────
    case:   Mapped["Case"] = relationship("Case", back_populates="notes")
    author: Mapped["User"] = relationship(        # noqa: F821
        "User", foreign_keys=[user_id],
    )

    def __repr__(self) -> str:
        return f"<CaseNote id={self.id} case={self.case_id}>"