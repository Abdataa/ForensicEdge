"""
backend/app/schemas/similarity_schema.py
------------------------------------------
Pydantic schemas for forensic similarity comparison.

This is the core output schema of ForensicEdge — the result that
forensic investigators see on the dashboard after running a comparison.

Flow
----
    POST /api/v1/compare
        Body:     CompareRequest   (two image IDs)
        Response: SimilarityResponse (full analysis result)

    GET /api/v1/compare/{result_id}
        Response: SimilarityResponse (retrieve past result)

    GET /api/v1/compare
        Response: SimilarityListResponse (paginated history)
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CompareRequest(BaseModel):
    """
    Body for POST /api/v1/compare.
    Both images must already be uploaded and have status='ready'
    (embedding extracted) before comparison is possible.
    Validation of status is performed in similarity_service.py.
    """
    image_id_1: int = Field(
        ...,
        description = "ID of the query evidence image",
        examples    = [1],
    )
    image_id_2: int = Field(
        ...,
        description = "ID of the reference evidence image",
        examples    = [2],
    )

    def validate_different_images(self) -> None:
        """Images must be different — comparing an image to itself is meaningless."""
        if self.image_id_1 == self.image_id_2:
            raise ValueError("image_id_1 and image_id_2 must be different images.")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class ImageSummary(BaseModel):
    """
    Compact image info embedded inside SimilarityResponse.
    Gives the frontend enough context to display image thumbnails
    alongside the similarity result without a second API call.
    """
    id:                int
    original_filename: str
    evidence_type:     str
    upload_date:       datetime

    model_config = {"from_attributes": True}


class SimilarityResponse(BaseModel):
    """
    Full forensic similarity analysis result.

    This is the primary output displayed on the React dashboard:
        - Similarity percentage (large central number)
        - Match status badge (MATCH / POSSIBLE MATCH / NO MATCH)
        - Detailed metrics panel (cosine similarity, euclidean distance)
        - Image thumbnails for both compared images
        - Timestamp for the audit log entry

    All three metric fields are included because:
        - similarity_percentage → investigator-friendly 0–100% scale
        - cosine_similarity     → ML-standard metric for the report
        - euclidean_distance    → complementary distance metric for the report
    """
    id:                    int
    similarity_percentage: float = Field(
        ...,
        ge=0.0, le=100.0,
        description="Similarity score mapped to [0, 100]",
    )
    cosine_similarity:     float = Field(
        ...,
        ge=-1.0, le=1.0,
        description="Raw cosine similarity between embeddings",
    )
    euclidean_distance:    float = Field(
        ...,
        ge=0.0, le=2.0,
        description="L2 distance between unit-norm embeddings",
    )
    match_status: str = Field(
        ...,
        description="MATCH | POSSIBLE MATCH | NO MATCH",
    )
    created_at:       datetime
    requested_by_id:  Optional[int] = Field(None, alias="requested_by")

    # Embedded image summaries for dashboard display
    image_1: Optional[ImageSummary] = None
    image_2: Optional[ImageSummary] = None

    model_config = {
        "from_attributes":  True,
        "populate_by_name": True,
    }


class SimilarityListResponse(BaseModel):
    """
    Paginated list of past comparisons for GET /api/v1/compare.
    Used by the "Analysis History" dashboard view.
    """
    total:   int
    page:    int
    limit:   int
    results: list[SimilarityResponse]