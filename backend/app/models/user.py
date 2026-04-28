"""
backend/app/models/user.py
---------------------------
SQLAlchemy ORM model for the users table.

Maps to report persistence model:
    Table: Users
    PK: userId
    Fields: fullName, email, passwordHash, role
    Relations: one-to-many ForensicImages, AuditLogs, Reports
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database  import Base
from app.core.security  import UserRole
from typing import TYPE_CHECKING

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
    # Primary key
    # ------------------------------------------------------------------
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # ------------------------------------------------------------------
    # Identity fields
    # ------------------------------------------------------------------
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
    # Role — analyst | admin | ai_engineer
    # ------------------------------------------------------------------
    role: Mapped[str] = mapped_column(
        Enum(UserRole, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=UserRole.ANALYST.value,
        server_default=UserRole.ANALYST.value,
    )

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------
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
    forensic_images: Mapped[list["ForensicImage"]] = relationship(   # noqa: F821
        "ForensicImage",
        back_populates = "uploader",
        cascade        = "all, delete-orphan",
        lazy           = "select",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(             # noqa: F821
        "AuditLog",
        back_populates = "user",
        cascade        = "all, delete-orphan",
        lazy           = "select",
    )
    reports: Mapped[list["Report"]] = relationship(                  # noqa: F821
        "Report",
        back_populates = "owner",
        cascade        = "all, delete-orphan",
        lazy           = "select",
    )
    feedback: Mapped[list["Feedback"]] = relationship(               # noqa: F821
        "Feedback",
        back_populates = "user",
        cascade        = "all, delete-orphan",
        lazy           = "select",
    )

    # ------------------------------------------------------------------
# Case Management relationships
# ------------------------------------------------------------------
     # Cases this user created

    created_cases: Mapped[list["Case"]] = relationship(   # noqa: F821
        "Case",
        foreign_keys="[Case.created_by]",
        back_populates="creator",
        lazy="select",
    )
   # Cases assigned to this user
    assigned_cases: Mapped[list["Case"]] = relationship(  # noqa: F821
        "Case",
        foreign_keys="[Case.assigned_to]",
        back_populates="assignee",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<User id={self.id} email={self.email!r} role={self.role!r} "
            f"active={self.is_active}>"
        )