"""
backend/app/models/forensic_image.py
--------------------------------------
SQLAlchemy ORM models for forensic evidence image lifecycle.

Contains four related tables that represent the full pipeline from raw
upload to stored feature embedding:

    ForensicImage      — raw uploaded evidence image (fingerprint / toolmark)
    PreprocessedImage  — enhanced version produced by enhance.py pipeline
    FeatureSet         — CNN embedding vector stored after inference
    ModelVersion       — record of which model weights produced the embedding

Report persistence model mappings:
    ForensicImages    → ForensicImage
    PreprocessedImages→ PreprocessedImage
    FeatureSets       → FeatureSet
    ModelVersions     → ModelVersion
"""

from datetime import datetime

from sqlalchemy import (
    DateTime, Enum, Float, ForeignKey,
    Integer, JSON, String, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ---------------------------------------------------------------------------
# Evidence type enum
# ---------------------------------------------------------------------------

class EvidenceType(str):
    FINGERPRINT = "fingerprint"
    TOOLMARK    = "toolmark"

EVIDENCE_TYPE_ENUM = Enum(
    "fingerprint", "toolmark",
    name="evidence_type",
)

# Image processing status
IMAGE_STATUS_ENUM = Enum(
    "uploaded",      # raw file stored, not yet processed
    "preprocessing", # enhance.py pipeline running
    "preprocessed",  # enhanced image ready
    "extracting",    # CNN embedding being computed
    "ready",         # embedding stored — available for comparison
    "failed",        # processing failed at some stage
    name="image_status",
)


# ---------------------------------------------------------------------------
# ForensicImage
# ---------------------------------------------------------------------------

class ForensicImage(Base):
    """
    Raw forensic evidence image uploaded by an investigator.

    Lifecycle: uploaded → preprocessed → embedding extracted → ready
    Tracked by the `status` field so the frontend can show progress.
    """

    __tablename__ = "forensic_images"

    # ------------------------------------------------------------------
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # ------------------------------------------------------------------
    # Ownership
    # ------------------------------------------------------------------
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # File metadata
    # ------------------------------------------------------------------
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="Path inside storage/uploads/ directory",
    )
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_type: Mapped[str] = mapped_column(
        EVIDENCE_TYPE_ENUM,
        nullable=False,
        comment="fingerprint | toolmark",
    )

    # ------------------------------------------------------------------
    # Processing status
    # ------------------------------------------------------------------
    status: Mapped[str] = mapped_column(
        IMAGE_STATUS_ENUM,
        nullable=False,
        default="uploaded",
        server_default="uploaded",
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------
    upload_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    uploader: Mapped["User"] = relationship(                         # noqa: F821
        "User",
        back_populates="forensic_images",
    )
    preprocessed_image: Mapped["PreprocessedImage"] = relationship(
        "PreprocessedImage",
        back_populates  = "source_image",
        uselist         = False,         # one-to-one
        cascade         = "all, delete-orphan",
    )
    feature_set: Mapped["FeatureSet"] = relationship(
        "FeatureSet",
        back_populates  = "image",
        uselist         = False,         # one-to-one in practice
        cascade         = "all, delete-orphan",
    )
    # Image appears as first image in similarity results
    similarity_results_as_query: Mapped[list["SimilarityResult"]] = relationship( # noqa: F821
        "SimilarityResult",
        foreign_keys    = "[SimilarityResult.image_id_1]",
        back_populates  = "image_1",
    )
    # Image appears as second image in similarity results
    similarity_results_as_reference: Mapped[list["SimilarityResult"]] = relationship( # noqa: F821
        "SimilarityResult",
        foreign_keys    = "[SimilarityResult.image_id_2]",
        back_populates  = "image_2",
    )

    def __repr__(self) -> str:
        return (
            f"<ForensicImage id={self.id} "
            f"type={self.evidence_type!r} status={self.status!r}>"
        )


# ---------------------------------------------------------------------------
# PreprocessedImage
# ---------------------------------------------------------------------------

class PreprocessedImage(Base):
    """
    Enhanced version of a ForensicImage produced by enhance.py.

    Stores the path to the processed file so the frontend can display
    both the original and enhanced versions side by side.
    """

    __tablename__ = "preprocessed_images"

    # ------------------------------------------------------------------
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    image_id: Mapped[int] = mapped_column(
        ForeignKey("forensic_images.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,     # one-to-one with ForensicImage
        index=True,
    )

    # Path inside storage/ where the enhanced image is saved
    enhanced_path: Mapped[str] = mapped_column(String(512), nullable=False)

    # Processing steps applied (for audit / dashboard display)
    processing_steps: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="e.g. {'resize': [224,224], 'clahe': true, 'unsharp': true}",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ------------------------------------------------------------------
    source_image: Mapped["ForensicImage"] = relationship(
        "ForensicImage",
        back_populates="preprocessed_image",
    )

    def __repr__(self) -> str:
        return f"<PreprocessedImage id={self.id} image_id={self.image_id}>"


# ---------------------------------------------------------------------------
# ModelVersion
# ---------------------------------------------------------------------------

class ModelVersion(Base):
    """
    Record of a trained model checkpoint.

    Tracks which version of best_model.pth produced a given FeatureSet,
    enabling reproducibility and model comparison over time.
    Matches the report's ModelVersions table.
    """

    __tablename__ = "model_versions"

    # ------------------------------------------------------------------
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    version: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        comment="e.g. 'v1.0', 'v1.1-retrained'",
    )
    accuracy: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Test set accuracy from evaluate.py",
    )
    auc: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="ROC AUC from evaluate.py",
    )
    eer: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Equal Error Rate from evaluate.py",
    )
    weights_path: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment="Path to best_model.pth for this version",
    )
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ------------------------------------------------------------------
    feature_sets: Mapped[list["FeatureSet"]] = relationship(
        "FeatureSet",
        back_populates="model_version",
    )

    def __repr__(self) -> str:
        return f"<ModelVersion id={self.id} version={self.version!r}>"


# ---------------------------------------------------------------------------
# FeatureSet
# ---------------------------------------------------------------------------

class FeatureSet(Base):
    """
    CNN embedding vector extracted from a ForensicImage.

    The embedding is stored as a JSON array so it can be retrieved and
    compared without re-running the CNN.  For large-scale deployments this
    would move to a vector database (pgvector), but JSON is sufficient for
    the project scope.

    Matches the report's FeatureSets table.
    """

    __tablename__ = "feature_sets"

    # ------------------------------------------------------------------
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    image_id: Mapped[int] = mapped_column(
        ForeignKey("forensic_images.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,     # one embedding per image
        index=True,
    )
    model_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("model_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # 256-dim L2-normalised embedding stored as JSON list of floats
    # e.g. [0.032, -0.118, 0.204, ...]
    feature_vector: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        comment="256-dim L2-normalised CNN embedding as float list",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ------------------------------------------------------------------
    image: Mapped["ForensicImage"] = relationship(
        "ForensicImage",
        back_populates="feature_set",
    )
    model_version: Mapped["ModelVersion"] = relationship(
        "ModelVersion",
        back_populates="feature_sets",
    )

    def __repr__(self) -> str:
        return (
            f"<FeatureSet id={self.id} image_id={self.image_id} "
            f"dim={len(self.feature_vector) if self.feature_vector else 0}>"
        )