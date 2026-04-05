"""
backend/app/models/similarity_result.py
-----------------------------------------
SQLAlchemy ORM model for the similarity_results table.

Maps to report persistence model:
    Table: SimilarityResults
    PK: resultId
    Fields: imageId1, imageId2, score, status
    Relations: one-to-one Report
"""

from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# Match status enum — mirrors match_status() in siamese_network.py
MATCH_STATUS_ENUM = Enum(
    "MATCH",
    "POSSIBLE MATCH",
    "NO MATCH",
    name="match_status",
)


class SimilarityResult(Base):
    """
    Stores the output of one Siamese network comparison between two images.

    Created by similarity_service.py after calling compare_images() from
    ai_engine/inference/compare.py.  The result is displayed on the
    dashboard and linked to a generated Report.
    """

    __tablename__ = "similarity_results"

    # ------------------------------------------------------------------
    # Primary key
    # ------------------------------------------------------------------
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # ------------------------------------------------------------------
    # The two images being compared (FK → forensic_images)
    # ------------------------------------------------------------------
    image_id_1: Mapped[int] = mapped_column(
        ForeignKey("forensic_images.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Query evidence image",
    )
    image_id_2: Mapped[int] = mapped_column(
        ForeignKey("forensic_images.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference evidence image",
    )

    # ------------------------------------------------------------------
    # Who requested the comparison
    # ------------------------------------------------------------------
    requested_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ------------------------------------------------------------------
    # Similarity metrics (from siamese_network.analyze())
    # ------------------------------------------------------------------
    similarity_percentage: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Cosine similarity mapped to [0, 100]",
    )
    cosine_similarity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Raw cosine similarity [-1, 1]",
    )
    euclidean_distance: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="L2 distance between embeddings [0, 2]",
    )
    match_status: Mapped[str] = mapped_column(
        MATCH_STATUS_ENUM,
        nullable=False,
        comment="MATCH | POSSIBLE MATCH | NO MATCH",
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
    image_1: Mapped["ForensicImage"] = relationship(                 # noqa: F821
        "ForensicImage",
        foreign_keys   = [image_id_1],
        back_populates = "similarity_results_as_query",
    )
    image_2: Mapped["ForensicImage"] = relationship(                 # noqa: F821
        "ForensicImage",
        foreign_keys   = [image_id_2],
        back_populates = "similarity_results_as_reference",
    )
    report: Mapped["Report"] = relationship(                         # noqa: F821
        "Report",
        back_populates = "similarity_result",
        uselist        = False,    # one-to-one
        cascade        = "all, delete-orphan",
    )
    feedback: Mapped[list["Feedback"]] = relationship(               # noqa: F821
        "Feedback",
        back_populates = "similarity_result",
        cascade        = "all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<SimilarityResult id={self.id} "
            f"score={self.similarity_percentage:.1f}% "
            f"status={self.match_status!r}>"
        )
    