"""
backend/app/services/feedback_service.py
------------------------------------------
Business logic for investigator feedback on similarity results.

Closes the human-in-the-loop cycle:
    Investigator flags wrong result → feedback saved →
    AI engineer exports incorrect cases → retrain_from_feedback.py
    improves the model → better future predictions.

Works for both fingerprint and toolmark results — the feedback record
links to a SimilarityResult which already carries the evidence_type
via its linked ForensicImage.
"""

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback          import Feedback
from app.models.similarity_result import SimilarityResult
from app.models.user              import User
from app.schemas.feedback_schema  import (
    FeedbackCreate,
    FeedbackResponse,
    FeedbackListResponse,
)
from app.services.log_service import create_log


# ---------------------------------------------------------------------------
async def submit_feedback(
    payload:    FeedbackCreate,
    user:       User,
    db:         AsyncSession,
    ip_address: Optional[str] = None,
) -> FeedbackResponse:
    """
    Submit investigator feedback on a similarity result.

    Validates:
        - SimilarityResult exists and is accessible by the user
        - User hasn't already submitted feedback for this result

    Raises:
        HTTP 404 — result not found
        HTTP 403 — result belongs to another user (non-admin)
        HTTP 409 — feedback already submitted for this result by this user
    """
    # Validate result exists and is accessible
    row = await db.execute(
        select(SimilarityResult).where(SimilarityResult.id == payload.result_id)
    )
    result = row.scalar_one_or_none()

    if result is None:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = f"Similarity result {payload.result_id} not found.",
        )
    if result.requested_by != user.id and user.role != "admin":
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail      = "Access denied.",
        )

    # Prevent duplicate feedback from the same user on the same result
    existing = await db.execute(
        select(Feedback).where(
            Feedback.result_id == payload.result_id,
            Feedback.user_id   == user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code = status.HTTP_409_CONFLICT,
            detail      = (
                f"You have already submitted feedback for result "
                f"{payload.result_id}."
            ),
        )

    feedback = Feedback(
        user_id    = user.id,
        result_id  = payload.result_id,
        is_correct = payload.is_correct,
        comment    = payload.comment,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)

    # Audit log
    await create_log(
        db          = db,
        action_type = "feedback_submitted",
        user_id     = user.id,
        details     = {
            "feedback_id": feedback.id,
            "result_id":   payload.result_id,
            "is_correct":  payload.is_correct,
        },
        ip_address  = ip_address,
    )

    return FeedbackResponse.model_validate(feedback)


# ---------------------------------------------------------------------------
async def list_feedback(
    db:         AsyncSession,
    page:       int           = 1,
    limit:      int           = 50,
    is_correct: Optional[bool] = None,
) -> FeedbackListResponse:
    """
    List all feedback records — admin and AI engineer only.

    Supports filtering by is_correct:
        is_correct=False → only incorrect predictions (for retraining)
        is_correct=True  → confirmed correct predictions
        is_correct=None  → all feedback

    Returns summary counts for the admin dashboard widget.
    """
    limit = min(limit, 100)
    query = select(Feedback).order_by(desc(Feedback.created_at))

    if is_correct is not None:
        query = query.where(Feedback.is_correct == is_correct)

    count_result = await db.execute(query.with_only_columns(Feedback.id))
    total = len(count_result.all())

    offset   = (page - 1) * limit
    rows     = await db.execute(query.offset(offset).limit(limit))
    feedback = rows.scalars().all()

    # Summary counts for dashboard widget
    correct_count = await db.execute(
        select(func.count(Feedback.id)).where(Feedback.is_correct == True)
    )
    incorrect_count = await db.execute(
        select(func.count(Feedback.id)).where(Feedback.is_correct == False)
    )

    return FeedbackListResponse(
        total            = total,
        page             = page,
        limit            = limit,
        feedback         = [FeedbackResponse.model_validate(f) for f in feedback],
        total_correct    = correct_count.scalar(),
        total_incorrect  = incorrect_count.scalar(),
    )


# ---------------------------------------------------------------------------
async def get_incorrect_feedback(
    db: AsyncSession,
) -> list[dict]:
    """
    Export all incorrect feedback cases for retraining.

    Called by ai_engine/training/retrain_from_feedback.py to identify
    hard examples — image pairs the model got wrong according to
    investigators.

    Returns a list of dicts with:
        result_id, image_id_1, image_id_2,
        similarity_percentage, match_status, comment
    """
    rows = await db.execute(
        select(Feedback, SimilarityResult)
        .join(SimilarityResult, Feedback.result_id == SimilarityResult.id)
        .where(Feedback.is_correct == False)
        .order_by(desc(Feedback.created_at))
    )

    results = []
    for feedback, result in rows.all():
        results.append({
            "feedback_id":           feedback.id,
            "result_id":             result.id,
            "image_id_1":            result.image_id_1,
            "image_id_2":            result.image_id_2,
            "similarity_percentage": result.similarity_percentage,
            "match_status":          result.match_status,
            "investigator_comment":  feedback.comment,
        })

    return results