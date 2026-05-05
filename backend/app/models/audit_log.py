"""
backend/app/models/audit_log.py
---------------------------------
Immutable audit log — records every user action in the system.

Used for:
    - Forensic chain-of-custody (who accessed/analysed what and when)
    - Admin monitoring (see all actions across all users)
    - Investigator history (GET /logs returns own actions only)

Immutability contract
----------------------
Audit log rows are NEVER updated or deleted by application code.
If a User is deleted, user_id is set to NULL (SET NULL) so the log
entry survives — orphaned logs are forensically important.

action_type enum
-----------------
PostgreSQL enums are ALTER-sensitive. Adding new values requires:
    ALTER TYPE action_type ADD VALUE IF NOT EXISTS 'new_value';
This must be done OUTSIDE a transaction (or in its own transaction).
See database/migrations/ for the corresponding Alembic migration.

Values added for Case Management
----------------------------------
    case_created, case_updated, case_deleted
    case_evidence_linked, case_analysis_linked, case_report_linked
    case_note_added
"""

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ---------------------------------------------------------------------------
# Action type enum — ALL valid values across the entire system
# ---------------------------------------------------------------------------

ACTION_TYPE_ENUM = Enum(
    # ── Authentication ──────────────────────────────────────────────────────
    "user_login",
    "user_logout",
    "user_registered",
    "password_changed",

    # ── User management (admin) ─────────────────────────────────────────────
    "user_created",
    "user_updated",
    "user_deactivated",
    "user_deleted",

    # ── Evidence images ─────────────────────────────────────────────────────
    "image_uploaded",
    "image_deleted",
    "image_preprocessed",
    "embedding_extracted",
    "image_viewed",           # investigator opened image detail / comparison

    # ── Similarity analysis ─────────────────────────────────────────────────
    "comparison_started",
    "comparison_completed",

    # ── Reports ─────────────────────────────────────────────────────────────
    "report_generated",
    "report_downloaded",
    "report_deleted",

    # ── Feedback ────────────────────────────────────────────────────────────
    "feedback_submitted",

    # ── Dataset / model ─────────────────────────────────────────────────────
    "dataset_created",
    "model_retrained",

    # ── Case Management (added for Case Management Subsystem) ───────────────
    "case_created",
    "case_updated",
    "case_deleted",
    "case_evidence_linked",   # ForensicImage attached to a Case
    "case_analysis_linked",   # SimilarityResult attached to a Case
    "case_report_linked",     # Report attached to a Case
    "case_note_added",        # Investigator note posted in a Case
   #database_search
    "database_search",          # search entire database for similar images
    name="action_type",
)


# ---------------------------------------------------------------------------
# AuditLog model
# ---------------------------------------------------------------------------

class AuditLog(Base):
    """
    Immutable record of a single user action.

    Columns
    -------
    user_id     — who performed the action (NULL if user was deleted)
    action_type — what action was performed (enum — see above)
    details     — JSON payload with action-specific context
                  e.g. {"image_id": 42, "evidence_type": "fingerprint"}
    ip_address  — client IP at the time of the action
    timestamp   — server time when the action was recorded
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # NULL when the user has been deleted — SET NULL preserves the log(logs must survive user deletion)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
# What happened
    action_type: Mapped[str] = mapped_column(
        ACTION_TYPE_ENUM,
        nullable=False,
        index=True,
    )

    details: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Action-specific metadata as JSON",
    )
# Network context — useful for security audits
    ip_address: Mapped[str | None] = mapped_column(
        String(45),    # IPv6 max length is 45 chars
        nullable=True,
    )


    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # ── Relationship ────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(   # noqa: F821
        "User",
        back_populates="audit_logs",
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} action={self.action_type!r} "
            f"user_id={self.user_id} ts={self.timestamp}>"
        )