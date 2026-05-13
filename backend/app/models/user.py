"""
backend/app/models/user.py
---------------------------
SQLAlchemy ORM model for the users table.

Maps to report persistence model:
    Table: Users
    PK: userId
    Fields: fullName, email, passwordHash, role, investigator_id, public_uuid
    Relations: one-to-many ForensicImages, AuditLogs, Reports
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Enum, String, func, Integer, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database  import Base
from app.core.security  import UserRole

if TYPE_CHECKING:
    from .case import Case


class User(Base):
    """
    Represents a ForensicEdge system user.

    Roles (from report use case diagram):
        analyst      — forensic investigator
        admin        — system administrator
        ai_engineer  — AI / dataset management
    """

    __tablename__ = "users"

    # ------------------------------------------------------------------
    # Primary key (Internal Use Only)
    # ------------------------------------------------------------------
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # ------------------------------------------------------------------
    # Public Identifier (Step 10 - External Use)
    # ------------------------------------------------------------------
    # Used for API endpoints to prevent internal ID exposure
    public_uuid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        unique=True,
        index=True,
        nullable=False,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )

    # ------------------------------------------------------------------
    # Identity fields
    # ------------------------------------------------------------------
    # Unique ForensicEdge Identifier (e.g., FE-ETH-2026-00001)
    investigator_id: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
        index=True,
    )

    full_name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Agency & Rank Metadata
    # ------------------------------------------------------------------
    # Example: Digital Forensics Unit, Cyber Crime Division
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    agency:     Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    rank:       Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Internal physical badge/shield number
    badge_number: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # ------------------------------------------------------------------
    # Clearance & Role
    # ------------------------------------------------------------------
    # Level: 1:Basic, 2:Investigator, 3:Senior, 4:Supervisor, 5:Admin
    clearance_level: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default="1",
        nullable=False
    )

    role: Mapped[str] = mapped_column(
        Enum(UserRole, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=UserRole.ANALYST.value,
        server_default=UserRole.ANALYST.value,
    )

    # ------------------------------------------------------------------
    # Employment Status
    # ------------------------------------------------------------------
    # Values: ACTIVE, SUSPENDED, ON_LEAVE, TERMINATED, RETIRED, TRAINING
    employment_status: Mapped[str] = mapped_column(
        String(20),
        default="ACTIVE",
        server_default="ACTIVE",
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    forensic_images: Mapped[list["ForensicImage"]] = relationship(# noqa: F821
        "ForensicImage",
        back_populates = "uploader",
        cascade         = "all, delete-orphan",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(# noqa: F821
        "AuditLog",
        back_populates = "user",
        cascade         = "all, delete-orphan",
    )
    reports: Mapped[list["Report"]] = relationship(   # noqa: F821
        "Report",
        back_populates = "owner",
        cascade         = "all, delete-orphan",
    )
    feedback: Mapped[list["Feedback"]] = relationship(  # noqa: F821
        "Feedback",
        back_populates = "user",
        cascade         = "all, delete-orphan",
    )

    # ------------------------------------------------------------------
    # Case Management relationships
    # ------------------------------------------------------------------
    created_cases: Mapped[list["Case"]] = relationship(  # noqa: F821
        "Case",
        foreign_keys="[Case.created_by]",
        back_populates="creator",
    )
    assigned_cases: Mapped[list["Case"]] = relationship(
        "Case",
        foreign_keys="[Case.assigned_to]",
        back_populates="assignee",
    )

    def __repr__(self) -> str:
        return (
            f"<User id={self.id} public_uuid={self.public_uuid} "
            f"email={self.email!r} clearance={self.clearance_level}>"
        )