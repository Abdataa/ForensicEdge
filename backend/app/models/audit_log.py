"""
backend/app/models/audit_log.py
---------------------------------
SQLAlchemy ORM model for the audit_logs table.

Maps to report persistence model:
    Table: AuditLogs
    PK: logId
    Fields: actionType, userId, timestamp
    Relations: linked to Users
    Purpose: forensic chain-of-custody + admin audit trail

In forensic systems, every action that touches evidence must be logged.
This satisfies the report use case: "Investigator Retrieves Previous
Analysis Logs" and the admin use case: "View Audit Logs".
"""

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# Action types — covers all significant system events
ACTION_TYPE_ENUM = Enum(
    # Authentication
    "user_login",
    "user_logout",
    "user_registered",
    "password_changed",
    # Evidence management
    "image_uploaded",
    "image_deleted",
    "image_preprocessed",
    # Analysis
    "comparison_started",
    "comparison_completed",
    "embedding_extracted",
    # Reports
    "report_generated",
    "report_downloaded",
    "report_deleted",
    # Admin
    "user_created",
    "user_updated",
    "user_deactivated",
    "user_deleted",
    # Feedback
    "feedback_submitted",
    # AI / Dataset
    "dataset_created",
    "model_retrained",
    name="action_type",
)


class AuditLog(Base):
    """
    Immutable record of every significant system action.

    Audit logs are NEVER updated or deleted — they provide the forensic
    chain-of-custody trail required for evidence admissibility.
    Only INSERT operations should be performed on this table.

    Linked to Users (with SET NULL on user deletion so logs survive
    even when an account is removed — critical for forensic traceability).
    """

    __tablename__ = "audit_logs"

    # ------------------------------------------------------------------
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # ------------------------------------------------------------------
    # Who performed the action
    # SET NULL (not CASCADE) — logs must survive user deletion
    # ------------------------------------------------------------------
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ------------------------------------------------------------------
    # What happened
    # ------------------------------------------------------------------
    action_type: Mapped[str] = mapped_column(
        ACTION_TYPE_ENUM,
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Context — flexible JSON for action-specific details
    # e.g. {"image_id": 42, "evidence_type": "fingerprint"}
    #      {"result_id": 7, "similarity": 87.4, "status": "MATCH"}
    # ------------------------------------------------------------------
    details: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Action-specific metadata as JSON",
    )

    # ------------------------------------------------------------------
    # Network context — useful for security audits
    # ------------------------------------------------------------------
    ip_address: Mapped[str | None] = mapped_column(
        String(45),    # IPv6 max length is 45 chars
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Timestamp — server-side to prevent client clock manipulation
    # ------------------------------------------------------------------
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    user: Mapped["User"] = relationship(                             # noqa: F821
        "User",
        back_populates="audit_logs",
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} action={self.action_type!r} "
            f"user_id={self.user_id} ts={self.timestamp}>"
        )