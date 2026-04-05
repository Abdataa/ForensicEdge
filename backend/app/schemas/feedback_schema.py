"""
backend/app/schemas/feedback_schema.py
----------------------------------------
Pydantic schemas for investigator feedback on similarity results.

Purpose
-------
Closes the human-in-the-loop cycle described in the project report.
When an investigator disagrees with the model's prediction, they submit
feedback which is stored and later used by retrain_from_feedback.py to
improve the model.

Flow
----
    POST /api/v1/feedback
        Body:     FeedbackCreate    (result_id + is_correct + comment)
        Response: FeedbackResponse

    GET /api/v1/feedback/{feedback_id}
        Response: FeedbackResponse

    GET /api/v1/feedback
        Response: FeedbackListResponse  (admin/ai_engineer view of all feedback)
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class FeedbackCreate(BaseModel):
    """
    Body for POST /api/v1/feedback.

    is_correct=True  → investigator confirms the model was right
    is_correct=False → investigator flags the result as wrong
                       (used as hard example by retrain_from_feedback.py)
    """
    result_id: int = Field(
        ...,
        description = "ID of the SimilarityResult being reviewed",
        examples    = [5],
    )
    is_correct: bool = Field(
        ...,
        description = "True if model prediction was correct, False if wrong",
        examples    = [False],
    )
    comment: Optional[str] = Field(
        None,
        max_length  = 500,
        description = "Optional explanation — especially useful when is_correct=False",
        examples    = ["These are clearly different fingers. Model is incorrect."],
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class FeedbackResponse(BaseModel):
    """Feedback record returned to the client after submission or retrieval."""
    id:         int
    result_id:  int
    user_id:    int
    is_correct: bool
    comment:    Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class FeedbackListResponse(BaseModel):
    """
    Paginated list of feedback records.
    Used by AI engineers to identify which results to include in retraining.
    """
    total:     int
    page:      int
    limit:     int
    feedback:  list[FeedbackResponse]

    # Summary counts — useful for the admin dashboard widget
    total_correct:   Optional[int] = None
    total_incorrect: Optional[int] = None
    