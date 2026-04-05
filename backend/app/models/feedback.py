"""
backend/app/models/feedback.py
--------------------------------
SQLAlchemy ORM model for the feedback table.

Maps to report use case:
    Use Case 9: "Investigator Provides Feedback on Incorrect Match"

Purpose
-------
When an investigator disagrees with the model's similarity result, they
can mark it as incorrect and add a comment.  This feedback is collected
into ai_engine/datasets/feedback_samples/ and used by
ai_engine/training/retrain_from_feedback.py to improve the model —
closing the human-in-the-loop cycle described in the report.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Feedback(Base):
    """
    Investigator feedback on a similarity result.

    The `is_correct` field indicates whether the investigator agrees
    with the model's match_status prediction:
        True  — model was correct (confirm the result)
        False — model was wrong   (flag for retraining)

    Only results marked is_correct=False are used as hard negative/
    positive examples in retrain_from_feedback.py.
    """

    __tablename__ = "feedback"

    # ------------------------------------------------------------------
    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # ------------------------------------------------------------------
    # Who submitted the feedback
    # ------------------------------------------------------------------
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Which result the feedback is about
    # ------------------------------------------------------------------
    result_id: Mapped[int] = mapped_column(
        ForeignKey("similarity_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Feedback content
    # ------------------------------------------------------------------
    is_correct: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        comment="True = model was correct, False = model was wrong",
    )
    comment: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Optional explanation from the investigator",
    )

    # ------------------------------------------------------------------
    # Timestamp
    # ------------------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    user: Mapped["User"] = relationship(                             # noqa: F821
        "User",
        back_populates="feedback",
    )
    similarity_result: Mapped["SimilarityResult"] = relationship(    # noqa: F821
        "SimilarityResult",
        back_populates="feedback",
    )

    def __repr__(self) -> str:
        return (
            f"<Feedback id={self.id} result_id={self.result_id} "
            f"correct={self.is_correct}>"
        )