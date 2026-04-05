"""
backend/app/models/dataset.py
-------------------------------
SQLAlchemy ORM model for the datasets table.

Maps to report persistence model:
    Table: Datasets
    PK: datasetId
    Fields: name, type, path
    Purpose: AI Engineer dataset management use case
"""

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


DATASET_TYPE_ENUM = Enum(
    "fingerprint",
    "toolmark",
    "mixed",
    name="dataset_type",
)

DATASET_STATUS_ENUM = Enum(
    "active",       # available for training
    "archived",     # no longer used
    "processing",   # being prepared
    name="dataset_status",
)


class Dataset(Base):
    """
    Tracks forensic image datasets used for model training.

    Managed by the AI Engineer role via the dataset management use case.
    Referenced by ModelVersion to document which data produced each model.
    """

    __tablename__ = "datasets"

    # ------------------------------------------------------------------
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # ------------------------------------------------------------------
    # Dataset metadata
    # ------------------------------------------------------------------
    name: Mapped[str] = mapped_column(
        String(120),
        unique=True,
        nullable=False,
        comment="e.g. 'SOCOFing-augmented-v1'",
    )
    dataset_type: Mapped[str] = mapped_column(
        DATASET_TYPE_ENUM,
        nullable=False,
        comment="fingerprint | toolmark | mixed",
    )
    path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="Path to dataset root directory",
    )
    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    total_images: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Total number of images in the dataset",
    )
    total_identities: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of unique identities / classes",
    )
    status: Mapped[str] = mapped_column(
        DATASET_STATUS_ENUM,
        nullable=False,
        default="active",
        server_default="active",
    )

    # ------------------------------------------------------------------
    # Ownership
    # ------------------------------------------------------------------
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<Dataset id={self.id} name={self.name!r} "
            f"type={self.dataset_type!r} status={self.status!r}>"
        )