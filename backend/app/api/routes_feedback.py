"""
backend/app/api/routes_feedback.py
------------------------------------
Endpoints for submitting and reviewing investigator feedback.

Depends on:
    - app.services.feedback_service (submit_feedback, list_feedback, get_incorrect_feedback)
    - app.schemas.feedback_schema (FeedbackCreate, FeedbackResponse, FeedbackListResponse)
"""

from typing import Optional

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.api.dependencies import get_current_active_user, require_role
from app.models.user import User
from app.schemas.feedback_schema import (
    FeedbackCreate,
    FeedbackResponse,
    FeedbackListResponse,
)
from app.services import feedback_service

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit feedback on a similarity result",
)
async def submit_feedback(
    request: Request,
    payload: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Record whether a similarity prediction was correct or incorrect.

    - **is_correct = True**: you agree with the model's match status
    - **is_correct = False**: you disagree (used for model retraining)

    Each user may submit only one feedback per result.
    """
    return await feedback_service.submit_feedback(
        payload=payload,
        user=current_user,
        db=db,
        ip_address=request.client.host if request.client else None,
    )


@router.get(
    "",
    response_model=FeedbackListResponse,
    summary="List all feedback records (admin/engineer only)",
    dependencies=[Depends(require_role(["admin", "ai_engineer"]))],
)
async def list_feedback(
    is_correct: Optional[bool] = None,
    page: int = 1,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieve paginated feedback records.

    - **is_correct**: filter by correctness (True/False)
    - Access restricted to admin and AI engineer roles.
    """
    return await feedback_service.list_feedback(
        db=db,
        page=page,
        limit=limit,
        is_correct=is_correct,
    )


@router.get(
    "/incorrect",
    summary="Export incorrect feedback for retraining",
    dependencies=[Depends(require_role(["admin", "ai_engineer"]))],
)
async def export_incorrect_feedback(
    db: AsyncSession = Depends(get_db),
):
    """
    Returns a JSON list of all incorrect feedback cases.

    Used by the retraining pipeline to collect hard examples.
    """
    return await feedback_service.get_incorrect_feedback(db)