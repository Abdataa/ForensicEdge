"""
backend/app/api/routes_feedback.py
------------------------------------
Investigator feedback endpoints.

Endpoints
---------
    POST /api/v1/feedback              — submit feedback on a result
    GET  /api/v1/feedback              — list all feedback (admin/ai_engineer)
    GET  /api/v1/feedback/{id}         — get single feedback record
    GET  /api/v1/feedback/export       — export incorrect cases for retraining

From report scenario 6:
    "Investigator submits feedback through 'Report Issue with Result'.
     Feedback recorded in the database for model improvement."
"""

from typing import Optional

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database     import get_db
from app.core.dependencies import CurrentUser, AIOrAdminUser
from app.schemas.feedback_schema import (
    FeedbackCreate,
    FeedbackResponse,
    FeedbackListResponse,
)
from app.services import feedback_service

router = APIRouter(prefix="/feedback", tags=["Feedback"])


# ---------------------------------------------------------------------------
@router.post(
    "",
    response_model = FeedbackResponse,
    status_code    = status.HTTP_201_CREATED,
    summary        = "Submit feedback on a similarity result",
)
async def submit_feedback(
    payload:      FeedbackCreate,
    request:      Request,
    current_user: CurrentUser ,
    db:           AsyncSession = Depends(get_db),
):
    """
    Submit investigator feedback on a similarity result.

    - **result_id**: the comparison result being reviewed
    - **is_correct**: `true` if the model was right, `false` if wrong
    - **comment**: explanation (especially useful when `is_correct=false`)

    Incorrect results are used by the AI team to retrain and improve the model.
    One submission per result per user — returns HTTP 409 on duplicate.
    """
    return await feedback_service.submit_feedback(
        payload    = payload,
        user       = current_user,
        db         = db,
        ip_address = request.client.host if request.client else None,
    )


# ---------------------------------------------------------------------------
@router.get(
    "",
    response_model = FeedbackListResponse,
    summary        = "List all feedback (admin / AI engineer)",
)
async def list_feedback(
    _:          AIOrAdminUser  ,
    is_correct: Optional[bool] = None,
    page:       int            = 1,
    limit:      int            = 50,

    db:         AsyncSession   = Depends(get_db),
):
    """
    List all feedback records.
    Restricted to admin and AI engineer roles.

    - **is_correct=false**: show only incorrect predictions (for retraining)
    - **is_correct=true**: show confirmed correct predictions
    - Includes summary counts: total_correct and total_incorrect
    """
    return await feedback_service.list_feedback(
        db         = db,
        page       = page,
        limit      = limit,
        is_correct = is_correct,
    )


# ---------------------------------------------------------------------------
@router.get(
    "/export",
    summary = "Export incorrect cases for model retraining",
)
async def export_incorrect_feedback(
    _:  AIOrAdminUser ,
    db: AsyncSession  = Depends(get_db),
):
    """
    Export all investigator-flagged incorrect results as structured data.
    Used by `ai_engine/training/retrain_from_feedback.py` to build
    a hard-example retraining set.

    Returns a list of dicts with:
    - result_id, image_id_1, image_id_2
    - similarity_percentage, match_status
    - investigator_comment

    Restricted to admin and AI engineer roles.
    """
    return await feedback_service.get_incorrect_feedback(db=db)


# ---------------------------------------------------------------------------
@router.get(
    "/{feedback_id}",
    response_model = FeedbackResponse,
    summary        = "Get a single feedback record",
)
async def get_feedback(
    feedback_id:  int,
    _:            AIOrAdminUser ,
    db:           AsyncSession  = Depends(get_db),
):
    """Retrieve a single feedback record by ID (admin/AI engineer only)."""
    from sqlalchemy import select
    from app.models.feedback import Feedback
    from fastapi import HTTPException

    row = await db.execute(
        select(Feedback).where(Feedback.id == feedback_id)
    )
    fb = row.scalar_one_or_none()

    if fb is None:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = f"Feedback {feedback_id} not found.",
        )
    return FeedbackResponse.model_validate(fb)